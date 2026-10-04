from coordination.envelope import ActionOutcome, NamespacedId, ReadAck, SendReceipt, TransportState


def test_namespaced_id_includes_device_workspace_agent_task():
    ident = NamespacedId(
        device_id="hetzner-rmthz",
        workspace="/home/alexey/git/agent-coordination",
        agent_tag="agent-coordination-head",
        task_id="ac-relay-mvp",
        session_id="81e8010c-89e4-478b-be3a-4ee6991607f3",
    )
    rendered = ident.render()
    assert rendered.startswith("hetzner-rmthz/")
    assert "agent-coordination-head" in rendered
    assert "ac-relay-mvp" in rendered


def test_receipt_read_ack_and_outcome_are_distinct_states():
    sender = NamespacedId("a", "/w", "head", "t1", "s1")
    recipient = NamespacedId("b", "/w", "peer", "t1", "s2")
    receipt = SendReceipt(
        message_id="m1",
        idempotency_key="k1",
        sender=sender,
        recipient=recipient,
        delivery="inbox",
        recorded_at="2026-10-04T11:46:00Z",
        catalog_resolved_session_id="s2",
        catalog_observed_at="2026-10-04T11:46:00Z",
        bridge_device_id="hetzner-rmthz",
        originating_agent=sender,
    )
    ack = ReadAck("m1", recipient, "2026-10-04T11:47:00Z")
    outcome = ActionOutcome("m1", "C1341", "m2", agreed=True, completed=False)
    done = ActionOutcome("m1", "C1341", "m2", agreed=True, completed=True, evidence_paths=["tests/"])
    assert receipt.state is TransportState.SEND_RECEIPT
    assert ack.state is TransportState.RECIPIENT_READ_ACK
    assert outcome.to_dict()["state"] == TransportState.SEMANTIC_AGREED.value
    assert done.to_dict()["state"] == TransportState.ACTION_COMPLETED.value
    assert receipt.state != ack.state
    assert ack.state != outcome.state
