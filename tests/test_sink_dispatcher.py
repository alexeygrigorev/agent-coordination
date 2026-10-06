#!/usr/bin/env python3
"""Comprehensive test suite for Product 4 Autonomous Sink Dispatcher Service.

Directive C3012:
Tests:
- test_sink_dispatcher_admit_valid_handshake
- test_sink_dispatcher_rejects_unknown_device
- test_sink_dispatcher_rejects_head_cred_leak
- test_sink_dispatcher_fifo_cursor_progression
- test_sink_dispatcher_cli_once
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

# Ensure agent-coordination is at index 0 of sys.path
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) in sys.path:
    sys.path.remove(str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT))

AGENT_BUS_ROOT = Path("/home/alexey/git/agent-bus")
if AGENT_BUS_ROOT.is_dir() and str(AGENT_BUS_ROOT) not in sys.path:
    sys.path.append(str(AGENT_BUS_ROOT))

from coordination.bus import FileBus
from adapters.agent_bus_client import enroll_agent, poll_messages, send_message
from coordination.host_interface import GuardRejected, query_host_events
from coordination.sink_dispatcher import SinkDispatcher


def test_sink_dispatcher_admit_valid_handshake(tmp_path: Path) -> None:
    """Verifies physical-like handshake payload (like AC-WIN-HETZ-001) from windows-desktop device.

    Verifies admission decision, event emitted to host_events.jsonl, correlated reply sent to sender,
    and message ACKed (sink unread=0).
    """
    bus_store = tmp_path / "bus_store"
    bus_store.mkdir(parents=True, mode=0o700)
    events_dir = tmp_path / "events"
    events_dir.mkdir(parents=True, mode=0o700)

    # 1. Enroll sink (hetzner-rmthz) and sender (windows-desktop)
    sink_cred, _ = enroll_agent(
        store_path=bus_store,
        agent_name="coord-primary-sink",
        device_id="hetzner-rmthz",
    )
    sender_cred, _ = enroll_agent(
        store_path=bus_store,
        agent_name="windows-codex",
        device_id="windows-desktop",
    )

    sink_id = sink_cred["identity"]["identity_id"]
    sender_id = sender_cred["identity"]["identity_id"]

    # 2. Windows desktop sender sends typed handshake ping
    sent_msg = send_message(
        store_path=bus_store,
        cred=sender_cred,
        recipient_id=sink_id,
        body="AC-WIN-HETZ-001 desktop to Hetzner ping",
        data={
            "device_id": "windows-desktop",
            "task_id": "task-handshake-001",
            "handshake": "AC-WIN-HETZ-001",
            "reply_requested": True,
        },
        kind="handshake",
    )
    msg_id = sent_msg["message_id"]

    # Verify message is currently unread in sink's inbox
    sink_inbox = poll_messages(bus_store, sink_cred, unread_only=True)
    assert len(sink_inbox) == 1
    assert sink_inbox[0]["message_id"] == msg_id

    # 3. Instantiate SinkDispatcher and run poll_and_dispatch
    dispatcher = SinkDispatcher(
        store_path=bus_store,
        cred=sink_cred,
        events_dir=events_dir,
    )
    outcomes = dispatcher.poll_and_dispatch(max_messages=10)

    # 4. Verify admission outcome
    assert len(outcomes) == 1
    outcome = outcomes[0]
    assert outcome["status"] == "admitted"
    assert outcome["message_id"] == msg_id
    assert outcome["device_id"] == "windows-desktop"
    assert outcome["reply_sent"] is True
    assert outcome["event_id"] is not None

    # 5. Verify structured host event recorded in host_events.jsonl
    events = query_host_events(events_dir=events_dir, event_type="task_admitted")
    assert len(events) == 1
    evt = events[0]
    assert evt["event_type"] == "task_admitted"
    assert evt["device_id"] == "windows-desktop"
    assert evt["task_id"] == "task-handshake-001"
    assert evt["details"]["execution_target"] == "hetzner-rmthz"
    assert evt["details"]["delivery"] == "sessionless_worker_bus"
    assert evt["details"]["session_id"] is None
    assert evt["details"]["message_id"] == msg_id
    assert evt["details"]["sender_id"] == sender_id

    # 6. Verify correlated reply sent to Windows sender
    sender_inbox = poll_messages(bus_store, sender_cred, unread_only=True)
    assert len(sender_inbox) == 1
    reply = sender_inbox[0]
    assert reply["reply_to"] == msg_id
    assert reply["sender_id"] == sink_id
    assert reply["recipient_id"] == sender_id
    assert reply["body"] == "AC-WIN-HETZ-001 desktop to Hetzner ping-ACK"
    assert reply["data"]["handshake"] == "AC-WIN-HETZ-001"
    assert reply["data"]["status"] == "admitted"
    assert reply["data"]["sink_id"] == sink_id
    assert reply["data"]["reply_to_message_id"] == msg_id
    assert reply["data"]["session_id"] is None
    assert reply["data"]["execution_target"] == "hetzner-rmthz"

    # 7. Verify sink unread cursor is 0 (message ACKed)
    sink_unread = poll_messages(bus_store, sink_cred, unread_only=True)
    assert len(sink_unread) == 0


def test_sink_dispatcher_rejects_unknown_device(tmp_path: Path) -> None:
    """Verifies unregistered device fails closed, records rejection event, and acks to prevent poison-pill."""
    bus_store = tmp_path / "bus_store"
    bus_store.mkdir(parents=True, mode=0o700)
    events_dir = tmp_path / "events"
    events_dir.mkdir(parents=True, mode=0o700)

    sink_cred, _ = enroll_agent(bus_store, "coord-primary-sink", device_id="hetzner-rmthz")
    client_cred, _ = enroll_agent(bus_store, "rogue-agent", device_id="windows-desktop")

    sink_id = sink_cred["identity"]["identity_id"]

    # Send message declaring unregistered device
    rogue_device = "rogue-unregistered-device-999"
    msg = send_message(
        store_path=bus_store,
        cred=client_cred,
        recipient_id=sink_id,
        body="Attempt admission for unknown node",
        data={
            "device_id": rogue_device,
            "task_id": "task-rogue-001",
            "reply_requested": True,
        },
        kind="command",
    )
    msg_id = sent_msg_id = msg["message_id"]

    dispatcher = SinkDispatcher(store_path=bus_store, cred=sink_cred, events_dir=events_dir)
    outcomes = dispatcher.poll_and_dispatch()

    # Verify rejection outcome
    assert len(outcomes) == 1
    outcome = outcomes[0]
    assert outcome["status"] == "rejected"
    assert outcome["device_id"] == rogue_device
    assert outcome["message_id"] == sent_msg_id
    assert "unknown_device" in outcome["reason"] or rogue_device in outcome["reason"]

    # Verify admission_rejected event recorded in host_events.jsonl
    events = query_host_events(events_dir=events_dir, event_type="admission_rejected")
    assert len(events) == 1
    assert events[0]["device_id"] == rogue_device
    assert events[0]["task_id"] == "task-rogue-001"
    assert events[0]["details"]["message_id"] == sent_msg_id

    # Verify poison pill message was ACKed so sink does not stall
    sink_unread = poll_messages(bus_store, sink_cred, unread_only=True)
    assert len(sink_unread) == 0

    # Verify no reply was sent to client
    client_inbox = poll_messages(bus_store, client_cred, unread_only=True)
    assert len(client_inbox) == 0


def test_sink_dispatcher_rejects_head_cred_leak(tmp_path: Path) -> None:
    """Verifies payload with forbidden 'head.cred' is rejected with GuardRejected, and records event."""
    bus_store = tmp_path / "bus_store"
    bus_store.mkdir(parents=True, mode=0o700)
    events_dir = tmp_path / "events"
    events_dir.mkdir(parents=True, mode=0o700)

    sink_cred, _ = enroll_agent(bus_store, "coord-primary-sink", device_id="hetzner-rmthz")
    client_cred, _ = enroll_agent(bus_store, "windows-codex", device_id="windows-desktop")

    sink_id = sink_cred["identity"]["identity_id"]
    dispatcher = SinkDispatcher(store_path=bus_store, cred=sink_cred, events_dir=events_dir)

    # 1. Direct admission verification: raises GuardRejected
    with pytest.raises(GuardRejected):
        dispatcher.admission.admit_host_task(
            "windows-desktop",
            "task-direct-cred-leak",
            payload={"head.cred": "secret-leak-001"},
            reject_on_cred=True,
        )

    # 2. Inject raw message into FileBus containing forbidden head.cred
    bus = FileBus(bus_store)
    poison_msg = bus.send(
        sender_id=client_cred["identity"]["identity_id"],
        token=client_cred["token"],
        recipient_id=sink_id,
        body="Inbound message with stolen credentials",
        data={
            "device_id": "windows-desktop",
            "task_id": "task-poison-leak-002",
            "head.cred": "stolen-super-secret-token",
            "reply_requested": True,
        },
        kind="command",
    )
    poison_msg_id = poison_msg.message_id

    # 3. Dispatch message and verify fail-closed guard rejection
    outcomes = dispatcher.poll_and_dispatch()
    assert len(outcomes) == 1
    outcome = outcomes[0]
    assert outcome["status"] == "rejected"
    assert outcome["device_id"] == "windows-desktop"
    assert outcome["message_id"] == poison_msg_id
    assert "head_cred_inheritance_rejected" in outcome["reason"]

    # 4. Verify guard_rejected event recorded in host_events.jsonl
    events = query_host_events(events_dir=events_dir, event_type="guard_rejected")
    assert len(events) == 1
    assert events[0]["device_id"] == "windows-desktop"
    assert events[0]["task_id"] == "task-poison-leak-002"
    assert events[0]["details"]["message_id"] == poison_msg_id
    assert events[0]["details"]["error_type"] == "GuardRejected"

    # 5. Verify poison pill ACKed so sink does not stall
    sink_unread = poll_messages(bus_store, sink_cred, unread_only=True)
    assert len(sink_unread) == 0

    # 6. Verify no reply was sent
    client_inbox = poll_messages(bus_store, client_cred, unread_only=True)
    assert len(client_inbox) == 0


def test_sink_dispatcher_fifo_cursor_progression(tmp_path: Path) -> None:
    """Sends multiple messages, runs poll_and_dispatch, verifies all admitted in FIFO order, unread drains to 0."""
    bus_store = tmp_path / "bus_store"
    bus_store.mkdir(parents=True, mode=0o700)
    events_dir = tmp_path / "events"
    events_dir.mkdir(parents=True, mode=0o700)

    sink_cred, _ = enroll_agent(bus_store, "coord-primary-sink", device_id="hetzner-rmthz")
    sender_cred, _ = enroll_agent(bus_store, "windows-codex", device_id="windows-desktop")

    sink_id = sink_cred["identity"]["identity_id"]

    # Send 4 messages in sequence
    msg_ids = []
    for seq in range(1, 5):
        m = send_message(
            store_path=bus_store,
            cred=sender_cred,
            recipient_id=sink_id,
            body=f"Directive step {seq}",
            data={
                "device_id": "windows-desktop",
                "task_id": f"task-seq-{seq}",
                "seq": seq,
                "reply_requested": True,
            },
            kind="command",
        )
        msg_ids.append(m["message_id"])

    # Initial check: 4 unread messages in sink inbox
    assert len(poll_messages(bus_store, sink_cred, unread_only=True)) == 4

    dispatcher = SinkDispatcher(store_path=bus_store, cred=sink_cred, events_dir=events_dir)

    # First dispatch batch: max_messages = 2
    batch1 = dispatcher.poll_and_dispatch(max_messages=2)
    assert len(batch1) == 2
    assert [b["message_id"] for b in batch1] == [msg_ids[0], msg_ids[1]]
    assert all(b["status"] == "admitted" for b in batch1)

    # Exactly 2 unread messages remaining
    remaining = poll_messages(bus_store, sink_cred, unread_only=True)
    assert len(remaining) == 2
    assert [m["message_id"] for m in remaining] == [msg_ids[2], msg_ids[3]]

    # Second dispatch batch: max_messages = 2
    batch2 = dispatcher.poll_and_dispatch(max_messages=2)
    assert len(batch2) == 2
    assert [b["message_id"] for b in batch2] == [msg_ids[2], msg_ids[3]]
    assert all(b["status"] == "admitted" for b in batch2)

    # Inbox fully drained
    assert len(poll_messages(bus_store, sink_cred, unread_only=True)) == 0

    # Verify all 4 admitted host events recorded in order
    events = query_host_events(events_dir=events_dir, event_type="task_admitted")
    assert len(events) == 4
    assert [e["task_id"] for e in events] == [
        "task-seq-1",
        "task-seq-2",
        "task-seq-3",
        "task-seq-4",
    ]


def test_sink_dispatcher_cli_once(tmp_path: Path) -> None:
    """Executes CLI subcommand --once and checks JSON output."""
    bus_store = tmp_path / "bus_store"
    bus_store.mkdir(parents=True, mode=0o700)
    events_dir = tmp_path / "events"
    events_dir.mkdir(parents=True, mode=0o700)

    sink_cred_file = tmp_path / "sink.cred.json"
    sink_cred, _ = enroll_agent(
        store_path=bus_store,
        agent_name="coord-primary-sink",
        device_id="hetzner-rmthz",
        cred_path=sink_cred_file,
    )
    sender_cred, _ = enroll_agent(
        store_path=bus_store,
        agent_name="windows-codex",
        device_id="windows-desktop",
    )

    sink_id = sink_cred["identity"]["identity_id"]

    # Send a message to sink
    sent = send_message(
        store_path=bus_store,
        cred=sender_cred,
        recipient_id=sink_id,
        body="CLI test message",
        data={
            "device_id": "windows-desktop",
            "task_id": "task-cli-001",
            "reply_requested": True,
        },
        kind="command",
    )

    # 1. Run CLI with --once flag
    cmd_flag = [
        sys.executable,
        "-m",
        "coordination.sink_dispatcher",
        "--store",
        str(bus_store),
        "--cred",
        str(sink_cred_file),
        "--events-dir",
        str(events_dir),
        "--once",
        "--json",
    ]
    res = subprocess.run(cmd_flag, capture_output=True, text=True, check=True)
    out = json.loads(res.stdout)
    assert out["status"] == "ok"
    assert out["dispatched_count"] == 1
    assert len(out["outcomes"]) == 1
    assert out["outcomes"][0]["status"] == "admitted"
    assert out["outcomes"][0]["message_id"] == sent["message_id"]

    # 2. Run CLI with positional 'once' subcommand when inbox is drained
    cmd_subcommand = [
        sys.executable,
        "-m",
        "coordination.sink_dispatcher",
        "once",
        "--store",
        str(bus_store),
        "--cred",
        str(sink_cred_file),
        "--events-dir",
        str(events_dir),
        "--json",
    ]
    res2 = subprocess.run(cmd_subcommand, capture_output=True, text=True, check=True)
    out2 = json.loads(res2.stdout)
    assert out2["status"] == "ok"
    assert out2["dispatched_count"] == 0
    assert len(out2["outcomes"]) == 0
