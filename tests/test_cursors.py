from pathlib import Path

import pytest

from coordination.cursors import CursorStore, payload_digest
from coordination.errors import IdempotencyConflict


def test_idempotent_retry_returns_same_id(tmp_path: Path):
    store = CursorStore(tmp_path)
    digest = payload_digest("hello", {"t": "1"})
    first = store.remember_send("k1", sender="a", recipient="b", digest=digest, message_id="m1")
    assert first is None
    assert store.lookup_send("k1", sender="a", recipient="b", digest=digest) == "m1"
    again = store.remember_send("k1", sender="a", recipient="b", digest=digest, message_id="m-other")
    assert again == "m1"


def test_payload_conflict_is_rejected(tmp_path: Path):
    store = CursorStore(tmp_path)
    store.remember_send("k1", sender="a", recipient="b", digest="d1", message_id="m1")
    with pytest.raises(IdempotencyConflict):
        store.remember_send("k1", sender="a", recipient="b", digest="d2", message_id="m2")


def test_offline_outbox_and_cursor(tmp_path: Path):
    store = CursorStore(tmp_path)
    store.queue_offline({"idempotency_key": "k1", "body": "x"})
    assert len(store.pending_outbox()) == 1
    store.mark_sent("k1", "m1")
    assert store.pending_outbox() == []
    store.advance("mailbox-a", "m1")
    assert store.cursor("mailbox-a") == "m1"
