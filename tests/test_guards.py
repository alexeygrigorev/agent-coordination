import pytest

from coordination.catalog import CatalogEntry
from coordination.errors import GuardRejected
from coordination.guards import DeliveryMode, inspect_delivery_guard


def _entry(state: str | None, phase: str = "running") -> CatalogEntry:
    return CatalogEntry("sid", "peer", "/ws", "codex", state, phase)


def test_inbox_always_allowed():
    decision = inspect_delivery_guard(_entry("working"), DeliveryMode.INBOX)
    assert decision.allow_pane is False
    assert decision.reason == "inbox_default"


def test_busy_and_draft_and_unknown_reject_pane():
    with pytest.raises(GuardRejected):
        inspect_delivery_guard(_entry("working"), DeliveryMode.PANE, composer_empty=True)
    with pytest.raises(GuardRejected):
        inspect_delivery_guard(
            _entry("idle"),
            DeliveryMode.PANE,
            composer_empty=True,
            human_draft_present=True,
        )
    with pytest.raises(GuardRejected):
        inspect_delivery_guard(_entry(None), DeliveryMode.PANE, composer_empty=True)


def test_native_readiness_absent_refuses_pane_even_if_idle():
    with pytest.raises(GuardRejected) as rejected:
        inspect_delivery_guard(
            _entry("idle"),
            DeliveryMode.PANE,
            composer_empty=True,
            readiness_subcommand_available=False,
        )
    assert "native_readiness_absent" in str(rejected.value)
