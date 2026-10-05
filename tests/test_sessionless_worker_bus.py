"""Unit and integration tests for SessionlessWorkerBus and ReceiptStore."""

from __future__ import annotations

import json
import stat
from pathlib import Path

import pytest

from coordination.bus import BusError, FileBus
from coordination.envelope import TransportState
from coordination.worker_bus import ReceiptStore, SessionlessWorkerBus, WorkerSendOutcome


def test_sessionless_worker_registration_and_no_aplexer_session(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Verify sessionless worker communicates without requiring or forging an aplexer session."""
    monkeypatch.setenv("APLEXER_SESSION_ID", "aplexer-interactive-session-fake-1234")
    monkeypatch.setenv("APLEXER_PORT", "9999")
    monkeypatch.setenv("APLEXER_PANE", "pane-0")

    store = tmp_path / "bus"
    worker = SessionlessWorkerBus.register(
        store=store,
        agent_name="worker-alpha",
        device_id="hetzner-rmthz",
        project_id="agent-coordination",
        task_id="task-unit-1",
    )

    # Bus-native identity: never adopts APLEXER_* environment variables
    assert worker.identity.kind == "bus-agent"
    assert worker.identity.identity_id != "aplexer-interactive-session-fake-1234"
    assert worker.identity.agent_name == "worker-alpha"
    assert worker.identity.task_id == "task-unit-1"

    # NamespacedId has session_id=None, which renders as '-'
    nid = worker.namespaced_id
    assert nid.session_id is None
    assert "aplexer-interactive-session-fake-1234" not in nid.render()
    assert nid.render() == "hetzner-rmthz/agent-coordination/worker-alpha/-/task-unit-1"

    # Save credentials and reload
    cred_file = tmp_path / "worker-alpha.cred.json"
    worker.save_credentials(cred_file)

    mode = stat.S_IMODE(cred_file.stat().st_mode)
    assert mode == 0o600

    reloaded = SessionlessWorkerBus.from_credentials(store, cred_file)
    assert reloaded.identity_id == worker.identity_id
    assert reloaded.token == worker.token
    assert reloaded.namespaced_id.render() == nid.render()


def test_worker_send_receive_explicit_ack_and_receipt_tracking(tmp_path: Path):
    """Verify registration, send, receive, explicit ACK, and durable receipt tracking."""
    store = tmp_path / "bus"
    a = SessionlessWorkerBus.register(
        store=store,
        agent_name="sender-worker",
        device_id="device-local",
        project_id="agent-coordination",
        task_id="send-task",
    )
    b = SessionlessWorkerBus.register(
        store=store,
        agent_name="receiver-worker",
        device_id="device-local",
        project_id="agent-coordination",
        task_id="recv-task",
    )

    # 1. Send with receipt
    outcome = a.send(
        recipient_id=b.identity_id,
        body="process artifact data",
        data={"path": "out.txt"},
        idempotency_key="worker-task-1",
    )
    assert isinstance(outcome, WorkerSendOutcome)
    msg, send_receipt = outcome

    assert msg.message_id
    assert msg.body == "process artifact data"
    assert msg.digest
    assert send_receipt.state == TransportState.SEND_RECEIPT
    assert send_receipt.message_id == msg.message_id
    assert send_receipt.payload_sha256 == msg.digest
    assert send_receipt.sender.agent_tag == "sender-worker"
    assert send_receipt.recipient.agent_tag == "receiver-worker"

    # Verify send receipt was durably stored
    persisted_send_receipt = a.get_send_receipt(msg.message_id)
    assert persisted_send_receipt is not None
    assert persisted_send_receipt.message_id == msg.message_id
    assert persisted_send_receipt.state == TransportState.SEND_RECEIPT

    # 2. Receiver inspects and receives
    assert b.current_cursor() is None
    pending = b.receive()
    assert len(pending) == 1
    assert pending[0].message_id == msg.message_id

    # Cursor has NOT advanced yet before ACK
    assert b.current_cursor() is None

    # 3. Explicit ACK with ReadAck receipt
    read_ack = b.ack(msg.message_id)
    assert read_ack.state == TransportState.RECIPIENT_READ_ACK
    assert read_ack.message_id == msg.message_id
    assert read_ack.acked_by.agent_tag == "receiver-worker"
    assert read_ack.acked_at

    # Cursor advanced durably to the acknowledged message ID
    assert b.current_cursor() == msg.message_id

    # Verify read ACK receipt is persisted and queryable
    persisted_ack = b.get_read_ack(msg.message_id)
    assert persisted_ack is not None
    assert persisted_ack.state == TransportState.RECIPIENT_READ_ACK
    assert persisted_ack.message_id == msg.message_id

    # List receipts contains both send and read receipts
    receipts = b.list_receipts(msg.message_id)
    assert len(receipts) == 2
    states = {r["state"] for r in receipts}
    assert states == {TransportState.SEND_RECEIPT.value, TransportState.RECIPIENT_READ_ACK.value}

    # Subsequent receive yields no unread messages
    assert b.receive() == []


def test_durable_restart_mid_stream_unacknowledged_retry(tmp_path: Path):
    """Verify durable restart: worker terminates mid-stream, reloads cursor, and achieves exactly-once progression."""
    store = tmp_path / "bus"
    a = SessionlessWorkerBus.register(
        store=store,
        agent_name="coordinator",
        device_id="device-local",
        project_id="agent-coordination",
    )
    b_cred = tmp_path / "b.cred.json"
    b_init = SessionlessWorkerBus.register(
        store=store,
        agent_name="stream-worker",
        device_id="device-local",
        project_id="agent-coordination",
    )
    b_init.save_credentials(b_cred)

    # Coordinator enqueues 3 sequential messages
    m1, _ = a.send(recipient_id=b_init.identity_id, body="chunk-1", idempotency_key="seq-1")
    m2, _ = a.send(recipient_id=b_init.identity_id, body="chunk-2", idempotency_key="seq-2")
    m3, _ = a.send(recipient_id=b_init.identity_id, body="chunk-3", idempotency_key="seq-3")

    # Worker receives all 3 messages
    received = b_init.receive()
    assert [m.message_id for m in received] == [m1.message_id, m2.message_id, m3.message_id]

    # Worker processes and ACKs chunk-1 ONLY
    b_init.ack(m1.message_id)
    assert b_init.current_cursor() == m1.message_id

    # --- SIMULATE CRASH / TERMINATION MID-STREAM BEFORE ACKING CHUNK-2 OR CHUNK-3 ---
    del b_init

    # Worker restarts: new instance reloads credentials and durable cursor
    b_restarted_1 = SessionlessWorkerBus.from_credentials(store, b_cred)
    assert b_restarted_1.current_cursor() == m1.message_id

    # Unacknowledged messages chunk-2 and chunk-3 are retried; chunk-1 is NOT duplicated
    resumed = b_restarted_1.receive()
    assert [m.message_id for m in resumed] == [m2.message_id, m3.message_id]

    # Worker processes and ACKs chunk-2
    b_restarted_1.ack(m2.message_id)
    assert b_restarted_1.current_cursor() == m2.message_id

    # --- SIMULATE SECOND TERMINATION BEFORE ACKING CHUNK-3 ---
    del b_restarted_1

    # Worker restarts second time
    b_restarted_2 = SessionlessWorkerBus.from_credentials(store, b_cred)
    assert b_restarted_2.current_cursor() == m2.message_id

    # Only unacknowledged chunk-3 is returned; chunks 1 and 2 are never duplicated
    resumed_2 = b_restarted_2.receive()
    assert [m.message_id for m in resumed_2] == [m3.message_id]

    # Worker completes and ACKs chunk-3
    b_restarted_2.ack(m3.message_id)
    assert b_restarted_2.current_cursor() == m3.message_id

    # Inbox is fully drained
    assert b_restarted_2.receive() == []


def test_negative_corrupt_cursor_recovery(tmp_path: Path):
    """Verify recovery when the durable cursor file is corrupted on disk."""
    store = tmp_path / "bus"
    a = SessionlessWorkerBus.register(store=store, agent_name="a", device_id="dev", project_id="agent-coordination")
    b = SessionlessWorkerBus.register(store=store, agent_name="b", device_id="dev", project_id="agent-coordination")

    m1, _ = a.send(recipient_id=b.identity_id, body="step-1")
    b.ack(m1.message_id)
    assert b.current_cursor() == m1.message_id

    cursor_file = store / "cursors" / "cursors.json"
    assert cursor_file.exists()

    # Corrupt the cursor file with invalid JSON garbage
    cursor_file.write_bytes(b"CORRUPTED_CURSOR_PAYLOAD\x00\xff{{invalid json")

    # Worker attempts cursor reload / receive
    assert b.recover_corrupt_cursor() is True
    # Worker does not crash; cursor recovers safely
    assert b.current_cursor() is None

    # Corrupt backup file was created
    corrupt_backups = list((store / "cursors").glob("cursors.corrupt*"))
    assert len(corrupt_backups) >= 1

    # Normal operations resume seamlessly
    m2, _ = a.send(recipient_id=b.identity_id, body="step-2")
    msgs = b.receive()
    assert any(m.message_id == m2.message_id for m in msgs)
    b.ack(m2.message_id)
    assert b.current_cursor() == m2.message_id


def test_negative_unacknowledged_message_retry(tmp_path: Path):
    """Verify that unacknowledged messages are persistently retried until explicit ACK."""
    store = tmp_path / "bus"
    a = SessionlessWorkerBus.register(store=store, agent_name="a", device_id="dev", project_id="agent-coordination")
    b = SessionlessWorkerBus.register(store=store, agent_name="b", device_id="dev", project_id="agent-coordination")

    m1, _ = a.send(recipient_id=b.identity_id, body="task to retry")

    # Receive without acking
    first_fetch = b.receive()
    assert len(first_fetch) == 1
    assert first_fetch[0].message_id == m1.message_id

    # Simulated worker restart
    b_new = SessionlessWorkerBus(store=store, identity=b.identity, token=b.token)
    second_fetch = b_new.receive()
    assert len(second_fetch) == 1
    assert second_fetch[0].message_id == m1.message_id

    # Now explicitly ACK
    b_new.ack(m1.message_id)

    # Third fetch returns empty
    third_fetch = b_new.receive()
    assert third_fetch == []


def test_negative_foreign_worker_rejection(tmp_path: Path):
    """Verify rejection of foreign worker ACK, forged tokens, and cross-project leakage."""
    store = tmp_path / "bus"
    a = SessionlessWorkerBus.register(store=store, agent_name="a", device_id="dev", project_id="proj-alpha")
    b = SessionlessWorkerBus.register(store=store, agent_name="b", device_id="dev", project_id="proj-alpha")
    c = SessionlessWorkerBus.register(store=store, agent_name="c-foreign", device_id="dev", project_id="proj-alpha")
    x = SessionlessWorkerBus.register(store=store, agent_name="x-other-project", device_id="dev", project_id="proj-beta")

    # 1. Foreign worker C tries to ACK message sent from A to B
    msg, _ = a.send(recipient_id=b.identity_id, body="secret task for b")
    with pytest.raises(BusError) as err:
        c.ack(msg.message_id)
    assert err.value.code == "not_recipient"

    # Message remains unacked in B's inbox
    assert len(b.receive()) == 1

    # 2. Worker with bad / forged token is rejected
    imposter = SessionlessWorkerBus(store=store, identity=b.identity, token="forged-fake-token")
    with pytest.raises(BusError) as err_auth:
        imposter.receive()
    assert err_auth.value.code == "auth_failed"

    with pytest.raises(BusError) as err_auth_send:
        imposter.send(recipient_id=a.identity_id, body="fake send")
    assert err_auth_send.value.code == "auth_failed"

    # 3. Cross-project messaging rejected (proj-alpha worker cannot send to proj-beta worker)
    with pytest.raises(BusError) as err_proj:
        a.send(recipient_id=x.identity_id, body="cross-project unauthorized")
    assert err_proj.value.code == "project_scope"

    # 4. Unknown recipient is rejected
    with pytest.raises(BusError) as err_unk:
        a.send(recipient_id="nonexistent-recipient-id", body="hello?")
    assert err_unk.value.code == "unknown_recipient"


def test_worker_reply_flow(tmp_path: Path):
    """Verify request-reply flow between sessionless workers with receipt tracking."""
    store = tmp_path / "bus"
    client = SessionlessWorkerBus.register(store=store, agent_name="client", device_id="dev", project_id="agent-coordination")
    worker = SessionlessWorkerBus.register(store=store, agent_name="worker", device_id="dev", project_id="agent-coordination")

    request, req_receipt = client.send(recipient_id=worker.identity_id, body="build-artifact", data={"version": "1.0"})
    assert req_receipt.state == TransportState.SEND_RECEIPT

    # Worker receives and ACKs request
    items = worker.receive()
    assert len(items) == 1
    worker.ack(items[0].message_id)

    # Worker replies
    reply_outcome = worker.reply(message_id=items[0].message_id, body="artifact-built", data={"sha": "abc1234"})
    reply_msg, reply_receipt = reply_outcome

    assert reply_msg.reply_to == request.message_id
    assert reply_msg.recipient_id == client.identity_id
    assert reply_receipt.state == TransportState.SEND_RECEIPT

    # Client receives reply and ACKs
    client_inbox = client.receive()
    assert len(client_inbox) == 1
    assert client_inbox[0].message_id == reply_msg.message_id
    client.ack(reply_msg.message_id)
    assert client.receive() == []
