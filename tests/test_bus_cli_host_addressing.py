import json
import pytest
from pathlib import Path

from coordination.bus_cli import main
from coordination.device_registry import DeviceRegistry
from coordination.errors import UnknownDevice

EXAMPLE_REGISTRY = Path(__file__).resolve().parents[1] / "examples" / "devices.example.json"


def test_registration_with_device_identity(tmp_path: Path, capsys: pytest.CaptureFixture):
    store = tmp_path / "store"
    cred_file1 = tmp_path / "cred1.json"
    cred_file2 = tmp_path / "cred2.json"

    # 1. Register with --device
    ret1 = main([
        "--store", str(store),
        "register",
        "--agent", "agent-hetzner",
        "--device", "hetzner-rmthz",
        "--cred", str(cred_file1),
        "--json",
    ])
    assert ret1 == 0
    out1, _ = capsys.readouterr()
    res1 = json.loads(out1)
    assert res1["agent_name"] == "agent-hetzner"
    assert res1["device_id"] == "hetzner-rmthz"
    assert cred_file1.exists()
    cred1 = json.loads(cred_file1.read_text(encoding="utf-8"))
    assert cred1["device_id"] == "hetzner-rmthz"

    # 2. Register with --target-device
    ret2 = main([
        "--store", str(store),
        "register",
        "--agent", "agent-windows",
        "--target-device", "windows-desktop",
        "--cred", str(cred_file2),
        "--json",
    ])
    assert ret2 == 0
    out2, _ = capsys.readouterr()
    res2 = json.loads(out2)
    assert res2["agent_name"] == "agent-windows"
    assert res2["device_id"] == "windows-desktop"
    assert cred_file2.exists()
    cred2 = json.loads(cred_file2.read_text(encoding="utf-8"))
    assert cred2["device_id"] == "windows-desktop"

    # 3. Sessionless worker registration with device identity
    cred_worker = tmp_path / "cred_worker.json"
    ret3 = main([
        "--store", str(store),
        "worker-register",
        "--agent", "worker-hetzner",
        "--device", "hetzner-rmthz",
        "--cred", str(cred_worker),
        "--json",
    ])
    assert ret3 == 0
    out3, _ = capsys.readouterr()
    res3 = json.loads(out3)
    assert res3["namespaced_id"]["device_id"] == "hetzner-rmthz"
    assert res3["namespaced_id"]["session_id"] is None


def test_sending_message_with_explicit_remote_host_device_target(tmp_path: Path, capsys: pytest.CaptureFixture):
    store = tmp_path / "store"
    cred_sender = tmp_path / "sender.json"
    cred_recipient = tmp_path / "recipient.json"

    # Register sender on hetzner-rmthz
    assert main([
        "--store", str(store),
        "register",
        "--agent", "sender-proc",
        "--device", "hetzner-rmthz",
        "--cred", str(cred_sender),
    ]) == 0
    capsys.readouterr()

    # Register recipient on windows-desktop
    assert main([
        "--store", str(store),
        "register",
        "--agent", "windows-listener",
        "--device", "windows-desktop",
        "--cred", str(cred_recipient),
    ]) == 0
    capsys.readouterr()
    recip_id = json.loads(cred_recipient.read_text())["identity_id"]

    # Send message with explicit remote host/device target
    ret_send = main([
        "--store", str(store),
        "send",
        "--cred", str(cred_sender),
        "--to", recip_id,
        "--target-device", "windows-desktop",
        "--body", "coordinate cross-computer task",
        "--data", '{"task": "build-win"}',
        "--json",
    ])
    assert ret_send == 0
    out_send, _ = capsys.readouterr()
    msg_sent = json.loads(out_send)
    assert msg_sent["body"] == "coordinate cross-computer task"
    data = msg_sent["data"]
    assert data["target_device"] == "windows-desktop"
    assert data["task"] == "build-win"

    # Verify no synthetic session: session_id is None / '-'
    assert data["destination_namespaced"]["session_id"] is None
    assert data["destination_namespaced"]["device_id"] == "windows-desktop"
    assert data["originating_agent"]["session_id"] is None
    assert data["originating_agent"]["device_id"] == "hetzner-rmthz"

    # Recipient checks inbox with --target-device windows-desktop
    ret_inbox = main([
        "--store", str(store),
        "inbox",
        "--cred", str(cred_recipient),
        "--target-device", "windows-desktop",
        "--json",
    ])
    assert ret_inbox == 0
    out_inbox, _ = capsys.readouterr()
    inbox_items = json.loads(out_inbox)
    assert len(inbox_items) == 1
    assert inbox_items[0]["message_id"] == msg_sent["message_id"]

    # Also query inbox filtered by sender's device hetzner-rmthz
    ret_inbox_filter = main([
        "--store", str(store),
        "inbox",
        "--cred", str(cred_recipient),
        "--device", "hetzner-rmthz",
        "--json",
    ])
    assert ret_inbox_filter == 0
    out_filter, _ = capsys.readouterr()
    filter_items = json.loads(out_filter)
    assert len(filter_items) == 1
    assert filter_items[0]["message_id"] == msg_sent["message_id"]


def test_unknown_device_fails_closed_with_clear_error(tmp_path: Path, capsys: pytest.CaptureFixture):
    store = tmp_path / "store"
    cred_sender = tmp_path / "sender.json"
    cred_recipient = tmp_path / "recipient.json"

    assert main([
        "--store", str(store),
        "register",
        "--agent", "sender-proc",
        "--device", "hetzner-rmthz",
        "--cred", str(cred_sender),
    ]) == 0
    capsys.readouterr()

    assert main([
        "--store", str(store),
        "register",
        "--agent", "recip-proc",
        "--device", "hetzner-rmthz",
        "--cred", str(cred_recipient),
    ]) == 0
    capsys.readouterr()
    recip_id = json.loads(cred_recipient.read_text())["identity_id"]

    # 1. Send with unknown target device (--json) fails closed
    ret_unknown = main([
        "--store", str(store),
        "send",
        "--cred", str(cred_sender),
        "--to", recip_id,
        "--target-device", "unregistered-rogue-host",
        "--body", "malicious message",
        "--json",
    ])
    assert ret_unknown != 0
    out_err, _ = capsys.readouterr()
    err_json = json.loads(out_err)
    assert err_json["code"] == "unknown_device"
    assert "unregistered-rogue-host" in err_json["message"]

    # 2. Send with unknown target device (without --json) prints clear error to stderr and returns != 0
    ret_unknown_text = main([
        "--store", str(store),
        "send",
        "--cred", str(cred_sender),
        "--to", recip_id,
        "--device", "unregistered-rogue-host-2",
        "--body", "test body",
    ])
    assert ret_unknown_text != 0
    _, err_text = capsys.readouterr()
    assert "unknown_device:unregistered-rogue-host-2" in err_text

    # 3. Inbox with unknown target device fails closed
    ret_inbox_err = main([
        "--store", str(store),
        "inbox",
        "--cred", str(cred_sender),
        "--target-device", "unregistered-rogue-host",
        "--json",
    ])
    assert ret_inbox_err != 0
    out_inbox_err, _ = capsys.readouterr()
    err_inbox_json = json.loads(out_inbox_err)
    assert err_inbox_json["code"] == "unknown_device"


def test_target_device_mismatch_fails_closed(tmp_path: Path, capsys: pytest.CaptureFixture):
    store = tmp_path / "store"
    cred_sender = tmp_path / "sender.json"
    cred_recipient = tmp_path / "recipient.json"

    assert main([
        "--store", str(store),
        "register",
        "--agent", "sender-proc",
        "--device", "hetzner-rmthz",
        "--cred", str(cred_sender),
    ]) == 0
    assert main([
        "--store", str(store),
        "register",
        "--agent", "recip-proc",
        "--device", "windows-desktop",
        "--cred", str(cred_recipient),
    ]) == 0
    capsys.readouterr()
    recip_id = json.loads(cred_recipient.read_text())["identity_id"]

    # Recipient is on windows-desktop, but sender addresses hetzner-rmthz explicitly
    ret_mismatch = main([
        "--store", str(store),
        "send",
        "--cred", str(cred_sender),
        "--to", recip_id,
        "--target-device", "hetzner-rmthz",
        "--body", "mismatch payload",
        "--json",
    ])
    assert ret_mismatch != 0
    out_mismatch, _ = capsys.readouterr()
    res = json.loads(out_mismatch)
    assert "Target device mismatch" in res["message"]


def test_worker_bus_explicit_device_targeting(tmp_path: Path, capsys: pytest.CaptureFixture):
    store = tmp_path / "store"
    cred_w1 = tmp_path / "w1.json"
    cred_w2 = tmp_path / "w2.json"

    # Worker 1 on hetzner-rmthz
    assert main([
        "--store", str(store),
        "worker-register",
        "--agent", "worker-1",
        "--device", "hetzner-rmthz",
        "--cred", str(cred_w1),
    ]) == 0
    # Worker 2 on windows-desktop
    assert main([
        "--store", str(store),
        "worker-register",
        "--agent", "worker-2",
        "--target-device", "windows-desktop",
        "--cred", str(cred_w2),
    ]) == 0
    capsys.readouterr()
    w2_id = json.loads(cred_w2.read_text())["identity_id"]

    # Worker 1 sends to Worker 2 on windows-desktop
    ret_w_send = main([
        "--store", str(store),
        "worker-send",
        "--cred", str(cred_w1),
        "--to", w2_id,
        "--target-device", "windows-desktop",
        "--body", "worker task payload",
        "--json",
    ])
    assert ret_w_send == 0
    out_w_send, _ = capsys.readouterr()
    send_dict = json.loads(out_w_send)
    assert send_dict["message"]["body"] == "worker task payload"
    msg_id = send_dict["message"]["message_id"]

    # Worker 2 receives targeting windows-desktop
    ret_w_recv = main([
        "--store", str(store),
        "worker-receive",
        "--cred", str(cred_w2),
        "--target-device", "windows-desktop",
        "--json",
    ])
    assert ret_w_recv == 0
    out_w_recv, _ = capsys.readouterr()
    msgs = json.loads(out_w_recv)
    assert len(msgs) == 1
    assert msgs[0]["message_id"] == msg_id

    # Worker 2 ACKs
    ret_ack = main([
        "--store", str(store),
        "worker-ack",
        "--cred", str(cred_w2),
        "--message-id", msg_id,
        "--json",
    ])
    assert ret_ack == 0
    out_ack, _ = capsys.readouterr()
    ack_res = json.loads(out_ack)
    assert ack_res["state"] == "recipient_read_ack"


def test_custom_registry_path_validation(tmp_path: Path, capsys: pytest.CaptureFixture):
    store = tmp_path / "store"
    cred_sender = tmp_path / "sender.json"
    cred_recipient = tmp_path / "recipient.json"

    # Create custom registry with only 'custom-node-alpha'
    custom_reg = tmp_path / "custom_devices.json"
    custom_reg.write_text(json.dumps({
        "devices": [
            {
                "id": "custom-node-alpha",
                "kind": "aplexer-host",
                "hostname": "alpha.local",
                "role": "custom-worker",
                "workspace_roots": [],
                "native_aplexer": True,
                "outbound_ssh_only": False,
            }
        ]
    }), encoding="utf-8")

    assert main([
        "--store", str(store),
        "--registry", str(custom_reg),
        "register",
        "--agent", "custom-sender",
        "--device", "custom-node-alpha",
        "--cred", str(cred_sender),
    ]) == 0

    assert main([
        "--store", str(store),
        "--registry", str(custom_reg),
        "register",
        "--agent", "custom-recip",
        "--device", "custom-node-alpha",
        "--cred", str(cred_recipient),
    ]) == 0
    capsys.readouterr()
    recip_id = json.loads(cred_recipient.read_text())["identity_id"]

    # Target custom-node-alpha succeeds
    ret_ok = main([
        "--store", str(store),
        "--registry", str(custom_reg),
        "send",
        "--cred", str(cred_sender),
        "--to", recip_id,
        "--target-device", "custom-node-alpha",
        "--body", "custom payload",
        "--json",
    ])
    assert ret_ok == 0
    capsys.readouterr()

    # Target hetzner-rmthz (which is not in custom_reg) fails closed
    ret_fail = main([
        "--store", str(store),
        "--registry", str(custom_reg),
        "send",
        "--cred", str(cred_sender),
        "--to", recip_id,
        "--target-device", "hetzner-rmthz",
        "--body", "should fail",
        "--json",
    ])
    assert ret_fail != 0
    out_fail, _ = capsys.readouterr()
    err_res = json.loads(out_fail)
    assert err_res["code"] == "unknown_device"
