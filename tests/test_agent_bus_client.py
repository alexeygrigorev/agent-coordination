#!/usr/bin/env python3
"""Comprehensive pytest test suite for Product 4 AgentBus transport adapter.

Directive C2958 / C2959.
Tests:
- test_enroll_creates_sessionless_identity_and_mode_0600_cred
- test_send_and_poll_lifecycle
- test_reply_and_ack_durable_cursor
- test_reject_head_cred_inheritance
- test_duplicate_idempotency_key
- test_rpc_dispatch_interface
- test_cli_subcommands_headless_execution
"""

from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

# Ensure repo root and agent-bus are on sys.path
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

AGENT_BUS_ROOT = Path("/home/alexey/git/agent-bus")
if AGENT_BUS_ROOT.is_dir() and str(AGENT_BUS_ROOT) not in sys.path:
    sys.path.insert(0, str(AGENT_BUS_ROOT))

from coordination.errors import IdempotencyConflict
from adapters.agent_bus_client import (
    OfflineSpool,
    ack_message,
    build_typed_ssh_command,
    enroll_agent,
    poll_messages,
    register_rpc_handler,
    reject_head_cred_inheritance,
    reply_message,
    rpc_dispatch,
    send_message,
)


def test_enroll_creates_sessionless_identity_and_mode_0600_cred(tmp_path: Path) -> None:
    """Verifies agent enrollment creates sessionless identity (session_id=None) and 0600 credential file."""
    bus_store = tmp_path / "bus_store"
    bus_store.mkdir(parents=True, mode=0o700)

    # 1. Custom cred_path
    custom_cred = tmp_path / "custom_creds" / "worker_custom.cred.json"
    cred_data, cred_file_str = enroll_agent(
        store_path=bus_store,
        agent_name="agent-worker-1",
        device_id="windows-desktop",
        project_id="cross-computer-coordination",
        task_id="task-custom-1",
        cred_path=custom_cred,
    )

    assert cred_file_str == str(custom_cred.resolve())
    assert custom_cred.is_file()

    # Permissions check: mode must be 0600
    file_stat = custom_cred.stat()
    assert stat.S_IMODE(file_stat.st_mode) == 0o600

    # Invariants on identity: session_id must strictly be None
    ident = cred_data["identity"]
    assert ident["device_id"] == "windows-desktop"
    assert ident["project_id"] == "cross-computer-coordination"
    assert ident["agent_name"] == "agent-worker-1"
    assert ident["task_id"] == "task-custom-1"
    assert ident["session_id"] is None, "Non-aplexer agent identity must strictly preserve session_id=None"
    assert isinstance(cred_data["token"], str) and len(cred_data["token"]) > 0
    assert cred_data["store"] == str(bus_store.resolve())

    # Verify content saved on disk
    disk_data = json.loads(custom_cred.read_text(encoding="utf-8"))
    assert disk_data == cred_data
    assert disk_data["identity"]["session_id"] is None

    # 2. Default cred_path (when cred_path is None)
    cred_data_default, default_path_str = enroll_agent(
        store_path=bus_store,
        agent_name="agent-worker-default",
    )
    default_cred_path = Path(default_path_str)
    assert default_cred_path.is_file()
    assert stat.S_IMODE(default_cred_path.stat().st_mode) == 0o600
    assert cred_data_default["identity"]["session_id"] is None
    assert cred_data_default["identity"]["agent_name"] == "agent-worker-default"


def test_send_and_poll_lifecycle(tmp_path: Path) -> None:
    """Verifies sending messages and polling inbox using both cred dicts and cred files."""
    bus_store = tmp_path / "bus_store"
    bus_store.mkdir(parents=True, mode=0o700)

    cred_alice, path_alice = enroll_agent(bus_store, "alice")
    cred_bob, path_bob = enroll_agent(bus_store, "bob")

    bob_id = cred_bob["identity"]["identity_id"]
    alice_id = cred_alice["identity"]["identity_id"]

    # Alice sends to Bob
    sent_msg = send_message(
        store_path=bus_store,
        cred=cred_alice,
        recipient_id=bob_id,
        body="Hello Bob from Alice",
        data={"action": "ping", "sequence": 1},
        kind="instruction",
    )

    assert sent_msg["sender_id"] == alice_id
    assert sent_msg["recipient_id"] == bob_id
    assert sent_msg["body"] == "Hello Bob from Alice"
    assert sent_msg["data"] == {"action": "ping", "sequence": 1}
    assert sent_msg["kind"] == "instruction"
    assert sent_msg["created_at"] is not None
    assert sent_msg["delivered_at"] is not None

    # Bob polls inbox (using dict cred)
    inbox_bob = poll_messages(bus_store, cred_bob, unread_only=True)
    assert len(inbox_bob) == 1
    assert inbox_bob[0]["message_id"] == sent_msg["message_id"]
    assert inbox_bob[0]["body"] == "Hello Bob from Alice"

    # Alice polls inbox -> should be empty (no loopback)
    inbox_alice = poll_messages(bus_store, cred_alice, unread_only=True)
    assert len(inbox_alice) == 0

    # Alice sends another message to Bob using cred file path and store=None (resolved from cred)
    sent_msg_2 = send_message(
        store_path=None,
        cred=path_alice,
        recipient_id=bob_id,
        body="Second message from Alice",
        data={"sequence": 2},
    )

    # Bob polls using cred file path
    inbox_bob_2 = poll_messages(store_path=None, cred=path_bob, unread_only=True)
    assert len(inbox_bob_2) == 2
    bob_msg_ids = {m["message_id"] for m in inbox_bob_2}
    assert sent_msg["message_id"] in bob_msg_ids
    assert sent_msg_2["message_id"] in bob_msg_ids


def test_reply_and_ack_durable_cursor(tmp_path: Path) -> None:
    """Verifies message reply and ACK semantics, including durable cursor advancement."""
    bus_store = tmp_path / "bus_store"
    bus_store.mkdir(parents=True, mode=0o700)

    cred_alice, _ = enroll_agent(bus_store, "alice")
    cred_bob, _ = enroll_agent(bus_store, "bob")

    bob_id = cred_bob["identity"]["identity_id"]
    alice_id = cred_alice["identity"]["identity_id"]

    # 1. Alice -> Bob
    msg1 = send_message(
        bus_store,
        cred_alice,
        recipient_id=bob_id,
        body="Task directive C2958",
        data={"directive": "C2958"},
    )
    msg1_id = msg1["message_id"]

    # 2. Bob receives message
    bob_inbox = poll_messages(bus_store, cred_bob, unread_only=True)
    assert len(bob_inbox) == 1
    assert bob_inbox[0]["message_id"] == msg1_id

    # 3. Bob replies to Alice
    reply_msg = reply_message(
        bus_store,
        cred_bob,
        message_id=msg1_id,
        body="Directive C2958 acknowledged and accepted",
        data={"status": "accepted"},
    )
    assert reply_msg["reply_to"] == msg1_id
    assert reply_msg["sender_id"] == bob_id
    assert reply_msg["recipient_id"] == alice_id
    assert reply_msg["kind"] == "reply"

    # 4. Bob ACKs msg1
    ack_res = ack_message(bus_store, cred_bob, message_id=msg1_id)
    assert ack_res is True

    # 5. Bob's unread inbox is now empty (durable cursor read ACK verified)
    bob_unread = poll_messages(bus_store, cred_bob, unread_only=True)
    assert len(bob_unread) == 0

    # Bob's full inbox still retains msg1 with acked_at populated
    bob_all = poll_messages(bus_store, cred_bob, unread_only=False)
    assert len(bob_all) == 1
    assert bob_all[0]["message_id"] == msg1_id
    assert bob_all[0]["acked_at"] is not None

    # 6. Alice receives Bob's reply
    alice_inbox = poll_messages(bus_store, cred_alice, unread_only=True)
    assert len(alice_inbox) == 1
    assert alice_inbox[0]["message_id"] == reply_msg["message_id"]
    assert alice_inbox[0]["reply_to"] == msg1_id

    # 7. Alice ACKs Bob's reply
    ack_res_alice = ack_message(bus_store, cred_alice, message_id=reply_msg["message_id"])
    assert ack_res_alice is True
    assert len(poll_messages(bus_store, cred_alice, unread_only=True)) == 0


def test_reject_head_cred_inheritance(tmp_path: Path) -> None:
    """Verifies fail-closed rejection and sanitization of head.cred / head_token material."""
    # 1. Direct unit tests on reject_head_cred_inheritance
    # Rejection cases (reject=True raises ValueError)
    forbidden_payloads = [
        {"head.cred": "secret-head-token-123"},
        {"head_token": "bearer-head-token-456"},
        {"head_cred": "token-789"},
        {"head.token": "token-abc"},
        {"cred": "secret-cred"},
        {"head": {"token": "nested-head-token"}},
        {"head": {"cred": "nested-head-cred"}},
        {"token": "my-head-token-secret"},
        {"cmd": "run with --cred /tmp/filebus/head.cred"},
        {"cmd": "export head_token=xyz"},
        ["safe", {"head.cred": "in-list"}],
    ]

    for payload in forbidden_payloads:
        with pytest.raises(ValueError, match="head_cred_inheritance_rejected"):
            reject_head_cred_inheritance(payload, reject=True)

    # Sanitization case (reject=False strips forbidden keys while keeping safe fields)
    mixed_payload = {
        "id": "task-clean-1",
        "head.cred": "leak-1",
        "head_token": "leak-2",
        "head_cred": "leak-3",
        "safe_key": "safe_val",
        "nested": {
            "head": {"token": "leak-4", "normal": "preserve-me"},
            "count": 100,
        },
    }
    cleaned = reject_head_cred_inheritance(mixed_payload, reject=False)
    assert "head.cred" not in cleaned
    assert "head_token" not in cleaned
    assert "head_cred" not in cleaned
    assert cleaned["id"] == "task-clean-1"
    assert cleaned["safe_key"] == "safe_val"
    assert cleaned["nested"]["count"] == 100
    assert cleaned["nested"]["head"] == {"normal": "preserve-me"}

    # 2. Transport integration tests in send_message and reply_message
    bus_store = tmp_path / "bus_store"
    bus_store.mkdir(parents=True, mode=0o700)
    cred_alice, _ = enroll_agent(bus_store, "alice")
    cred_bob, _ = enroll_agent(bus_store, "bob")
    bob_id = cred_bob["identity"]["identity_id"]

    # Fails closed on head.cred in data
    with pytest.raises(ValueError, match="head_cred_inheritance_rejected"):
        send_message(
            bus_store,
            cred_alice,
            recipient_id=bob_id,
            body="Sneaky message",
            data={"head.cred": "stolen-head-token"},
        )

    # Fails closed on head_token in data
    with pytest.raises(ValueError, match="head_cred_inheritance_rejected"):
        send_message(
            bus_store,
            cred_alice,
            recipient_id=bob_id,
            body="Sneaky message",
            data={"head_token": "stolen-head-token"},
        )

    # Fails closed on head.cred in body
    with pytest.raises(ValueError, match="head_cred_inheritance_rejected"):
        send_message(
            bus_store,
            cred_alice,
            recipient_id=bob_id,
            body="Passing token: head.cred = abc",
            data=None,
        )

    # Clean send succeeds
    clean_msg = send_message(
        bus_store,
        cred_alice,
        recipient_id=bob_id,
        body="Legitimate message",
        data={"status": "ok"},
    )
    assert clean_msg["body"] == "Legitimate message"

    # Fails closed on reply with head.cred
    with pytest.raises(ValueError, match="head_cred_inheritance_rejected"):
        reply_message(
            bus_store,
            cred_bob,
            message_id=clean_msg["message_id"],
            body="Reply with leak",
            data={"head.cred": "leak"},
        )


def test_duplicate_idempotency_key(tmp_path: Path) -> None:
    """Verifies deduplication on identical payload and IdempotencyConflict on conflicting payload."""
    bus_store = tmp_path / "bus_store"
    bus_store.mkdir(parents=True, mode=0o700)

    cred_alice, _ = enroll_agent(bus_store, "alice")
    cred_bob, _ = enroll_agent(bus_store, "bob")
    bob_id = cred_bob["identity"]["identity_id"]

    idem_key = "idemp-test-key-999"

    # 1. First send
    msg1 = send_message(
        bus_store,
        cred_alice,
        recipient_id=bob_id,
        body="Idempotent content",
        data={"param": "v1"},
        idempotency_key=idem_key,
    )

    # 2. Resend with exact same key and payload -> returns exact same message
    msg2 = send_message(
        bus_store,
        cred_alice,
        recipient_id=bob_id,
        body="Idempotent content",
        data={"param": "v1"},
        idempotency_key=idem_key,
    )
    assert msg1["message_id"] == msg2["message_id"]
    assert msg1["created_at"] == msg2["created_at"]

    # 3. Resend with same key but differing body -> raises IdempotencyConflict
    with pytest.raises(IdempotencyConflict):
        send_message(
            bus_store,
            cred_alice,
            recipient_id=bob_id,
            body="Conflicting different content",
            data={"param": "v1"},
            idempotency_key=idem_key,
        )

    # 4. Resend with same key but differing data -> raises IdempotencyConflict
    with pytest.raises(IdempotencyConflict):
        send_message(
            bus_store,
            cred_alice,
            recipient_id=bob_id,
            body="Idempotent content",
            data={"param": "conflicting_v2"},
            idempotency_key=idem_key,
        )


def test_rpc_dispatch_interface(tmp_path: Path) -> None:
    """Verifies rpc_dispatch for built-in transport methods and custom handlers."""
    bus_store = tmp_path / "bus_store"
    bus_store.mkdir(parents=True, mode=0o700)

    cred_alice, _ = enroll_agent(bus_store, "alice")
    cred_bob, _ = enroll_agent(bus_store, "bob")
    bob_id = cred_bob["identity"]["identity_id"]

    # 1. Built-in ping and echo
    ping_res = rpc_dispatch(bus_store, cred_alice, "ping", {"check": "alive"})
    assert ping_res["status"] == "ok"
    assert ping_res["pong"] is True

    echo_res = rpc_dispatch(bus_store, cred_alice, "echo", {"arg1": 123, "arg2": "xyz"})
    assert echo_res["status"] == "ok"
    assert echo_res["result"] == {"arg1": 123, "arg2": "xyz"}

    # 2. Built-in send
    send_res = rpc_dispatch(
        bus_store,
        cred_alice,
        "send",
        {
            "recipient_id": bob_id,
            "body": "RPC message body",
            "data": {"via_rpc": True},
        },
    )
    assert send_res["status"] == "ok"
    assert "message_id" in send_res
    msg_id = send_res["message_id"]

    # 3. Built-in poll
    poll_res = rpc_dispatch(bus_store, cred_bob, "poll", {"unread_only": True})
    assert poll_res["status"] == "ok"
    assert len(poll_res["messages"]) == 1
    assert poll_res["messages"][0]["message_id"] == msg_id

    # 4. Built-in reply
    reply_res = rpc_dispatch(
        bus_store,
        cred_bob,
        "reply",
        {
            "message_id": msg_id,
            "body": "RPC reply body",
            "data": {"reply_data": "ok"},
        },
    )
    assert reply_res["status"] == "ok"
    assert reply_res["reply_to"] == msg_id

    # 5. Built-in ack
    ack_res = rpc_dispatch(bus_store, cred_bob, "ack", {"message_id": msg_id})
    assert ack_res["status"] == "ok"
    assert ack_res["acked"] is True

    # 6. Built-in enroll via rpc
    enroll_res = rpc_dispatch(
        bus_store,
        cred_alice,
        "enroll",
        {"agent_name": "charlie"},
    )
    assert enroll_res["status"] == "ok"
    assert enroll_res["identity"]["agent_name"] == "charlie"
    assert enroll_res["identity"]["session_id"] is None

    # 7. Custom handler registration
    def custom_compute_handler(store: Any, cred: Any, params: dict[str, Any]) -> dict[str, Any]:
        return {"status": "ok", "sum": params["a"] + params["b"]}

    register_rpc_handler("custom_add", custom_compute_handler)
    custom_res = rpc_dispatch(bus_store, cred_alice, "custom_add", {"a": 25, "b": 17})
    assert custom_res["status"] == "ok"
    assert custom_res["sum"] == 42

    # 8. Unknown RPC method raises ValueError
    with pytest.raises(ValueError, match="Unknown RPC method"):
        rpc_dispatch(bus_store, cred_alice, "unsupported_method_xyz", {})


def test_cli_subcommands_headless_execution(tmp_path: Path) -> None:
    """Verifies all CLI subcommands (enroll, send, poll, reply, ack, rpc) under headless execution."""
    script_path = REPO_ROOT / "adapters" / "agent_bus_client.py"
    bus_store = tmp_path / "cli_store"
    bus_store.mkdir(parents=True, mode=0o700)

    # 1. CLI enroll alice
    cred_alice_file = tmp_path / "cli_alice.cred.json"
    cmd_enroll_alice = [
        sys.executable,
        str(script_path),
        "enroll",
        "--store",
        str(bus_store),
        "--name",
        "cli-alice",
        "--cred",
        str(cred_alice_file),
    ]
    res = subprocess.run(cmd_enroll_alice, capture_output=True, text=True, check=True)
    alice_data = json.loads(res.stdout)
    assert alice_data["status"] == "ok"
    assert alice_data["identity"]["agent_name"] == "cli-alice"
    assert alice_data["identity"]["session_id"] is None
    assert cred_alice_file.is_file()
    assert stat.S_IMODE(cred_alice_file.stat().st_mode) == 0o600

    # 2. CLI enroll bob
    cred_bob_file = tmp_path / "cli_bob.cred.json"
    cmd_enroll_bob = [
        sys.executable,
        str(script_path),
        "enroll",
        "--store",
        str(bus_store),
        "--name",
        "cli-bob",
        "--cred",
        str(cred_bob_file),
    ]
    res = subprocess.run(cmd_enroll_bob, capture_output=True, text=True, check=True)
    bob_data = json.loads(res.stdout)
    assert bob_data["status"] == "ok"
    bob_id = bob_data["identity"]["identity_id"]

    # 3. CLI send
    cmd_send = [
        sys.executable,
        str(script_path),
        "send",
        "--cred",
        str(cred_alice_file),
        "--recipient",
        bob_id,
        "--body",
        "CLI message from alice to bob",
        "--data",
        json.dumps({"test_cli": True}),
        "--kind",
        "note",
    ]
    res = subprocess.run(cmd_send, capture_output=True, text=True, check=True)
    send_out = json.loads(res.stdout)
    assert send_out["status"] == "ok"
    msg_id = send_out["message_id"]

    # 4. CLI poll
    cmd_poll = [
        sys.executable,
        str(script_path),
        "poll",
        "--cred",
        str(cred_bob_file),
        "--unread",
    ]
    res = subprocess.run(cmd_poll, capture_output=True, text=True, check=True)
    poll_out = json.loads(res.stdout)
    assert poll_out["status"] == "ok"
    assert poll_out["count"] == 1
    assert poll_out["messages"][0]["message_id"] == msg_id

    # 5. CLI reply
    cmd_reply = [
        sys.executable,
        str(script_path),
        "reply",
        "--cred",
        str(cred_bob_file),
        "--message-id",
        msg_id,
        "--body",
        "CLI reply from bob",
        "--data",
        json.dumps({"reply_ack": True}),
    ]
    res = subprocess.run(cmd_reply, capture_output=True, text=True, check=True)
    reply_out = json.loads(res.stdout)
    assert reply_out["status"] == "ok"
    assert reply_out["reply_to"] == msg_id

    # 6. CLI ack
    cmd_ack = [
        sys.executable,
        str(script_path),
        "ack",
        "--cred",
        str(cred_bob_file),
        "--message-id",
        msg_id,
    ]
    res = subprocess.run(cmd_ack, capture_output=True, text=True, check=True)
    ack_out = json.loads(res.stdout)
    assert ack_out["status"] == "ok"
    assert ack_out["acked"] is True

    # 7. CLI rpc
    cmd_rpc = [
        sys.executable,
        str(script_path),
        "rpc",
        "--cred",
        str(cred_alice_file),
        "--method",
        "ping",
        "--params",
        json.dumps({"cli_rpc": 1}),
    ]
    res = subprocess.run(cmd_rpc, capture_output=True, text=True, check=True)
    rpc_out = json.loads(res.stdout)
    assert rpc_out["status"] == "ok"
    assert rpc_out["pong"] is True

    # 8. Error handling prints structured JSON error to stderr and exits non-zero
    cmd_err = [
        sys.executable,
        str(script_path),
        "send",
        "--cred",
        str(cred_alice_file),
        "--recipient",
        "nonexistent-recipient-uuid",
        "--body",
        "Will fail",
    ]
    res = subprocess.run(cmd_err, capture_output=True, text=True)
    assert res.returncode == 1
    err_json = json.loads(res.stderr)
    assert err_json["status"] == "error"
    assert "error" in err_json


def test_offline_spool_stores_and_enforces_cred_protection(tmp_path: Path) -> None:
    """Verifies OfflineSpool stores pending messages and enforces fail-closed credential protection."""
    spool_db = tmp_path / "test_spool.db"
    spool = OfflineSpool(db_path=spool_db)

    # 1. Normal message spooling
    msg = spool.spool_message(
        recipient_id="agent-recipient-1",
        body="Execute coordination directive",
        data={"action": "run_step", "params": {"step": 1}},
        idempotency_key="spool-key-1",
        kind="instruction",
    )

    assert msg["status"] == "pending"
    assert msg["recipient_id"] == "agent-recipient-1"
    assert msg["body"] == "Execute coordination directive"
    assert msg["data"] == {"action": "run_step", "params": {"step": 1}}
    assert msg["idempotency_key"] == "spool-key-1"
    assert msg["kind"] == "instruction"
    assert msg["spool_id"] is not None and len(msg["spool_id"]) > 0
    assert msg["created_at"] is not None
    assert msg["delivered_at"] is None
    assert msg["message_id"] is None

    # Check pending list
    pending = spool.list_pending()
    assert len(pending) == 1
    assert pending[0]["spool_id"] == msg["spool_id"]
    assert pending[0]["status"] == "pending"
    assert pending[0]["data"] == {"action": "run_step", "params": {"step": 1}}

    # 2. Reject head credential inheritance in data
    forbidden_datas = [
        {"head.cred": "secret-head-token-123"},
        {"head_token": "bearer-head-token-456"},
        {"head_cred": "token-789"},
        {"head": {"token": "nested-head-token"}},
        {"head": {"cred": "nested-head-cred"}},
        {"token": "head-token-leak"},
    ]
    for bad_data in forbidden_datas:
        with pytest.raises(ValueError, match="head_cred_inheritance_rejected"):
            spool.spool_message(
                recipient_id="agent-recipient-1",
                body="Attempt to spool with head cred in data",
                data=bad_data,
            )

    # 3. Reject head credential inheritance in body
    forbidden_bodies = [
        "Include head.cred in plain text",
        "Setting head_token=secret",
    ]
    for bad_body in forbidden_bodies:
        with pytest.raises(ValueError, match="head_cred_inheritance_rejected"):
            spool.spool_message(
                recipient_id="agent-recipient-1",
                body=bad_body,
                data=None,
            )

    # Ensure none of the rejected messages were inserted into SQLite
    assert len(spool.list_pending()) == 1


def test_offline_spool_flush_fifo_lifecycle_and_dedup(tmp_path: Path) -> None:
    """Verifies FIFO ordering, deduplication with IdempotencyConflict, and delivery lifecycle upon flush."""
    bus_store = tmp_path / "bus_store"
    bus_store.mkdir(parents=True, mode=0o700)

    cred_alice, _ = enroll_agent(bus_store, "alice")
    cred_bob, _ = enroll_agent(bus_store, "bob")
    bob_id = cred_bob["identity"]["identity_id"]

    spool = OfflineSpool(db_path=tmp_path / "fifo_spool.db")

    # 1. Spool 3 messages in order
    msg1 = spool.spool_message(recipient_id=bob_id, body="First message", data={"seq": 1})
    msg2 = spool.spool_message(recipient_id=bob_id, body="Second message", data={"seq": 2})
    msg3 = spool.spool_message(recipient_id=bob_id, body="Third message", data={"seq": 3})

    # 2. Test dedup and idempotency conflict
    idem_key = "idemp-fifo-key-100"
    msg4 = spool.spool_message(recipient_id=bob_id, body="Fourth message", data={"seq": 4}, idempotency_key=idem_key)
    msg4_dup = spool.spool_message(recipient_id=bob_id, body="Fourth message", data={"seq": 4}, idempotency_key=idem_key)
    assert msg4["spool_id"] == msg4_dup["spool_id"]

    with pytest.raises(IdempotencyConflict):
        spool.spool_message(recipient_id=bob_id, body="Fourth conflict body", data={"seq": 4}, idempotency_key=idem_key)

    with pytest.raises(IdempotencyConflict):
        spool.spool_message(recipient_id=bob_id, body="Fourth message", data={"seq": 999}, idempotency_key=idem_key)

    # Verify FIFO pending list
    pending = spool.list_pending()
    assert len(pending) == 4
    assert [p["body"] for p in pending] == ["First message", "Second message", "Third message", "Fourth message"]
    assert [p["spool_id"] for p in pending] == [msg1["spool_id"], msg2["spool_id"], msg3["spool_id"], msg4["spool_id"]]

    # 3. Flush pending messages
    delivered = spool.flush(store_path=bus_store, cred=cred_alice)
    assert len(delivered) == 4
    assert [d["body"] for d in delivered] == ["First message", "Second message", "Third message", "Fourth message"]
    assert [d["spool_id"] for d in delivered] == [msg1["spool_id"], msg2["spool_id"], msg3["spool_id"], msg4["spool_id"]]

    # Spool queue should now be empty
    assert len(spool.list_pending()) == 0

    # 4. Bob polls inbox and receives all messages
    bob_inbox = poll_messages(store_path=bus_store, cred=cred_bob, unread_only=True)
    assert len(bob_inbox) == 4
    assert {m["body"] for m in bob_inbox} == {"First message", "Second message", "Third message", "Fourth message"}
    assert {m["data"]["seq"] for m in bob_inbox} == {1, 2, 3, 4}


def test_offline_spool_flush_fails_closed_on_connection_error_without_dropping(tmp_path: Path) -> None:
    """Verifies flush fails closed on transport errors, preserving all pending and unhandled messages."""
    spool = OfflineSpool(db_path=tmp_path / "flaky_spool.db")

    msg1 = spool.spool_message(recipient_id="agent-b", body="Step 1: Prep", data={"step": 1})
    msg2 = spool.spool_message(recipient_id="agent-b", body="Step 2: Sync", data={"step": 2})
    msg3 = spool.spool_message(recipient_id="agent-b", body="Step 3: Finish", data={"step": 3})

    attempted_calls: list[dict[str, Any]] = []

    def mock_flaky_transport(store_path: Any, cred: Any, **kwargs: Any) -> dict[str, Any]:
        attempted_calls.append(kwargs)
        if kwargs["body"] == "Step 2: Sync":
            raise ConnectionError("Simulated SSH / network socket disconnect")
        return {"message_id": f"mock-msg-{kwargs['body']}", "status": "ok", **kwargs}

    # First flush: succeeds on msg1, fails on msg2, stops before msg3
    delivered_first = spool.flush(store_path=None, cred={}, transport_fn=mock_flaky_transport)
    assert len(delivered_first) == 1
    assert delivered_first[0]["body"] == "Step 1: Prep"
    assert delivered_first[0]["spool_id"] == msg1["spool_id"]

    # Verify pending: msg2 and msg3 are NOT dropped or skipped
    pending_after_failure = spool.list_pending()
    assert len(pending_after_failure) == 2
    assert [p["body"] for p in pending_after_failure] == ["Step 2: Sync", "Step 3: Finish"]
    assert [p["spool_id"] for p in pending_after_failure] == [msg2["spool_id"], msg3["spool_id"]]

    # Verify mock transport only attempted Step 1 and Step 2
    assert len(attempted_calls) == 2
    assert attempted_calls[0]["body"] == "Step 1: Prep"
    assert attempted_calls[1]["body"] == "Step 2: Sync"

    # Network recovery: second flush succeeds for remaining messages
    def mock_recovered_transport(store_path: Any, cred: Any, **kwargs: Any) -> dict[str, Any]:
        return {"message_id": f"recovered-msg-{kwargs['body']}", "status": "ok", **kwargs}

    delivered_second = spool.flush(store_path=None, cred={}, transport_fn=mock_recovered_transport)
    assert len(delivered_second) == 2
    assert [d["body"] for d in delivered_second] == ["Step 2: Sync", "Step 3: Finish"]
    assert [d["spool_id"] for d in delivered_second] == [msg2["spool_id"], msg3["spool_id"]]

    # All messages now delivered
    assert len(spool.list_pending()) == 0


def test_build_typed_ssh_command_stdin_framing(tmp_path: Path) -> None:
    """Verifies typed SSH command generation and stdin JSON framing avoiding shell quoting issues."""
    cmd_args, json_payload = build_typed_ssh_command(
        host="remote-box.internal",
        store_path="/var/agent-bus/store",
        cred_path="/etc/agent-bus/agent.cred.json",
        method="poll",
        params={"unread_only": True},
    )

    expected_cmd = [
        "ssh",
        "remote-box.internal",
        "python3",
        "-m",
        "adapters.agent_bus_client",
        "rpc",
        "--store",
        "/var/agent-bus/store",
        "--cred",
        "/etc/agent-bus/agent.cred.json",
        "--stdin",
    ]
    assert cmd_args == expected_cmd

    payload = json.loads(json_payload)
    assert payload == {"method": "poll", "params": {"unread_only": True}}

    # Test custom python_bin and method="send"
    cmd_args_custom, json_payload_custom = build_typed_ssh_command(
        host="windows-node",
        store_path=str(tmp_path / "store"),
        cred_path=str(tmp_path / "cred.json"),
        method="send",
        params={"recipient_id": "target-uuid", "body": "Quoted body with 'single' and \"double\" quotes"},
        python_bin="/usr/bin/python3.12",
    )
    assert cmd_args_custom[2] == "/usr/bin/python3.12"
    payload_custom = json.loads(json_payload_custom)
    assert payload_custom["method"] == "send"
    assert payload_custom["params"]["body"] == "Quoted body with 'single' and \"double\" quotes"

    # Verify execution of typed RPC with --stdin framing locally
    script_path = REPO_ROOT / "adapters" / "agent_bus_client.py"
    bus_store = tmp_path / "rpc_store"
    bus_store.mkdir(parents=True, mode=0o700)
    cred_file = tmp_path / "rpc_agent.cred.json"
    enroll_agent(bus_store, "rpc-tester", cred_path=cred_file)

    cmd_exec = [
        sys.executable,
        str(script_path),
        "rpc",
        "--store",
        str(bus_store),
        "--cred",
        str(cred_file),
        "--stdin",
    ]
    stdin_input = json.dumps({"method": "ping", "params": {"test_typed": 42}})
    res = subprocess.run(cmd_exec, input=stdin_input, capture_output=True, text=True, check=True)
    out = json.loads(res.stdout)
    assert out["status"] == "ok"
    assert out["method"] == "ping"
    assert out["pong"] is True
    assert out["params"] == {"test_typed": 42}


def test_cli_spool_and_flush(tmp_path: Path) -> None:
    """Verifies CLI subcommands for spool and flush operations."""
    script_path = REPO_ROOT / "adapters" / "agent_bus_client.py"
    bus_store = tmp_path / "cli_bus_store"
    bus_store.mkdir(parents=True, mode=0o700)
    spool_db = tmp_path / "cli_test_spool.db"

    # Enroll sender and recipient
    cred_alice_file = tmp_path / "cli_alice.cred.json"
    enroll_agent(bus_store, "cli-alice", cred_path=cred_alice_file)

    cred_bob_file = tmp_path / "cli_bob.cred.json"
    cred_bob, _ = enroll_agent(bus_store, "cli-bob", cred_path=cred_bob_file)
    bob_id = cred_bob["identity"]["identity_id"]

    # 1. Spool message via CLI
    cmd_spool = [
        sys.executable,
        str(script_path),
        "spool",
        "--spool-db",
        str(spool_db),
        "--recipient",
        bob_id,
        "--body",
        "Queued offline command",
        "--data",
        json.dumps({"offline_task": "t-100"}),
        "--key",
        "cli-spool-key-1",
        "--kind",
        "instruction",
    ]
    res_spool = subprocess.run(cmd_spool, capture_output=True, text=True, check=True)
    spool_out = json.loads(res_spool.stdout)
    assert spool_out["status"] == "ok"
    assert spool_out["action"] == "spool"
    assert spool_out["recipient_id"] == bob_id
    assert spool_out["body"] == "Queued offline command"
    assert spool_out["spool_status"] == "pending"
    assert spool_out["spool_id"] is not None

    # 2. Spool message with forbidden head cred fails via CLI
    cmd_spool_forbidden = [
        sys.executable,
        str(script_path),
        "spool",
        "--spool-db",
        str(spool_db),
        "--recipient",
        bob_id,
        "--body",
        "Should fail closed",
        "--data",
        json.dumps({"head.cred": "stolen-token"}),
    ]
    res_forbidden = subprocess.run(cmd_spool_forbidden, capture_output=True, text=True)
    assert res_forbidden.returncode == 1
    err_out = json.loads(res_forbidden.stderr)
    assert err_out["status"] == "error"
    assert err_out["error_type"] == "ValueError"

    # 3. Flush spool via CLI
    cmd_flush = [
        sys.executable,
        str(script_path),
        "flush",
        "--spool-db",
        str(spool_db),
        "--store",
        str(bus_store),
        "--cred",
        str(cred_alice_file),
    ]
    res_flush = subprocess.run(cmd_flush, capture_output=True, text=True, check=True)
    flush_out = json.loads(res_flush.stdout)
    assert flush_out["status"] == "ok"
    assert flush_out["action"] == "flush"
    assert flush_out["count"] == 1
    assert flush_out["pending_remaining"] == 0
    assert len(flush_out["delivered"]) == 1
    assert flush_out["delivered"][0]["body"] == "Queued offline command"

    # 4. Verify recipient polls inbox and receives the spooled message
    cmd_poll = [
        sys.executable,
        str(script_path),
        "poll",
        "--store",
        str(bus_store),
        "--cred",
        str(cred_bob_file),
        "--unread",
    ]
    res_poll = subprocess.run(cmd_poll, capture_output=True, text=True, check=True)
    poll_out = json.loads(res_poll.stdout)
    assert poll_out["status"] == "ok"
    assert poll_out["count"] == 1
    assert poll_out["messages"][0]["body"] == "Queued offline command"
    assert poll_out["messages"][0]["data"] == {"offline_task": "t-100"}
