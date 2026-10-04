"""Protected draft and busy-pane guards.

Installed aplexer has no `message readiness` subcommand (verified 2026-10-04).
Pane injection is refused unless an explicit empty-composer capture is supplied.
Default delivery is inbox-only.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .catalog import CatalogEntry
from .errors import GuardRejected


class DeliveryMode(str, Enum):
    INBOX = "inbox"
    PANE = "pane"
    PANE_OR_INBOX = "pane_or_inbox"


BUSY_STATES = frozenset({"working", "running"})
UNKNOWN_STATES = frozenset({None, "", "unknown"})


@dataclass(frozen=True)
class GuardDecision:
    mode: DeliveryMode
    allow_pane: bool
    reason: str


def inspect_delivery_guard(
    entry: CatalogEntry | None,
    requested: DeliveryMode,
    *,
    composer_empty: bool | None = None,
    human_draft_present: bool | None = None,
    readiness_subcommand_available: bool = False,
) -> GuardDecision:
    if requested is DeliveryMode.INBOX:
        return GuardDecision(DeliveryMode.INBOX, False, "inbox_default")

    if human_draft_present is True:
        raise GuardRejected("protected_human_draft")

    if entry is None:
        raise GuardRejected("recipient_unresolved")

    if entry.reported_state in BUSY_STATES:
        raise GuardRejected(f"busy_pane:{entry.reported_state}")

    if entry.reported_state in UNKNOWN_STATES:
        raise GuardRejected("unknown_recipient_state")

    if composer_empty is not True:
        raise GuardRejected("composer_not_proven_empty")

    if not readiness_subcommand_available:
        # Native readiness is absent on the installed CLI. An empty-composer
        # capture is still not a substitute for native readiness; pane remains
        # refused so we never overwrite a draft on a guessed idle.
        raise GuardRejected("native_readiness_absent")

    return GuardDecision(requested, True, "native_ready_empty_composer")
