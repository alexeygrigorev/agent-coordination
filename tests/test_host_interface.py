from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from coordination.errors import GuardRejected, UnknownDevice
from coordination.host_interface import (
    MultiHostAdmission,
    admit_host_task,
    emit_host_event,
    query_host_events,
    reject_head_cred_inheritance,
)


def test_admit_hetzner_host():
    """Verifies local execution target and <=1500M memory limit for Hetzner host."""
    adm = MultiHostAdmission()

    # 1. Memory exceeding 1500M is capped to <= 1500M
    decision = adm.admit_host_task(
        "hetzner-rmthz",
        "task-hetzner-large-mem",
        payload={"memory_mb": 4096},
    )
    assert decision["admitted"] is True
    assert decision["device_id"] == "hetzner-rmthz"
    assert decision["execution_target"] == "hetzner-rmthz"
    assert decision["delivery"] == "local_task_unit"
    assert decision["memory_mb"] <= 1500
    assert decision["memory_mb"] == 1500

    # 2. String memory exceeding 1500M is also capped
    decision_str = adm.admit_host_task(
        "hetzner-rmthz",
        "task-hetzner-str-mem",
        payload={"memory_limit": "2G"},
    )
    assert decision_str["memory_mb"] <= 1500
    assert decision_str["memory_mb"] == 1500

    # 3. Memory below 1500M is preserved
    decision_low = adm.admit_host_task(
        "hetzner-rmthz",
        "task-hetzner-low-mem",
        payload={"memory_mb": 512},
    )
    assert decision_low["memory_mb"] == 512
    assert decision_low["memory_mb"] <= 1500

    # 4. Default memory is <= 1500M
    decision_default = adm.admit_host_task(
        "hetzner-rmthz",
        "task-hetzner-default-mem",
        payload={},
    )
    assert decision_default["execution_target"] == "hetzner-rmthz"
    assert decision_default["delivery"] == "local_task_unit"
    assert decision_default["memory_mb"] <= 1500


def test_admit_windows_host():
    """Verifies execution_target='hetzner-rmthz', session_id=None, sessionless bus delivery."""
    adm = MultiHostAdmission()

    # 1. Basic Windows task admission
    decision = adm.admit_host_task(
        "windows-desktop",
        "task-win-001",
        payload={"command": "build"},
    )
    assert decision["admitted"] is True
    assert decision["device_id"] == "windows-desktop"
    assert decision["execution_target"] == "hetzner-rmthz"
    assert decision["session_id"] is None
    assert decision["delivery"] == "sessionless_worker_bus"

    # 2. Even if caller provides session_id, Windows host strictly enforces session_id=None
    decision_with_session = adm.admit_host_task(
        "windows-desktop",
        "task-win-002",
        payload={"session_id": "invented-windows-session", "command": "test"},
    )
    assert decision_with_session["admitted"] is True
    assert decision_with_session["execution_target"] == "hetzner-rmthz"
    assert decision_with_session["session_id"] is None
    assert decision_with_session["delivery"] == "sessionless_worker_bus"
    assert decision_with_session["payload"]["session_id"] is None


def test_unknown_host_fails_closed():
    """Verifies UnknownDevice error raised on unregistered host."""
    adm = MultiHostAdmission()

    with pytest.raises(UnknownDevice) as excinfo:
        adm.admit_host_task("unregistered-laptop", "task-fail-001", {})

    assert excinfo.value.device_id == "unregistered-laptop"
    assert excinfo.value.code == "unknown_device"

    # Module-level function also fails closed
    with pytest.raises(UnknownDevice):
        admit_host_task("fake-node", "task-fail-002", {})


def test_reject_head_cred_inheritance():
    """Verifies payload with head.cred is rejected or stripped."""
    adm = MultiHostAdmission()

    payload_with_creds = {
        "job_name": "compile",
        "head.cred": "super-secret-token",
        "head_cred": "another-secret",
        "head": {
            "cred": "nested-token",
            "agent_tag": "coordinator",
        },
    }

    # 1. Stripping behavior: credentials removed from admitted payload
    decision = adm.admit_host_task(
        "windows-desktop",
        "task-strip-cred",
        payload=payload_with_creds,
    )
    assert decision["admitted"] is True
    assert "head.cred" not in decision["payload"]
    assert "head_cred" not in decision["payload"]
    assert "cred" not in decision["payload"]["head"]
    assert decision["payload"]["head"]["agent_tag"] == "coordinator"
    assert decision["payload"]["job_name"] == "compile"

    # 2. Rejecting behavior: raises GuardRejected when reject_on_cred=True
    with pytest.raises(GuardRejected) as excinfo:
        adm.admit_host_task(
            "windows-desktop",
            "task-reject-cred",
            payload=payload_with_creds,
            reject_on_cred=True,
        )
    assert "head_cred_inheritance_rejected" in str(excinfo.value)

    # 3. Direct reject_head_cred_inheritance helper tests
    cleaned = reject_head_cred_inheritance(payload_with_creds, reject=False)
    assert "head.cred" not in cleaned
    assert "head_cred" not in cleaned
    assert "cred" not in cleaned["head"]
    assert cleaned["head"]["agent_tag"] == "coordinator"

    with pytest.raises(GuardRejected):
        reject_head_cred_inheritance(payload_with_creds, reject=True)


def test_emit_and_query_host_events(tmp_path: Path):
    """Verifies atomic JSONL event emission and query capabilities."""
    events_dir = tmp_path / "events"

    # 1. Emit single event
    evt1 = emit_host_event(
        event_type="host_admitted",
        device_id="hetzner-rmthz",
        task_id="t-001",
        details={"status": "admitted", "memory_mb": 1500},
        events_dir=events_dir,
    )
    assert evt1["event_type"] == "host_admitted"
    assert evt1["device_id"] == "hetzner-rmthz"
    assert evt1["task_id"] == "t-001"
    assert "timestamp" in evt1
    assert evt1["timestamp"].endswith("Z")

    # 2. Emit second event via class instance
    adm = MultiHostAdmission(events_dir=events_dir)
    evt2 = adm.emit_host_event(
        event_type="host_admitted",
        device_id="windows-desktop",
        task_id="t-002",
        details={"status": "admitted", "execution_target": "hetzner-rmthz"},
    )
    assert evt2["device_id"] == "windows-desktop"

    # 3. Query all events
    events = query_host_events(events_dir=events_dir)
    assert len(events) == 2
    assert events[0]["task_id"] == "t-001"
    assert events[1]["task_id"] == "t-002"

    # 4. Filtered query
    win_events = adm.query_host_events(device_id="windows-desktop")
    assert len(win_events) == 1
    assert win_events[0]["device_id"] == "windows-desktop"

    # 5. Verify atomic multi-threaded concurrent emissions
    def _emit_worker(worker_idx: int):
        for i in range(5):
            emit_host_event(
                event_type="worker_heartbeat",
                device_id="hetzner-rmthz",
                task_id=f"t-worker-{worker_idx}-{i}",
                details={"step": i},
                events_dir=events_dir,
            )

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(_emit_worker, idx) for idx in range(5)]
        for f in futures:
            f.result()

    all_events = query_host_events(events_dir=events_dir)
    # 2 initial + (5 workers * 5 events = 25) = 27 events
    assert len(all_events) == 27
    heartbeats = [e for e in all_events if e["event_type"] == "worker_heartbeat"]
    assert len(heartbeats) == 25
