import pytest

from coordination.ql_consumer_fencing import (
    Fenced,
    QLConsumerFencing,
    reject_head_cred_inheritance,
)
from coordination.role_failover import RoleAuthority


@pytest.fixture
def test_setup(tmp_path):
    now = [1000.0]
    auth = RoleAuthority(tmp_path / "roles.db", lambda: now[0])
    fencing = QLConsumerFencing(auth)
    return auth, fencing, now


def enroll_agent(auth, actor, generation="g1", priority=1, **extra):
    auth.observe(
        actor,
        "hetzner",
        generation,
        ready=True,
        draft=False,
        quota_ok=True,
        priority=priority,
        **extra,
    )


def test_valid_enqueue_under_current_epoch(test_setup):
    """Verifies successful enqueue when epoch and credentials are valid."""
    auth, fencing, now = test_setup
    auth.configure("project-x", "principal", ["agent-a"])
    enroll_agent(auth, "agent-a")
    elect_result = auth.tick("project-x", "principal")
    assert elect_result["state"] == "elected"
    assert elect_result["epoch"] == 1

    # Record valid activation
    auth.activation(
        "project-x",
        "principal",
        "agent-a",
        "g1",
        1,
        role_ack="ack-alpha",
        first_action="tool-dispatch",
    )

    launched = []

    def mock_launcher(key, payload):
        launched.append((key, payload))
        return {"state": "queued", "task_id": payload["id"], "key": key}

    payload = {"id": "task-42", "goal": "run-fenced-pipeline", "timeout": 300}
    outcome = fencing.admit_and_enqueue_task(
        project="project-x",
        role="principal",
        actor="agent-a",
        generation="g1",
        epoch=1,
        task_id="task-42",
        payload=payload,
        launcher_submit_fn=mock_launcher,
    )

    assert outcome["state"] == "queued"
    assert outcome["task_id"] == "task-42"
    assert outcome["key"] == "ql-task:project-x:principal:1:task-42"
    assert len(launched) == 1
    assert launched[0][0] == "ql-task:project-x:principal:1:task-42"
    assert launched[0][1] == payload


def test_stale_principal_fenced_after_takeover(test_setup):
    """Verifies that when an election promotes a successor (incrementing epoch),

    the former holder's enqueue fails closed with Fenced.
    """
    auth, fencing, now = test_setup
    auth.configure("project-x", "principal", ["incumbent-a", "successor-b"])
    enroll_agent(auth, "incumbent-a", priority=0)
    enroll_agent(auth, "successor-b", priority=1)

    assert auth.tick("project-x", "principal")["holder"] == "incumbent-a"
    auth.activation(
        "project-x",
        "principal",
        "incumbent-a",
        "g1",
        1,
        role_ack="ack-incumbent",
        first_action="tool-init",
    )

    # Lease expires on incumbent
    now[0] += 181
    enroll_agent(auth, "successor-b")
    diag = auth.tick("project-x", "principal")
    assert diag["state"] == "diagnosing"

    # Past diagnosis grace period, promote successor-b
    now[0] += 121
    enroll_agent(auth, "successor-b")
    promoted = auth.tick("project-x", "principal")
    assert promoted["state"] == "elected"
    assert promoted["holder"] == "successor-b"
    assert promoted["epoch"] == 2

    auth.activation(
        "project-x",
        "principal",
        "successor-b",
        "g1",
        2,
        role_ack="ack-successor",
        first_action="tool-init",
    )

    launched = []

    def mock_launcher(key, payload):
        launched.append((key, payload))
        return {"state": "queued"}

    # Former holder incumbent-a attempts to enqueue under stale epoch 1 -> fails closed with Fenced
    with pytest.raises(Fenced):
        fencing.admit_and_enqueue_task(
            project="project-x",
            role="principal",
            actor="incumbent-a",
            generation="g1",
            epoch=1,
            task_id="stale-work-1",
            payload={"id": "stale-work-1"},
            launcher_submit_fn=mock_launcher,
        )

    # Former holder incumbent-a attempts to spoof epoch 2 -> fails closed with Fenced
    with pytest.raises(Fenced):
        fencing.admit_and_enqueue_task(
            project="project-x",
            role="principal",
            actor="incumbent-a",
            generation="g1",
            epoch=2,
            task_id="stale-work-2",
            payload={"id": "stale-work-2"},
            launcher_submit_fn=mock_launcher,
        )

    assert len(launched) == 0

    # Promoted successor-b can successfully enqueue under epoch 2
    ok_res = fencing.admit_and_enqueue_task(
        project="project-x",
        role="principal",
        actor="successor-b",
        generation="g1",
        epoch=2,
        task_id="successor-work-1",
        payload={"id": "successor-work-1"},
        launcher_submit_fn=mock_launcher,
    )
    assert ok_res["state"] == "queued"
    assert len(launched) == 1


def test_deduplicate_launch_intents(test_setup):
    """Verifies calling enqueue again with the same task_id returns

    {'state': 'already_enqueued'} without invoking the launcher twice.
    """
    auth, fencing, now = test_setup
    auth.configure("project-x", "principal", ["agent-a"])
    enroll_agent(auth, "agent-a")
    auth.tick("project-x", "principal")
    auth.activation(
        "project-x",
        "principal",
        "agent-a",
        "g1",
        1,
        role_ack="ack-a",
        first_action="first-tool",
    )

    call_count = 0

    def mock_launcher(key, payload):
        nonlocal call_count
        call_count += 1
        return {"state": "queued", "task_id": payload["id"]}

    payload = {"id": "idempotent-task-1", "action": "build"}

    # First admission and enqueue
    res1 = fencing.admit_and_enqueue_task(
        project="project-x",
        role="principal",
        actor="agent-a",
        generation="g1",
        epoch=1,
        task_id="idempotent-task-1",
        payload=payload,
        launcher_submit_fn=mock_launcher,
    )
    assert res1 == {"state": "queued", "task_id": "idempotent-task-1"}
    assert call_count == 1

    # Duplicate call with identical task_id
    res2 = fencing.admit_and_enqueue_task(
        project="project-x",
        role="principal",
        actor="agent-a",
        generation="g1",
        epoch=1,
        task_id="idempotent-task-1",
        payload=payload,
        launcher_submit_fn=mock_launcher,
    )
    assert res2 == {"state": "already_enqueued"}
    assert call_count == 1  # Launcher was NOT invoked again


def test_reject_head_cred_inheritance(test_setup):
    """Verifies payloads containing 'head.cred' or head token are rejected with ValueError or Fenced."""
    auth, fencing, now = test_setup
    auth.configure("project-x", "principal", ["agent-a"])
    enroll_agent(auth, "agent-a")
    auth.tick("project-x", "principal")
    auth.activation(
        "project-x",
        "principal",
        "agent-a",
        "g1",
        1,
        role_ack="ack-a",
        first_action="first-tool",
    )

    launched = []

    def mock_launcher(key, payload):
        launched.append(payload)
        return {"state": "queued"}

    # 1. Payload with 'head.cred'
    with pytest.raises((ValueError, Fenced)):
        fencing.admit_and_enqueue_task(
            project="project-x",
            role="principal",
            actor="agent-a",
            generation="g1",
            epoch=1,
            task_id="cred-task-1",
            payload={"id": "cred-task-1", "head.cred": "secret-head-token-123"},
            launcher_submit_fn=mock_launcher,
        )

    # 2. Payload with 'head_cred'
    with pytest.raises((ValueError, Fenced)):
        fencing.admit_and_enqueue_task(
            project="project-x",
            role="principal",
            actor="agent-a",
            generation="g1",
            epoch=1,
            task_id="cred-task-2",
            payload={"id": "cred-task-2", "head_cred": "secret-head-token-456"},
            launcher_submit_fn=mock_launcher,
        )

    # 3. Payload with 'head_token'
    with pytest.raises((ValueError, Fenced)):
        fencing.admit_and_enqueue_task(
            project="project-x",
            role="principal",
            actor="agent-a",
            generation="g1",
            epoch=1,
            task_id="cred-task-3",
            payload={"id": "cred-task-3", "head_token": "bearer-head-token"},
            launcher_submit_fn=mock_launcher,
        )

    # 4. Nested head token
    with pytest.raises((ValueError, Fenced)):
        fencing.admit_and_enqueue_task(
            project="project-x",
            role="principal",
            actor="agent-a",
            generation="g1",
            epoch=1,
            task_id="cred-task-4",
            payload={"id": "cred-task-4", "head": {"token": "secret-nested"}},
            launcher_submit_fn=mock_launcher,
        )

    # 5. Direct helper tests
    with pytest.raises((ValueError, Fenced)):
        reject_head_cred_inheritance({"head.cred": "leak"}, reject=True)

    with pytest.raises((ValueError, Fenced)):
        reject_head_cred_inheritance({"head": {"cred": "leak"}}, reject=True)

    # With reject=False, credentials are stripped
    cleaned = reject_head_cred_inheritance(
        {"id": "clean-me", "head.cred": "leak", "head_token": "leak2", "safe": "val"},
        reject=False,
    )
    assert "head.cred" not in cleaned
    assert "head_token" not in cleaned
    assert cleaned["id"] == "clean-me"
    assert cleaned["safe"] == "val"

    # Launcher was never called for any rejected attempts
    assert len(launched) == 0


def test_gated_replacement_startup_single_instance(test_setup):
    """Verifies exactly one replacement task is launched per epoch."""
    auth, fencing, now = test_setup
    auth.configure("project-x", "principal", ["agent-a"])
    enroll_agent(auth, "agent-a")
    auth.tick("project-x", "principal")

    launched = []

    def mock_launcher(key, payload):
        launched.append((key, payload))
        return {"state": "queued", "task_id": payload["id"]}

    plan = {"id": "replacement-worker-1", "goal": "restore-service"}

    # Unactivated caller fails closed
    with pytest.raises(Fenced):
        fencing.gated_replacement_startup(
            project="project-x",
            role="principal",
            caller_actor="agent-a",
            caller_gen="g1",
            caller_epoch=1,
            replacement_plan=plan,
            launcher_submit_fn=mock_launcher,
        )
    assert len(launched) == 0

    # Activate agent-a
    auth.activation(
        "project-x",
        "principal",
        "agent-a",
        "g1",
        1,
        role_ack="ack-a",
        first_action="first-tool",
    )

    # First launch under epoch 1 succeeds
    out1 = fencing.gated_replacement_startup(
        project="project-x",
        role="principal",
        caller_actor="agent-a",
        caller_gen="g1",
        caller_epoch=1,
        replacement_plan=plan,
        launcher_submit_fn=mock_launcher,
    )
    assert out1 == {"state": "queued", "task_id": "replacement-worker-1"}
    assert len(launched) == 1
    assert launched[0][0] == "ql-replace:project-x:principal:1"

    # Second launch attempt in the same epoch is deduplicated
    out2 = fencing.gated_replacement_startup(
        project="project-x",
        role="principal",
        caller_actor="agent-a",
        caller_gen="g1",
        caller_epoch=1,
        replacement_plan=plan,
        launcher_submit_fn=mock_launcher,
    )
    assert out2 == {"state": "already_enqueued"}
    assert len(launched) == 1  # Exactly one launch!

    # Stale caller fails closed
    with pytest.raises(Fenced):
        fencing.gated_replacement_startup(
            project="project-x",
            role="principal",
            caller_actor="agent-a",
            caller_gen="g1",
            caller_epoch=0,
            replacement_plan=plan,
            launcher_submit_fn=mock_launcher,
        )


def test_validate_consumer_epoch(test_setup):
    """Verifies stale epoch check fails closed."""
    auth, fencing, now = test_setup
    auth.configure("project-x", "principal", ["agent-a"])
    enroll_agent(auth, "agent-a")
    auth.tick("project-x", "principal")
    auth.activation(
        "project-x",
        "principal",
        "agent-a",
        "g1",
        1,
        role_ack="ack-a",
        first_action="first-tool",
    )

    # Valid current epoch and holder
    assert fencing.validate_consumer_epoch("project-x", "principal", "agent-a", "g1", 1) is True

    # Stale epoch (older)
    assert fencing.validate_consumer_epoch("project-x", "principal", "agent-a", "g1", 0) is False

    # Stale epoch (future / unreached)
    assert fencing.validate_consumer_epoch("project-x", "principal", "agent-a", "g1", 2) is False

    # Wrong actor identity
    assert fencing.validate_consumer_epoch("project-x", "principal", "impostor", "g1", 1) is False

    # Wrong runtime generation
    assert fencing.validate_consumer_epoch("project-x", "principal", "agent-a", "g2", 1) is False

    # Unconfigured project / role
    assert fencing.validate_consumer_epoch("unknown-proj", "principal", "agent-a", "g1", 1) is False

    # Lease expiration / suspected lease causes validation to fail closed
    now[0] += 181
    assert fencing.validate_consumer_epoch("project-x", "principal", "agent-a", "g1", 1) is False
