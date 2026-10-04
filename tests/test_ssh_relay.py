"""Local fake-transport tests. These are not cross-computer proof."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from coordination.cursors import CursorStore
from coordination.device_registry import DeviceRegistry
from coordination.envelope import NamespacedId
from coordination.errors import NativeBindingMissing, UnknownDevice
from coordination.ssh_relay import SendRequest, SshRelay

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "devices.example.json"


class FakeTransport:
    def __init__(self):
        self.calls: list[list[str]] = []
        self.sessions = [
            {
                "id": "93cf28f2-2872-411c-a5da-179e1b83b59f",
                "tag": "codex-principal",
                "workspace": "/home/alexey/git/cloudflare-agent-git",
                "engine": "codex",
                "reported_state": "working",
                "phase": "running",
            }
        ]
        self.send_result = {
            "id": "01aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            "delivery": "inbox",
            "created_at": 1791114000,
        }

    def run(self, device, argv, timeout=30):
        self.calls.append(argv)
        if argv[-2:] == ["list", "--json"] or argv[-1] == "--json" and "list" in argv:
            return json.dumps(self.sessions)
        if "message" in argv and "send" in argv:
            return json.dumps(self.send_result)
        raise AssertionError(argv)


def _relay(tmp_path: Path, transport=None) -> tuple[SshRelay, FakeTransport]:
    transport = transport or FakeTransport()
    relay = SshRelay(
        DeviceRegistry.load(EXAMPLE),
        transport,
        CursorStore(tmp_path),
        local_device_id="hetzner-rmthz",
    )
    return relay, transport


def test_send_resolves_catalog_and_records_inbox_receipt(tmp_path: Path):
    relay, transport = _relay(tmp_path)
    receipt = relay.send(
        SendRequest(
            sender=NamespacedId("hetzner-rmthz", "/home/alexey/git/agent-coordination", "agent-coordination-head", "t1", "81e8010c"),
            recipient=NamespacedId("hetzner-rmthz", "/home/alexey/git/cloudflare-agent-git", "codex-principal", "t1"),
            body="C1341 ACK",
            data={"token": "C1341"},
            idempotency_key="k-ack",
            correlation_token="C1341",
        )
    )
    assert receipt.message_id == "01aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    assert receipt.delivery == "inbox"
    assert receipt.catalog_resolved_session_id == "93cf28f2-2872-411c-a5da-179e1b83b59f"
    assert receipt.originating_agent.agent_tag == "agent-coordination-head"
    assert receipt.bridge_device_id == "hetzner-rmthz"
    assert any("list" in c for c in transport.calls)
    assert any("send" in c for c in transport.calls)


def test_idempotent_retry_does_not_double_send(tmp_path: Path):
    relay, transport = _relay(tmp_path)
    req = SendRequest(
        sender=NamespacedId("hetzner-rmthz", "/ac", "head", "t1", "s1"),
        recipient=NamespacedId("hetzner-rmthz", "/home/alexey/git/cloudflare-agent-git", "codex-principal", "t1"),
        body="same",
        data=None,
        idempotency_key="stable-key",
        correlation_token="T",
    )
    first = relay.send(req)
    sends_after_first = sum(1 for c in transport.calls if "send" in c)
    second = relay.send(req)
    sends_after_second = sum(1 for c in transport.calls if "send" in c)
    assert first.message_id == second.message_id
    assert sends_after_second == sends_after_first


def test_unknown_device_rejected(tmp_path: Path):
    relay, _ = _relay(tmp_path)
    with pytest.raises(UnknownDevice):
        relay.send(
            SendRequest(
                sender=NamespacedId("hetzner-rmthz", "/ac", "head", "t1"),
                recipient=NamespacedId("mystery-host", "/ac", "x", "t1"),
                body="no",
                data=None,
                idempotency_key="k",
                correlation_token="T",
            )
        )


def test_windows_target_queues_for_client_poll_not_native_binding(tmp_path: Path):
    relay, transport = _relay(tmp_path)
    receipt = relay.send(
        SendRequest(
            sender=NamespacedId("hetzner-rmthz", "/ac", "head", "t1", "s1"),
            recipient=NamespacedId("windows-desktop", "work/agent-coordination", "windows-codex", "t1"),
            body="hello windows",
            data=None,
            idempotency_key="win-1",
            correlation_token="WIN",
            originating_agent=NamespacedId("hetzner-rmthz", "/ac", "head", "t1", "s1"),
            bridge_device_id="hetzner-rmthz",
        )
    )
    assert receipt.delivery == "queued_client_poll"
    assert receipt.catalog_resolved_session_id is None
    assert not any("send" in c for c in transport.calls)
    pending = relay.store.pending_outbox()
    assert pending and pending[0]["queued_for_client_poll"] is True


def test_windows_device_has_no_native_catalog():
    registry = DeviceRegistry.load(EXAMPLE)
    windows = registry.get("windows-desktop")
    assert windows.can_run_aplexer() is False
    with pytest.raises(NativeBindingMissing):
        from coordination.catalog import resolve_catalog

        resolve_catalog(windows, lambda d, a: "[]")


def test_localhost_fake_is_not_cross_computer_proof():
    # Marker assertion: this module's FakeTransport never opens SSH.
    assert FakeTransport.run is not None
    assert "not cross-computer proof" in (__doc__ or "")
