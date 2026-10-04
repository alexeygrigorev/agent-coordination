from __future__ import annotations

import json
import pytest

from adapters.aplexer_ssh import (
    cmd_devices,
    main as aplexer_ssh_main,
    validate_no_from_spoof,
)
from adapters.windows_client import (
    IdentitySpoofError,
    OriginatingAgent,
    PollMessage,
    ReceiptMissingError,
    SendReceipt,
    TypedRpcRequest,
    TypedRpcResponse,
    handle_rpc_line,
    main as windows_client_main,
    send_message,
)


def test_aplexer_ssh_devices_command(capsys):
    ret = aplexer_ssh_main(["--registry", "examples/devices.example.json", "devices"])
    assert ret == 0
    out = capsys.readouterr().out
    devices = json.loads(out)
    assert any(d["id"] == "hetzner-rmthz" for d in devices)
    assert any(d["id"] == "windows-desktop" for d in devices)


def test_aplexer_ssh_anti_spoofing():
    # Matching caller identity succeeds
    validate_no_from_spoof(from_tag="agent-a", caller_tag="agent-a")
    validate_no_from_spoof(from_tag=None, caller_tag="agent-a")

    # Mismatched caller identity raises ValueError
    with pytest.raises(ValueError, match="Identity spoofing forbidden"):
        validate_no_from_spoof(from_tag="spoofed-tag", caller_tag="legit-tag")


def test_aplexer_ssh_pane_injection_rejected(capsys):
    # If --pane is passed to send, it must be rejected with exit code 1 and error JSON
    ret = aplexer_ssh_main([
        "send",
        "--workspace", "/home/alexey/git/agent-coordination",
        "--to", "target",
        "--body", "test",
        "--pane",
    ])
    assert ret == 1
    out = capsys.readouterr().out
    assert "Pane injection is forbidden" in out


def test_windows_client_originating_agent_validation():
    # Valid agent with session_id=None
    agent = OriginatingAgent(
        device_id="windows-desktop",
        workspace="work/agent-coordination",
        tag="windows-codex",
    )
    agent.validate()
    d = agent.to_dict()
    assert d["device_id"] == "windows-desktop"
    assert "session_id" not in d

    # Invented Windows aplexer session ID must be rejected!
    forged = OriginatingAgent(
        device_id="windows-desktop",
        workspace="work/agent-coordination",
        tag="windows-codex",
        session_id="invented-session-uuid-1234",
    )
    with pytest.raises(IdentitySpoofError, match="Invented Windows aplexer session ID forbidden"):
        forged.validate()


def test_windows_client_fail_closed_missing_receipt(monkeypatch):
    agent = OriginatingAgent()

    # Monkeypatch ssh_run to simulate remote returning no message ID
    monkeypatch.setattr(
        "adapters.windows_client.ssh_run",
        lambda alias, argv, **kw: json.dumps({"status": "ok"}),  # No "id"
    )

    with pytest.raises(ReceiptMissingError, match="missing durable message ID"):
        send_message(
            alias="hetzner",
            workspace="/home/alexey/git/agent-coordination",
            to="agent-coordination-head",
            body="ping",
            token="TOK-1",
            idempotency_key="KEY-1",
            origin=agent,
        )


def test_windows_client_success_receipt(monkeypatch):
    agent = OriginatingAgent()

    monkeypatch.setattr(
        "adapters.windows_client.ssh_run",
        lambda alias, argv, **kw: json.dumps({
            "id": "01msg1234567890",
            "delivery": "inbox",
            "created_at": 1791115000,
        }),
    )

    receipt = send_message(
        alias="hetzner",
        workspace="/home/alexey/git/agent-coordination",
        to="agent-coordination-head",
        body="ping",
        token="TOK-1",
        idempotency_key="KEY-1",
        origin=agent,
    )
    assert receipt.message_id == "01msg1234567890"
    assert receipt.idempotency_key == "KEY-1"
    assert receipt.correlation_token == "TOK-1"
    assert receipt.originating_agent["device_id"] == "windows-desktop"
    assert receipt.bridge_device_id == "hetzner-rmthz"


def test_windows_client_handle_rpc_line():
    # Unknown method
    res = json.loads(handle_rpc_line(json.dumps({"method": "bogus"})))
    assert not res["success"]
    assert res["error"]["code"] == "unknown_method"
