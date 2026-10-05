import json
import pytest
from pathlib import Path

from coordination.bus_cli import main

def test_worker_bus_cli_flow(tmp_path: Path, capsys: pytest.CaptureFixture):
    store = tmp_path / "store"
    cred_file1 = tmp_path / "cred1.json"
    cred_file2 = tmp_path / "cred2.json"
    
    # 1. Register worker 1
    ret = main([
        "--store", str(store),
        "worker-register",
        "--agent", "worker-one",
        "--device", "dev-1",
        "--cred", str(cred_file1)
    ])
    assert ret == 0
    out, _ = capsys.readouterr()
    res1 = json.loads(out)
    assert res1["agent_name"] == "worker-one"
    assert cred_file1.exists()
    
    # 2. Register worker 2
    ret = main([
        "--store", str(store),
        "worker-register",
        "--agent", "worker-two",
        "--device", "dev-2",
        "--cred", str(cred_file2)
    ])
    assert ret == 0
    out, _ = capsys.readouterr()
    res2 = json.loads(out)
    w2_id = res2["identity_id"]
    
    # 3. Worker 1 sends message to Worker 2
    ret = main([
        "--store", str(store),
        "worker-send",
        "--cred", str(cred_file1),
        "--to", w2_id,
        "--body", "hello from worker 1",
        "--data", '{"key": "value"}'
    ])
    assert ret == 0
    out, _ = capsys.readouterr()
    send_out = json.loads(out)
    assert "message" in send_out
    assert "receipt" in send_out
    assert send_out["message"]["body"] == "hello from worker 1"
    assert send_out["message"]["data"]["key"] == "value"
    msg_id = send_out["message"]["message_id"]
    
    # 4. Worker 2 receives message
    ret = main([
        "--store", str(store),
        "worker-receive",
        "--cred", str(cred_file2)
    ])
    assert ret == 0
    out, _ = capsys.readouterr()
    recv_out = json.loads(out)
    assert len(recv_out) == 1
    assert recv_out[0]["message_id"] == msg_id
    
    # 5. Worker 2 ACKs message
    ret = main([
        "--store", str(store),
        "worker-ack",
        "--cred", str(cred_file2),
        "--message-id", msg_id
    ])
    assert ret == 0
    out, _ = capsys.readouterr()
    ack_out = json.loads(out)
    assert ack_out["message_id"] == msg_id
    assert ack_out["state"] == "recipient_read_ack"
    
    # 6. Worker 2 receives again (should be empty because unread_only=True by default)
    ret = main([
        "--store", str(store),
        "worker-receive",
        "--cred", str(cred_file2)
    ])
    assert ret == 0
    out, _ = capsys.readouterr()
    recv_out2 = json.loads(out)
    assert len(recv_out2) == 0
