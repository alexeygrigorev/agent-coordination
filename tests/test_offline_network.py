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

