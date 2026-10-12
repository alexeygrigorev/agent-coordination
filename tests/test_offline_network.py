from pathlib import Path
from coordination.ssh_relay import SshRelay, SendRequest
from coordination.device_registry import DeviceRegistry
from coordination.cursors import CursorStore
from coordination.envelope import NamespacedId
from coordination.errors import TransportUnavailable

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "devices.example.json"

class FlakyTransport:
    def __init__(self):
        self.is_offline = True
        self.calls = []
        self.sessions = [
            {
                "id": "11111111",
                "tag": "codex-principal",
                "workspace": "/home/alexey/git/cloudflare-agent-git",
            }
        ]
        
    def run(self, device, argv, timeout=30):
        self.calls.append(argv)
        if self.is_offline:
            raise TransportUnavailable("network_down")
        if argv[-2:] == ["list", "--json"] or argv[-1] == "--json" and "list" in argv:
            import json
            return json.dumps(self.sessions)
        if "message" in argv and "send" in argv:
            import json
            return json.dumps({"id": "msg-ok", "delivery": "inbox", "created_at": 12345678})
        raise AssertionError(argv)

def test_desktop_to_hetzner_offline_queues_and_resumes(tmp_path: Path):
    transport = FlakyTransport()
    relay = SshRelay(
        DeviceRegistry.load(EXAMPLE),
        transport,
        CursorStore(tmp_path),
        local_device_id="desktop-local"
    )

    req = SendRequest(
        sender=NamespacedId("desktop-local", "/ac", "gui", "t1", "s1"),
        recipient=NamespacedId("hetzner-rmthz", "/home/alexey/git/cloudflare-agent-git", "codex-principal", "t1"),
        body="hello",
        data={"action": "test"},
        idempotency_key="msg-1",
        correlation_token="tok-1",
    )

    # 1. Network disconnected, simulates desktop sending to Hetzner
    transport.is_offline = True
    receipt1 = relay.send(req)
    assert receipt1.delivery == "queued_offline"
    
    pending = relay.store.pending_outbox()
    assert len(pending) == 1
    assert pending[0]["body"] == "hello"
    
    # 2. Network reconnects
    transport.is_offline = False
    
    # Retry offline queue
    receipts = relay.retry_offline()
    assert len(receipts) == 1
    assert receipts[0].delivery == "inbox"
    
    # Queue should be empty now
    assert len(relay.store.pending_outbox()) == 0
    
    # The cursor should remember the message ID
    assert relay.store.lookup_send(
        "msg-1",
        sender=req.sender.render(),
        recipient=req.recipient.render(),
        digest=receipts[0].payload_sha256
    ) == receipts[0].message_id


def test_offline_retry_advanced(tmp_path: Path):
    transport = FlakyTransport()
    transport.is_offline = True
    
    relay = SshRelay(
        DeviceRegistry.load(EXAMPLE),
        transport,
        CursorStore(tmp_path),
        local_device_id="desktop-local"
    )

    req = SendRequest(
        sender=NamespacedId("desktop-local", "/nested/path/with/slashes", "gui", "task_1", None),
        recipient=NamespacedId("hetzner-rmthz", "/home/alexey/git/cloudflare-agent-git", "codex-principal", "task_2", "sess_2"),
        body="complex payload",
        data={"action": "test2"},
        idempotency_key="msg-advanced",
        correlation_token="tok-2",
        originating_agent=NamespacedId("desktop-local", "/nested/path/with/slashes", "gui", "task_1", None)
    )

    # 1. Send while offline
    transport.calls.clear()
    receipt1 = relay.send(req)
    assert receipt1.delivery == "queued_offline"
    assert len(transport.calls) == 1
    
    outbox = relay.store.pending_outbox()
    assert len(outbox) == 1

    transport.is_offline = True
    transport.calls.clear()
    receipts_offline = relay.retry_offline()
    assert len(receipts_offline) == 1
    assert receipts_offline[0].delivery == "queued_offline"
    assert len(relay.store.pending_outbox()) == 1
    assert relay.store.pending_outbox()[0]["idempotency_key"] == "msg-advanced"
    assert len(transport.calls) == 1

    # 2. Network reconnects
    transport.is_offline = False
    transport.calls.clear()
    
    receipts = relay.retry_offline()
    assert len(receipts) == 1
    assert receipts[0].delivery == "inbox"
    assert len(transport.calls) == 2
    send_calls = [c for c in transport.calls if "send" in c]
    assert len(send_calls) == 1
    
    assert len(relay.store.pending_outbox()) == 0
    
    assert "--workspace" in send_calls[0]
    ws_idx = send_calls[0].index("--workspace")
    assert send_calls[0][ws_idx + 1] == "/home/alexey/git/cloudflare-agent-git"
    
    transport.calls.clear()
    receipts2 = relay.retry_offline()
    assert len(receipts2) == 0
    assert len(transport.calls) == 0
    
    transport.calls.clear()
    receipt_fresh = relay.send(req)
    assert receipt_fresh.message_id == receipts[0].message_id
    assert receipt_fresh.delivery == "inbox"
    assert len(transport.calls) == 0
    
    req_conflict = SendRequest(
        sender=req.sender,
        recipient=req.recipient,
        body="different body",
        data={"action": "test2"},
        idempotency_key="msg-advanced",
        correlation_token="tok-2",
    )
    from coordination.errors import IdempotencyConflict
    import pytest
    with pytest.raises(IdempotencyConflict) as exc_info:
        relay.send(req_conflict)
    assert "msg-advanced" in str(exc_info.value)

    transport.is_offline = True
    req3 = SendRequest(
        sender=NamespacedId("desktop-local", "/ac", "gui", "t3", None),
        recipient=NamespacedId("hetzner-rmthz", "/home/alexey/git/cloudflare-agent-git", "codex-principal", "t3", "s3"),
        body="restart payload",
        data=None,
        idempotency_key="msg-restart",
        correlation_token="tok-3",
    )
    transport.calls.clear()
    relay.send(req3)
    assert len(relay.store.pending_outbox()) == 1

    transport.is_offline = False
    transport.calls.clear()
    
    relay_restarted = SshRelay(
        DeviceRegistry.load(EXAMPLE),
        transport,
        CursorStore(tmp_path),
        local_device_id="desktop-local"
    )
    receipts_restart = relay_restarted.retry_offline()
    assert len(receipts_restart) == 1
    assert receipts_restart[0].delivery == "inbox"
    assert len(relay_restarted.store.pending_outbox()) == 0
    
    send_calls_restart = [c for c in transport.calls if "send" in c]
    assert len(send_calls_restart) == 1


def test_legacy_offline_queue_compatibility(tmp_path: Path):
    transport = FlakyTransport()
    transport.is_offline = False
    
    store = CursorStore(tmp_path)
    store.queue_offline({
        "idempotency_key": "msg-legacy",
        "message_id": "legacy-id",
        "sender": "desktop-local//home/usr/workspace/with/slashes/gui/-/task_legacy",
        "recipient": "hetzner-rmthz//home/alexey/git/cloudflare-agent-git/codex-principal/11111111/task_remote",
        "body": "legacy body",
        "data": None,
        "correlation_token": "legacy-tok",
        "bridge_device_id": "desktop-local",
        "originating_agent": "desktop-local//home/usr/workspace/with/slashes/gui/-/task_legacy"
    })
    
    relay = SshRelay(
        DeviceRegistry.load(EXAMPLE),
        transport,
        store,
        local_device_id="desktop-local"
    )
    
    receipts = relay.retry_offline()
    assert len(receipts) == 1
    assert receipts[0].delivery == "inbox"
    assert len(relay.store.pending_outbox()) == 0
    
    assert receipts[0].sender.workspace == "/home/usr/workspace/with/slashes"
    assert receipts[0].sender.session_id is None
    assert receipts[0].sender.task_id == "task_legacy"
    
    assert receipts[0].recipient.workspace == "/home/alexey/git/cloudflare-agent-git"
    assert receipts[0].recipient.session_id == "11111111"
    assert receipts[0].recipient.task_id == "task_remote"
    
    transport.calls.clear()
    relay.send(SendRequest(
        sender=receipts[0].sender,
        recipient=receipts[0].recipient,
        body="legacy body",
        data=None,
        idempotency_key="msg-legacy",
        correlation_token="legacy-tok",
    ))
    assert len(transport.calls) == 0



class SendFailsOnceTransport(FlakyTransport):
    """Online transport whose Nth `message send` raises mid-retry."""

    def __init__(self, fail_on_send):
        super().__init__()
        self.is_offline = False
        self.fail_on_send = fail_on_send
        self.send_attempts = 0
        self.sent_bodies = []

    def run(self, device, argv, timeout=30):
        if "message" in argv and "send" in argv:
            self.send_attempts += 1
            if self.send_attempts == self.fail_on_send:
                self.calls.append(argv)
                raise TransportUnavailable("connection_reset_mid_send")
            out = super().run(device, argv, timeout)
            self.sent_bodies.append(argv[argv.index("--json") + 1])
            return out
        return super().run(device, argv, timeout)


def test_mid_retry_transport_failure_keeps_undelivered_row_across_restart(tmp_path: Path):
    offline = FlakyTransport()
    relay = SshRelay(DeviceRegistry.load(EXAMPLE), offline, CursorStore(tmp_path),
                     local_device_id="desktop-local")
    recipient = NamespacedId("hetzner-rmthz", "/home/alexey/git/cloudflare-agent-git",
                             "codex-principal", "t-mid")
    for i in (1, 2):
        receipt = relay.send(SendRequest(
            sender=NamespacedId("desktop-local", "/a/b/c", "gui", "t-mid", f"s{i}"),
            recipient=recipient,
            body=f"body-{i}",
            data={"n": i},
            idempotency_key=f"mid-{i}",
            correlation_token=f"tok-{i}",
        ))
        assert receipt.delivery == "queued_offline"
    queued = {r["idempotency_key"]: r["message_id"] for r in relay.store.pending_outbox()}
    assert list(queued) == ["mid-1", "mid-2"]

    # Reconnect: the first send succeeds, the second fails in flight.
    flaky = SendFailsOnceTransport(fail_on_send=2)
    relay = SshRelay(DeviceRegistry.load(EXAMPLE), flaky, CursorStore(tmp_path),
                     local_device_id="desktop-local")
    receipts = relay.retry_offline()
    assert [(r.idempotency_key, r.delivery) for r in receipts] == [
        ("mid-1", "inbox"), ("mid-2", "queued_offline")]
    assert flaky.sent_bodies == ["body-1"]
    assert flaky.send_attempts == 2
    pending = relay.store.pending_outbox()
    assert [(r["idempotency_key"], r["message_id"]) for r in pending] == [("mid-2", queued["mid-2"])]

    # Restart over the same store with a healthy transport: only the failed row is sent.
    healthy = SendFailsOnceTransport(fail_on_send=0)
    restarted = SshRelay(DeviceRegistry.load(EXAMPLE), healthy, CursorStore(tmp_path),
                         local_device_id="desktop-local")
    receipts = restarted.retry_offline()
    assert [(r.idempotency_key, r.delivery) for r in receipts] == [("mid-2", "inbox")]
    assert healthy.sent_bodies == ["body-2"]
    assert restarted.store.pending_outbox() == []
    assert restarted.retry_offline() == []
    assert healthy.sent_bodies == ["body-2"]
