import shutil
"""
Tests for Agent Hub Outbound Host Adapter & Proposed C888 Wire Contract
Bidirectional Spool, Aplexer Bridge, and Reconnect/Restart Pipeline
"""

import unittest
import tempfile
import sqlite3
import os
import sys
import time
import json
import hashlib
import threading
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from unittest.mock import patch, MagicMock
from typing import Union, List, Optional, Tuple, Dict, Any

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from adapters.hub_outbound import (
    SQLiteSpool,
    AplexerBridge,
    HubOutboundIntegration,
    C888BusClient,
    get_hub_host_config,
    parse_envelope,
    receive_message,
    dispatch_inbound,
    handle_reply,
    track_ack,
    reconcile_receipt,
    advance_cursor,
    reconcile_log,
    validate_native_args,
    resolve_state_root,
    canonical_workspace,
    workspace_key,
    validate_consumer_uuid,
    read_bounded_regular_file,
    verify_workspace_metadata,
    MAX_MAILBOX_STATE_BYTES,
    RESERVED_PROVENANCE_KEYS,
    UNAGREED_WIRE_PROTOCOL_VERSION,
    C888_PROPOSED_WIRE_CONTRACT_PIN,
    ACCEPTED_HUB_MAIN_PIN,
    CANDIDATE_CONTRACT_ONLY,
    MAX_BUS_BODY_BYTES,
    InsecureTransportError,
    WireContractError,
    SpoolStorageLimitReached,
    MIN_PHYSICAL_SCHEMA_BYTES,
    IdempotencyConflictError,
    make_versioned_key,
    parse_versioned_key_issuance,
    validate_metadata_str,
    MAX_METADATA_STRING_BYTES,
    MAX_WORKSPACE_PATH_BYTES,
    MAX_PAYLOAD_TEXT_BYTES,
    DEFAULT_MAX_PHYSICAL_BYTES,
    DEFAULT_MAX_PAGES,
    DEFAULT_MAX_TOTAL_RECORDS,
    _read_bounded_response,
    validate_bus_message_schema,
    DenyRedirectHandler,
    is_versioned_key,
    MAX_SINGLE_MESSAGE_RESPONSE_BYTES,
    MAX_HTTP_ERROR_RESPONSE_BYTES,
)


def make_producer_fixture(
    base_dir: Path,
    workspace: Union[str, Path],
    consumer_uuid: str,
    exceptions: Optional[List[str]] = None,
    acked_through: Optional[str] = None,
    custom_reverse_map: Optional[Union[str, Path]] = None,
    corrupt_reverse_map: bool = False,
    corrupt_cursor_json: bool = False,
    cursor_symlink: bool = False,
    cursor_oversize: bool = False,
) -> Tuple[Path, Path, str]:
    """Creates a producer-faithful native state layout:
      state_root/messages/<hash>/workspace.json
      state_root/messages/<hash>/cursors/<consumer_uuid>.json
    Returns: (state_root, workspace_path, ws_hash)"""
    workspace_path = Path(workspace)
    canon_ws = canonical_workspace(workspace_path)
    ws_hash = workspace_key(canon_ws)

    state_root = base_dir / "state"
    msg_dir = state_root / "messages" / ws_hash
    msg_dir.mkdir(parents=True, exist_ok=True)

    # Write reverse map
    if corrupt_reverse_map:
        with open(msg_dir / "workspace.json", "wb") as f:
            f.write(b"NOT_JSON_DATA")
    elif custom_reverse_map is not None:
        with open(msg_dir / "workspace.json", "w", encoding="utf-8") as f:
            json.dump({"workspace": str(custom_reverse_map)}, f)
    else:
        with open(msg_dir / "workspace.json", "w", encoding="utf-8") as f:
            json.dump({"workspace": str(canon_ws)}, f)

    cursors_dir = msg_dir / "cursors"
    cursors_dir.mkdir(parents=True, exist_ok=True)

    cursor_file = cursors_dir / f"{consumer_uuid}.json"
    if cursor_oversize:
        with open(cursor_file, "wb") as f:
            f.write(b"X" * (MAX_MAILBOX_STATE_BYTES + 1024))
    elif corrupt_cursor_json:
        with open(cursor_file, "wb") as f:
            f.write(b"INVALID_JSON_CONTENT")
    elif cursor_symlink:
        target = msg_dir / "target.json"
        with open(target, "w", encoding="utf-8") as f:
            json.dump({"exceptions": exceptions or []}, f)
        if cursor_file.exists() or cursor_file.is_symlink():
            cursor_file.unlink()
        cursor_file.symlink_to(target)
    else:
        cursor_data = {
            "exceptions": exceptions or [],
            "acked_through": acked_through,
        }
        with open(cursor_file, "w", encoding="utf-8") as f:
            json.dump(cursor_data, f)

    return state_root, canon_ws, ws_hash



class MockLoopbackHubServer(BaseHTTPRequestHandler):
    """Loopback mock HTTP server implementing proposed C888 wire endpoints."""

    received_requests = []
    auth_header = None
    force_401_once = False

    def do_POST(self):
        content_len = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_len) if content_len > 0 else b""
        MockLoopbackHubServer.received_requests.append((self.command, self.path, body))
        MockLoopbackHubServer.auth_header = self.headers.get("Authorization")

        if MockLoopbackHubServer.force_401_once:
            MockLoopbackHubServer.force_401_once = False
            self.send_response(401)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "unauthorized"}).encode("utf-8"))
            return

        if self.path == "/api/bus/send":
            req_data = json.loads(body.decode("utf-8"))
            if req_data.get("idempotency_key") == "conflict-key":
                self.send_response(409)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "idempotency collision"}).encode("utf-8"))
                return

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            res = {
                "id": "msg-ulid-001",
                "thread_id": req_data.get("thread_id", "th-001"),
                "threadId": req_data.get("thread_id", "th-001"),
            }
            self.wfile.write(json.dumps(res).encode("utf-8"))

        elif self.path == "/api/bus/reply":
            req_data = json.loads(body.decode("utf-8"))
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            res = {
                "id": "reply-ulid-002",
                "thread_id": req_data.get("thread_id", "th-001"),
                "threadId": req_data.get("thread_id", "th-001"),
                "reply_to": req_data.get("reply_to"),
            }
            self.wfile.write(json.dumps(res).encode("utf-8"))

        elif self.path.endswith("/ack"):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "acked"}).encode("utf-8"))

        elif self.path.endswith("/accept"):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "accepted"}).encode("utf-8"))

        elif self.path.endswith("/complete"):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "completed"}).encode("utf-8"))

        elif self.path == "/api/bus/claims":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"id": "claim-001"}).encode("utf-8"))

        elif "/claims/" in self.path and self.path.endswith("/release"):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "released"}).encode("utf-8"))

        else:
            self.send_response(404)
            self.end_headers()

    def do_GET(self):
        MockLoopbackHubServer.received_requests.append((self.command, self.path, b""))
        MockLoopbackHubServer.auth_header = self.headers.get("Authorization")

        if self.path.startswith("/api/bus/inbox"):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            messages = [
                {
                    "id": "inbox-msg-1",
                    "from_actor": "remote-peer",
                    "to_actor": "host-agent",
                    "kind": "note",
                    "body": "ping from remote",
                    "created_at": 1728700000000,
                    "expires_at": 1728700000000,
                }
            ]
            self.wfile.write(json.dumps(messages).encode("utf-8"))

        elif self.path.startswith("/api/bus/messages/"):
            msg_id = self.path.split("/")[-1]
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            res = {
                "id": msg_id,
                "from_actor": "remote-peer",
                "to_actor": "host-agent",
                "kind": "note",
                "body": "message body content",
                "created_at": 1728700000000,
                "expires_at": 1728700000000,
            }
            self.wfile.write(json.dumps(res).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        # Suppress standard logging during tests
        return


class TestSQLiteSpoolStorageAndIdempotency(unittest.TestCase):
    """Tests for SQLiteSpool storage limits, commit-before-rollback prune, and collision detection."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "test_spool.db"
        self.spool = SQLiteSpool(
            self.db_path,
            max_payload_bytes=1000,
            max_storage_bytes=2000,
            retention_sec=86400.0,
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_payload_exceeding_max_bytes_rejected(self):
        with self.assertRaises(ValueError):
            self.spool.enqueue("key-large", "route/a", b"x" * 1001)

    def test_freelist_reuse_admitted_under_max_pages(self):
        db_path = Path(self.tmp.name) / "test_freelist.db"
        spool = SQLiteSpoolStorage(db_path, max_pages=64) if "SQLiteSpoolStorage" in globals() else SQLiteSpool(db_path, max_pages=64)
        
        payload = b"A" * 4000
        for i in range(30):
            spool.enqueue(f"key-{i}", "route/a", payload)
            
        with spool._get_connection() as conn:
            conn.execute("DELETE FROM outbound_spool")
            conn.commit()
            
        with spool._get_connection() as conn:
            freelist_count = int(conn.execute("PRAGMA freelist_count").fetchone()[0])
            
        self.assertGreater(freelist_count, 0)
        
        try:
            spool.enqueue("key-new", "route/a", payload)
        except SpoolStorageLimitReached:
            self.fail("Should have been admitted due to freelist reuse")

    def test_operational_error_re_raise_on_locked_or_io_error(self):
        db_path = Path(self.tmp.name) / "test_err.db"
        spool = SQLiteSpoolStorage(db_path) if "SQLiteSpoolStorage" in globals() else SQLiteSpool(db_path)
        
        real_get_connection = spool._get_connection
        class MockConn:
            def __init__(self, real_conn):
                self.real_conn = real_conn
            def execute(self, *args, **kwargs):
                if "INSERT" in args[0] and "enrolled_routes" in args[0]:
                    raise sqlite3.OperationalError("database is locked")
                return self.real_conn.execute(*args, **kwargs)
            def commit(self): self.real_conn.commit()
            def rollback(self): self.real_conn.rollback()

        import contextlib
        @contextlib.contextmanager
        def mock_get_conn():
            with real_get_connection() as c:
                yield MockConn(c)
                
        spool._get_connection = mock_get_conn
        
        with self.assertRaises(sqlite3.OperationalError) as ctx:
            spool.register_route("route/1", "ws", "tag")
        self.assertIn("database is locked", str(ctx.exception))

    def test_idempotent_replay_vs_route_collision(self):
        # Initial enqueue
        ok1 = self.spool.enqueue("key-idem", "route/original", b"payload-1")
        self.assertTrue(ok1)

        # Exact idempotent replay (same key, same route, same payload) -> True
        ok2 = self.spool.enqueue("key-idem", "route/original", b"payload-1")
        self.assertTrue(ok2)

        # Collision: same key + same payload, but DIFFERENT route -> False
        ok_diff_route = self.spool.enqueue("key-idem", "route/spoofed", b"payload-1")
        self.assertFalse(ok_diff_route)

        # Collision: same key + same route, but DIFFERENT payload -> False
        ok_diff_payload = self.spool.enqueue("key-idem", "route/original", b"payload-2")
        self.assertFalse(ok_diff_payload)

    def test_storage_bound_and_committed_prune_on_limit_reached(self):
        # Spool with max 1000 bytes
        spool = SQLiteSpool(
            Path(self.tmp.name) / "small_spool.db",
            max_payload_bytes=1000,
            max_storage_bytes=1000,
            retention_sec=86400.0,
        )

        # Enqueue 600 bytes and mark delivered with timestamp older than retention window (2 days ago)
        spool.enqueue("k1", "route/main", b"a" * 600)
        with spool._get_conn() as conn:
            conn.execute(
                "UPDATE outbound_spool SET status='delivered', last_attempt=? WHERE idempotency_key='k1'",
                (time.time() - 100000.0,),
            )
            conn.commit()

        # Enqueue 700 bytes pending
        spool.enqueue("k2", "route/main", b"b" * 700)

        # Now enqueue 400 bytes: total would be 700 + 400 = 1100 > 1000.
        # Prune runs and commits deletion of k1 (converting to tombstone).
        # Even though 700 + 400 > 1000 still raises RuntimeError, k1 deletion is COMMITTED!
        with self.assertRaises(RuntimeError) as ctx:
            spool.enqueue("k3", "route/main", b"c" * 400)
        self.assertIn("Spool storage limit reached", str(ctx.exception))

        # Verify that delivered message k1 was PRUNED and converted to tombstone, not rolled back!
        with spool._get_conn() as conn:
            row = conn.execute("SELECT * FROM outbound_spool WHERE idempotency_key='k1'").fetchone()
            self.assertIsNone(row, "Delivered message k1 should be pruned from outbound_spool")
            tomb = conn.execute("SELECT * FROM spool_tombstones WHERE idempotency_key='k1'").fetchone()
            self.assertIsNotNone(tomb, "k1 tombstone should be preserved for idempotency protection")
            self.assertEqual(tomb["route"], "route/main")

        # Tombstone idempotency replay test:
        # Replaying k1 with same payload and route returns True
        self.assertTrue(spool.enqueue("k1", "route/main", b"a" * 600))
        # Replaying k1 with differing route returns False
        self.assertFalse(spool.enqueue("k1", "route/other", b"a" * 600))

    def test_reconnect_retry_and_clock_injection(self):
        t0 = 1000000.0
        self.spool.enqueue("msg-retry", "route/a", b"test-data", now=t0)

        # Mark failed at t0
        self.spool.mark_failed(1, "connection timeout", now=t0)

        # Immediate check at t0 + 5s with default 30s backoff -> 0 eligible
        pending_immediate = self.spool.get_pending(retry_backoff_sec=30, now=t0 + 5.0)
        self.assertEqual(len(pending_immediate), 0)

        # Check after backoff cutoff (t0 + 35s) -> 1 eligible
        pending_after_backoff = self.spool.get_pending(retry_backoff_sec=30, now=t0 + 35.0)
        self.assertEqual(len(pending_after_backoff), 1)

        # Immediate reconnect trigger resets backoff
        self.spool.reset_retry_backoffs()
        pending_reset = self.spool.get_pending(retry_backoff_sec=30, now=t0 + 5.0)
        self.assertEqual(len(pending_reset), 1)
        self.assertEqual(pending_reset[0]["idempotency_key"], "msg-retry")


class TestAplexerBridgeStrictExecution(unittest.TestCase):
    """Tests for AplexerBridge strict argv execution, intent persistence, and log reconciliation."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "intent_spool.db"
        self.spool = SQLiteSpool(self.db_path)
        self.bridge = AplexerBridge("fake_aplexer", spool=self.spool)

    def tearDown(self):
        self.tmp.cleanup()

    def test_bridge_unavailable_when_binary_missing(self):
        with patch("shutil.which", return_value=None):
            self.assertFalse(self.bridge.is_available())
            ok, amb, err = self.bridge.send_message("/tmp/ws", "agent-1", {"text": "hi"})
            self.assertFalse(ok)
            self.assertFalse(amb)
            self.assertEqual(err, "aplexer unavailable")

    def test_strict_argv_construction_without_unsupported_flags(self):
        """Verifies strict argv: positional text at end, data JSON with bridge_id, NO --idempotency-key."""
        with patch.object(self.bridge, "is_available", return_value=True), \
             patch.object(self.bridge, "list_sessions", return_value=[{"workspace": "/tmp/ws", "tag": "agent-1"}]), \
             patch.object(self.bridge, "_run_cmd") as mock_run:

            mock_res = MagicMock(returncode=0, stdout='{"id": "00000000-0000-0000-0000-000000000001"}', stderr="")
            mock_run.return_value = mock_res

            ok, amb, err = self.bridge.send_message("/tmp/ws", "agent-1", {"text": "hello agent", "extra": 42})
            self.assertTrue(ok)
            self.assertFalse(amb)

            args = mock_run.call_args[0][0]
            # args structure: ["message", "send", "--workspace", ..., "--to", ..., "--json", "--data", <JSON>, <TEXT>]
            self.assertEqual(args[0], "message")
            self.assertEqual(args[1], "send")
            self.assertEqual(args[2], "--workspace")
            self.assertEqual(args[3], "/tmp/ws")
            self.assertEqual(args[4], "--to")
            self.assertEqual(args[5], "agent-1")
            self.assertEqual(args[6], "--json")
            self.assertEqual(args[7], "--data")
            # Last arg is positional text
            self.assertEqual(args[-1], "hello agent")
            # Argument immediately preceding positional text must be literal '--'
            self.assertEqual(args[-2], "--")
            # Verify data contains extra fields and stable bridge_id / idempotency_key
            data_dict = json.loads(args[-3])
            self.assertEqual(data_dict["extra"], 42)
            self.assertIn("bridge_id", data_dict)
            self.assertIn("idempotency_key", data_dict)
            # Ensure unsupported --idempotency-key is NOT in args
            self.assertNotIn("--idempotency-key", args)

    def test_deterministic_pre_effect_failure_differentiated(self):
        with patch.object(self.bridge, "is_available", return_value=True), \
             patch.object(self.bridge, "list_sessions", return_value=[{"workspace": "/tmp/ws", "tag": "agent-1"}]), \
             patch.object(self.bridge, "_run_cmd") as mock_run:

            mock_run.return_value = MagicMock(returncode=2, stdout="", stderr="error: invalid option '--unknown'")
            ok, amb, err = self.bridge.send_message("/tmp/ws", "agent-1", {"text": "test"})
            self.assertFalse(ok)
            self.assertFalse(amb)  # Deterministic failure, NOT ambiguous
            self.assertIn("Deterministic delivery failure", err)

    def test_ambiguous_ipc_crash_reconciled_via_native_message_log(self):
        """When IPC drops (exit code 1) but message committed, log inspection confirms delivery."""
        bridge_id = "test-bridge-uuid-1234"
        with patch.object(self.bridge, "is_available", return_value=True), \
             patch.object(self.bridge, "list_sessions", return_value=[{"workspace": "/tmp/ws", "tag": "agent-1"}]), \
             patch.object(self.bridge, "_run_cmd") as mock_run, \
             patch.object(self.bridge, "get_message_log") as mock_log:

            # IPC crash
            mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="IPC connection lost")
            # Message log shows envelope with matching bridge_id
            mock_log.return_value = [
                {
                    "id": "msg-committed-999",
                    "workspace": "/tmp/ws",
                    "to": {"tag": "agent-1"},
                    "body": "hello",
                    "data": {"bridge_id": bridge_id},
                }
            ]

            ok, amb, err = self.bridge.send_message(
                "/tmp/ws", "agent-1", {"text": "hello"}, idempotency_key=bridge_id
            )
            self.assertTrue(ok, "Message should be reconciled as delivered via message log")
            self.assertFalse(amb)

    def test_ambiguous_ipc_crash_not_in_log_stays_durably_ambiguous(self):
        bridge_id = "test-bridge-uuid-5678"
        with patch.object(self.bridge, "is_available", return_value=True), \
             patch.object(self.bridge, "list_sessions", return_value=[{"workspace": "/tmp/ws", "tag": "agent-1"}]), \
             patch.object(self.bridge, "_run_cmd") as mock_run, \
             patch.object(self.bridge, "get_message_log", return_value=[]):

            mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="IPC timeout")
            ok, amb, err = self.bridge.send_message(
                "/tmp/ws", "agent-1", {"text": "hello"}, idempotency_key=bridge_id
            )
            self.assertFalse(ok)
            self.assertTrue(amb, "Unconfirmed failure must stay durably ambiguous (no blind resend)")
            self.assertIn("Ambiguous delivery failure", err)

    def test_check_idle_empty_prompt_and_sync_wake(self):
        with patch.object(self.bridge, "list_sessions") as mock_sessions:
            mock_sessions.return_value = [
                {"workspace": "/tmp/ws", "tag": "busy-agent", "reported_state": "working"},
                {"workspace": "/tmp/ws", "tag": "idle-agent", "reported_state": "idle"},
            ]
            self.assertFalse(self.bridge.check_idle_empty_prompt("/tmp/ws", "busy-agent"))
            self.assertTrue(self.bridge.check_idle_empty_prompt("/tmp/ws", "idle-agent"))

        with patch.object(self.bridge, "is_available", return_value=True), \
             patch.object(self.bridge, "_run_cmd") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout='{"id":"m1","status":"submitted"}')
            self.assertTrue(self.bridge.attempt_deliver_wake("/tmp/ws", "m1"))


class TestProposedC888WireContractClient(unittest.TestCase):
    """Tests for C888BusClient routes, body bounds, auth header, loopback allowance, and HTTPS fail-closed."""

    @classmethod
    def setUpClass(cls):
        # Start loopback HTTP server
        cls.server = HTTPServer(("127.0.0.1", 0), MockLoopbackHubServer)
        cls.port = cls.server.server_port
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self):
        MockLoopbackHubServer.received_requests.clear()
        MockLoopbackHubServer.auth_header = None
        MockLoopbackHubServer.force_401_once = False
        self.base_url = f"http://127.0.0.1:{self.port}"
        self.token = "test-bearer-token-xyz"
        self.client = C888BusClient(
            self.base_url,
            token_provider=lambda: self.token,
            machine_id="machine-win-01",
            allow_loopback_http=True,
            fixture_opt_in=True,
        )

    def test_insecure_transport_fail_closed_on_non_loopback(self):
        with self.assertRaises(InsecureTransportError):
            C888BusClient("http://remote-hub.example.com/api", allow_loopback_http=True, fixture_opt_in=True)

    def test_send_and_reply_enforces_16kb_utf8_body_cap(self):
        large_body = "x" * (MAX_BUS_BODY_BYTES + 1)
        with self.assertRaises(ValueError) as ctx:
            self.client.send_bus_message("from-a", "to-b", "note", large_body, "k1")
        self.assertIn("16KB", str(ctx.exception))

        with self.assertRaises(ValueError) as ctx2:
            self.client.reply_bus_message("from-a", "to-b", "reply", large_body, "k2", reply_to="msg-0")
        self.assertIn("16KB", str(ctx2.exception))

    def test_send_message_loopback_and_auth_injection(self):
        res = self.client.send_bus_message("agent-local", "agent-remote", "note", "hello bus", "idem-01")
        self.assertEqual(res["id"], "msg-ulid-001")
        self.assertEqual(MockLoopbackHubServer.auth_header, f"Bearer {self.token}")

    def test_reply_message_loopback(self):
        res = self.client.reply_bus_message("agent-local", "agent-remote", "reply", "got it", "idem-02", reply_to="msg-ulid-001")
        self.assertEqual(res["id"], "reply-ulid-002")
        self.assertEqual(res["reply_to"], "msg-ulid-001")

    def test_inbox_and_show_message(self):
        inbox = self.client.get_bus_inbox("agent-local", limit=10)
        self.assertEqual(len(inbox), 1)
        self.assertEqual(inbox[0]["body"], "ping from remote")

        msg = self.client.show_bus_message("inbox-msg-1")
        self.assertEqual(msg["id"], "inbox-msg-1")

    def test_stage_acks_and_claims(self):
        ack_res = self.client.ack_bus_message("msg-ulid-001")
        self.assertEqual(ack_res["status"], "acked")

        claim_res = self.client.create_claim("proj-1", "scope-a", "agent-1", ttl_ms=60000)
        self.assertEqual(claim_res["id"], "claim-001")

        rel_res = self.client.release_claim("claim-001")
        self.assertEqual(rel_res["status"], "released")

    def test_bounded_401_refresh(self):
        refreshed = []
        def refresh():
            refreshed.append(True)
            return "new-token"

        self.client.refresh_token_callback = refresh
        MockLoopbackHubServer.force_401_once = True
        res = self.client.send_bus_message("agent-local", "agent-remote", "note", "retry after 401", "idem-401")
        self.assertEqual(res["id"], "msg-ulid-001")
        self.assertEqual(len(refreshed), 1)


class TestTwoWayIntegrationPipeline(unittest.TestCase):
    """Tests for two-way reply/ACK pipeline, cursor advancement, and network exception resilience."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "integration.db"
        self.spool = SQLiteSpool(self.db_path)
        self.state_root = Path(self.tmp.name) / "state"
        self.consumer_uuid = "00000000-0000-0000-0000-000000000111"
        self.bridge = AplexerBridge("fake", spool=self.spool, state_root=self.state_root)
        self.transport = MagicMock()
        self.integration = HubOutboundIntegration(
            self.spool,
            self.bridge,
            self.transport,
            routes={"route/agent1": {"workspace": "/tmp/ws1", "tag": "agent-1", "consumer_uuid": self.consumer_uuid}},
            state_root=self.state_root,
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_two_way_top_level_contract_functions_exist(self):
        raw_env = {
            "id": "11111111-2222-3333-4444-555555555555",
            "workspace": "/tmp/ws1",
            "from": {"tag": "sender"},
            "to": {"tag": "receiver"},
            "kind": "reply",
            "reply_to": "orig-999",
            "body": "reply text",
        }
        env = parse_envelope(raw_env)
        self.assertEqual(env["id"], "11111111-2222-3333-4444-555555555555")
        self.assertEqual(env["reply_to"], "orig-999")

        # advance_cursor and reconcile_receipt
        advance_cursor("route/agent1", receipt_cursor="rec-1", ack_cursor="ack-1", spool=self.spool)
        r, a = reconcile_receipt("route/agent1", spool=self.spool)
        self.assertEqual(r, "rec-1")
        self.assertEqual(a, "ack-1")

        # Record authenticated inbound mapping for orig-999
        self.spool.record_mapping(
            hub_message_id="orig-999",
            workspace="/tmp/ws1",
            tag="sender",
            native_message_id="orig-native-999",
            from_actor="receiver",
            to_actor="sender",
        )

        # handle_reply enqueues legitimate reply into spool
        reply_key = handle_reply(env, original_hub_id="orig-999", spool=self.spool)
        self.assertIsNotNone(reply_key)
        pending = self.spool.get_pending(route="hub/reply")
        self.assertEqual(len(pending), 1)

        # Forged reply from foreign workspace is cleanly rejected
        forged_env = dict(env)
        forged_env["workspace"] = "/tmp/foreign-ws"
        forged_key = handle_reply(forged_env, original_hub_id="orig-999", spool=self.spool)
        self.assertIsNone(forged_key, "Foreign workspace reply must be rejected")

        # Forged reply with unmapped hub ID is cleanly rejected
        unmapped_key = handle_reply(env, original_hub_id="unmapped-hub-id", spool=self.spool)
        self.assertIsNone(unmapped_key, "Unmapped hub id reply must be rejected")

    def test_process_spool_calls_get_cursor_and_get_message_log(self):
        """Verifies process_spool actively inspects cursors and native message logs."""
        self.spool.enqueue("key-outbound", "route/agent1", b'{"body":"outbound"}')
        self.transport.send_payload.return_value = True

        self.spool.record_mapping(
            hub_message_id="hub-req-123",
            workspace="/tmp/ws1",
            tag="agent-1",
            consumer_uuid=self.consumer_uuid,
            native_message_id="native-orig-001",
            route="route/agent1",
        )

        # Create producer-faithful fixture in injected state root
        make_producer_fixture(
            base_dir=Path(self.tmp.name),
            workspace="/tmp/ws1",
            consumer_uuid=self.consumer_uuid,
            exceptions=["native-orig-001"],
        )

        with patch.object(self.spool, "get_cursor", wraps=self.spool.get_cursor) as mock_get_cursor, \
             patch.object(self.spool, "set_cursor", wraps=self.spool.set_cursor) as mock_set_cursor, \
             patch.object(self.bridge, "get_message_log") as mock_get_log:

            mock_get_log.return_value = [
                {
                    "id": "native-msg-555",
                    "workspace": "/tmp/ws1",
                    "from": {"tag": "agent-1", "session_id": self.consumer_uuid},
                    "kind": "reply",
                    "reply_to": "hub-req-123",
                    "body": "native reply body",
                }
            ]

            self.integration.process_spool()

            # Verify get_cursor called for the route
            self.assertTrue(mock_get_cursor.called)
            # Verify get_message_log called for workspace
            self.assertTrue(mock_get_log.called)
            # Verify cursor was advanced for the new message
            self.assertTrue(mock_set_cursor.called)

    def test_network_exception_caught_per_row_without_crashing_loop(self):
        self.spool.enqueue("msg-crash", "route/agent1", b"data1")
        self.spool.enqueue("msg-ok", "route/agent1", b"data2")

        # Transport raises ConnectionResetError on first message, succeeds on second
        def side_effect(route, payload):
            if payload == b"data1":
                raise ConnectionResetError("network peer reset")
            return True

        self.transport.send_payload.side_effect = side_effect

        # process_spool must NOT raise ConnectionResetError
        self.integration.process_spool()

        with self.spool._get_conn() as conn:
            r1 = conn.execute("SELECT status, error_text FROM outbound_spool WHERE idempotency_key='msg-crash'").fetchone()
            self.assertEqual(r1["status"], "failed")
            self.assertIn("ConnectionResetError", r1["error_text"])

            r2 = conn.execute("SELECT status FROM outbound_spool WHERE idempotency_key='msg-ok'").fetchone()
            self.assertEqual(r2["status"], "delivered")

    def test_safe_config_reader(self):
        fake_cfg = Path(self.tmp.name) / "host.json"
        fake_cfg.write_text(json.dumps({
            "base_url": "https://hub.example.com",
            "access_token": "secret-token-123",
            "host_id": "host-test"
        }), encoding="utf-8")

        cfg = get_hub_host_config(fake_cfg)
        self.assertIsNotNone(cfg)
        self.assertEqual(cfg["base_url"], "https://hub.example.com")
        self.assertEqual(cfg["access_token"], "secret-token-123")



class TestHostileTextAndLiteralArgvSeparator(unittest.TestCase):
    """Check 6 / F2: Strict argv execution with '--' literal separator to prevent flag injection."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "test.db"
        self.spool = SQLiteSpool(self.db_path)
        self.bridge = AplexerBridge(spool=self.spool)

    def tearDown(self):
        self.tmp.cleanup()

    def test_send_message_includes_literal_double_dash_before_hostile_text(self):
        with patch.object(self.bridge, "is_available", return_value=True), \
             patch.object(self.bridge, "list_sessions", return_value=[{"workspace": "/tmp/ws", "tag": "worker-agent"}]), \
             patch.object(self.bridge, "_run_cmd") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout='{"id": "00000000-0000-0000-0000-000000000001"}', stderr="")

            # Hostile text that matches clap flags
            for hostile_text in ["--pane", "--all", "--foo", "--help", "--version", "--to", "--workspace"]:
                success, amb, err = self.bridge.send_message(
                    workspace="/tmp/ws",
                    tag="worker-agent",
                    body={"text": hostile_text},
                )
                self.assertTrue(success, f"Failed for {hostile_text}: {err}")
                self.assertFalse(amb)
                args = mock_run.call_args[0][0]
                # Verify that '--' is present and immediately precedes hostile_text
                self.assertIn("--", args)
                idx = args.index("--")
                self.assertEqual(args[idx + 1], hostile_text)
                self.assertEqual(args[-1], hostile_text)

    def test_send_message_literal_double_dash_itself_as_text(self):
        with patch.object(self.bridge, "is_available", return_value=True), \
             patch.object(self.bridge, "list_sessions", return_value=[{"workspace": "/tmp/ws", "tag": "worker-agent"}]), \
             patch.object(self.bridge, "_run_cmd") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout='{"id": "00000000-0000-0000-0000-000000000001"}', stderr="")
            success, amb, err = self.bridge.send_message(
                workspace="/tmp/ws",
                tag="worker-agent",
                body={"text": "--"},
            )
            self.assertTrue(success)
            self.assertFalse(amb)
            args = mock_run.call_args[0][0]
            # Should have '--' separator followed by '--' positional text
            self.assertEqual(args[-2:], ["--", "--"])


class TestNulByteValidationAndPrelaunchSafety(unittest.TestCase):
    """Check 6 / F2: Deterministic pre-effect validation for NUL bytes, types, and length bounds."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "test.db"
        self.spool = SQLiteSpool(self.db_path)
        self.bridge = AplexerBridge(spool=self.spool)

    def tearDown(self):
        self.tmp.cleanup()

    def test_validate_native_args_rejects_nul_bytes(self):
        # NUL in workspace
        self.assertFalse(validate_native_args("/tmp/ws\x00bad", "agent", "text")[0])
        # NUL in tag
        self.assertFalse(validate_native_args("/tmp/ws", "agent\x00tag", "text")[0])
        # NUL in text
        self.assertFalse(validate_native_args("/tmp/ws", "agent", "hello\x00world")[0])
        # NUL in idempotency key
        self.assertFalse(validate_native_args("/tmp/ws", "agent", "text", idempotency_key="key\x00bad")[0])
        # NUL in data keys
        self.assertFalse(validate_native_args("/tmp/ws", "agent", "text", data={"evil\x00key": "val"})[0])
        # NUL in data values
        self.assertFalse(validate_native_args("/tmp/ws", "agent", "text", data={"key": "evil\x00val"})[0])
        # Valid args pass
        self.assertTrue(validate_native_args("/tmp/ws", "agent", "valid", idempotency_key="key-1")[0])

    def test_send_message_pre_effect_rejection_no_intent_poisoning(self):
        with patch.object(self.bridge, "_run_cmd") as mock_run:
            # Send message with NUL byte in text
            success, amb, err = self.bridge.send_message(
                workspace="/tmp/ws",
                tag="agent-1",
                body={"text": "bad\x00payload"},
                idempotency_key="idem-nul-01",
            )
            self.assertFalse(success)
            self.assertFalse(amb)
            self.assertIn("null byte", err.lower())
            # Ensure _run_cmd was never called (pre-effect rejection)
            self.assertFalse(mock_run.called)

            # Ensure intent table was NOT poisoned (0 records)
            with self.spool._get_conn() as conn:
                count = conn.execute("SELECT count(*) FROM delivery_intents").fetchone()[0]
                self.assertEqual(count, 0)

    def test_run_cmd_catches_valueerror_and_oserror_safely(self):
        # Passing NUL byte directly to _run_cmd catches ValueError from posixsubprocess
        res = self.bridge._run_cmd(["aplexer", "message", "send", "bad\x00text"])
        self.assertEqual(res.returncode, 2)
        self.assertIn("null byte", res.stderr.lower())

    def test_spool_enqueue_rejects_nul_bytes(self):
        with self.assertRaises(ValueError):
            self.spool.enqueue("key\x00bad", "route/1", b"payload")
        with self.assertRaises(ValueError):
            self.spool.enqueue("key-1", "route/\x00bad", b"payload")

    def test_bus_client_rejects_nul_bytes(self):
        client = C888BusClient(base_url="https://hub.local", token_provider=lambda: "token", fixture_opt_in=True)
        with self.assertRaises(ValueError):
            client.send_bus_message(from_actor="a1", to_actor="a2", kind="task", body="hello", idempotency_key="k1", thread_id="th\x001")
        with self.assertRaises(ValueError):
            client.send_bus_message(from_actor="a1", to_actor="a2", kind="task", body="hello\x00world", idempotency_key="k1")
        with self.assertRaises(ValueError):
            client.reply_bus_message(from_actor="a1", to_actor="a2", kind="reply", body="hello", idempotency_key="k1", reply_to="msg\x001")

    def test_spool_processing_safe_on_corrupt_row_without_skipping_others(self):
        transport = MagicMock()
        transport.send_payload.return_value = True
        integration = HubOutboundIntegration(spool=self.spool, transport=transport, bridge=self.bridge)

        # Enqueue valid message
        self.spool.enqueue("valid-1", "route/test", b'{"body": "good"}')
        # Insert a corrupt row directly into the database
        with self.spool._get_conn() as conn:
            conn.execute(
                "INSERT INTO outbound_spool (idempotency_key, route, payload, status, created_at, attempt_count) VALUES (?, ?, ?, ?, ?, ?)",
                ("corrupt-1", "route/test", b"not-a-json-payload", "pending", time.time(), 0),
            )
            conn.commit()
        # Enqueue another valid message
        self.spool.enqueue("valid-2", "route/test", b'{"body": "also good"}')

        # Transport raises for corrupt row when payload is invalid json
        def transport_side_effect(route, payload):
            try:
                json.loads(payload.decode("utf-8"))
            except Exception as e:
                raise ValueError(f"malformed payload: {e}")
            return True

        transport.send_payload.side_effect = transport_side_effect

        # process_spool must NOT crash
        integration.process_spool()

        with self.spool._get_conn() as conn:
            r1 = conn.execute("SELECT status FROM outbound_spool WHERE idempotency_key='valid-1'").fetchone()
            self.assertEqual(r1["status"], "delivered")

            rc = conn.execute("SELECT status, error_text FROM outbound_spool WHERE idempotency_key='corrupt-1'").fetchone()
            self.assertEqual(rc["status"], "failed")
            self.assertIn("malformed payload", rc["error_text"])

            r2 = conn.execute("SELECT status FROM outbound_spool WHERE idempotency_key='valid-2'").fetchone()
            self.assertEqual(r2["status"], "delivered")


class TestReservedProvenanceKeysCollision(unittest.TestCase):
    """Check 6 / F2: Reserved provenance keys protection from user-body data collision."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "test.db"
        self.spool = SQLiteSpool(self.db_path)
        self.bridge = AplexerBridge(spool=self.spool)

    def tearDown(self):
        self.tmp.cleanup()

    def test_user_data_cannot_override_reserved_keys(self):
        with patch.object(self.bridge, "is_available", return_value=True), \
             patch.object(self.bridge, "list_sessions", return_value=[{"workspace": "/legit/workspace", "tag": "legit-agent"}]), \
             patch.object(self.bridge, "_run_cmd") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout='{"id": "00000000-0000-0000-0000-000000000001"}', stderr="")

            hostile_data = {
                "bridge_id": "malicious-bridge",
                "workspace": "/hostile/workspace",
                "tag": "hacked-tag",
                "session_id": "forged-uuid",
                "idempotency_key": "spoofed-key",
                "origin": "fake-origin",
                "user_custom_field": "legitimate_custom_value",
            }

            success, amb, err = self.bridge.send_message(
                workspace="/legit/workspace",
                tag="legit-agent",
                body={"text": "hello agent", "data": hostile_data},
                idempotency_key="real-key-123",
            )
            self.assertTrue(success, f"send_message failed: {err}")
            self.assertFalse(amb)

            # Check the --data JSON string passed to _run_cmd
            args = mock_run.call_args[0][0]
            data_idx = args.index("--data")
            merged_json = json.loads(args[data_idx + 1])

            # Reserved keys must contain trusted bridge values, not attacker overrides
            self.assertIn("bridge_id", merged_json)
            self.assertNotEqual(merged_json["bridge_id"], "malicious-bridge")
            self.assertEqual(merged_json["idempotency_key"], "real-key-123")
            # User non-reserved field is preserved
            self.assertEqual(merged_json["user_custom_field"], "legitimate_custom_value")


class TestStateProvenanceAndSiblingWorkspaceForgery(unittest.TestCase):
    """Check 3 / F1: State provenance, envelope verification, and sibling/foreign forgery rejection."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "test.db"
        self.spool = SQLiteSpool(self.db_path)
        self.state_root = Path(self.tmp.name) / "state"
        self.consumer_uuid = "00000000-0000-0000-0000-000000000111"
        self.bridge = AplexerBridge(spool=self.spool, state_root=self.state_root)
        self.transport = MagicMock()
        self.transport.send_payload.return_value = True
        self.integration = HubOutboundIntegration(
            spool=self.spool,
            transport=self.transport,
            bridge=self.bridge,
            state_root=self.state_root,
            routes={"route/agent1": {"workspace": "/tmp/ws_legit", "tag": "agent-1", "consumer_uuid": self.consumer_uuid}},
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_handle_reply_rejects_foreign_workspace(self):
        # Register mapping for /tmp/ws_legit
        self.spool.record_mapping(
            hub_message_id="hub-msg-100",
            workspace="/tmp/ws_legit",
            tag="agent-1",
            consumer_uuid=self.consumer_uuid,
            native_message_id="native-100",
            route="route/agent1",
        )

        # Attacker in /tmp/ws_attacker tries to reply to hub-msg-100
        forged_envelope = {
            "id": "reply-forged-1",
            "workspace": "/tmp/ws_attacker",
            "from": {"tag": "agent-1", "session_id": self.consumer_uuid},
            "reply_to": "hub-msg-100",
            "body": "hostile reply",
        }

        result = handle_reply(forged_envelope, "hub-msg-100", spool=self.spool)
        # Must be rejected (returns None)
        self.assertIsNone(result)

        # Mapping status remains unchanged ('delivered')
        m = self.spool.get_message_mapping("hub-msg-100")
        self.assertEqual(m["status"], "delivered")

    def test_handle_reply_rejects_unmapped_hub_id(self):
        forged_envelope = {
            "id": "reply-forged-2",
            "workspace": "/tmp/ws_legit",
            "from": {"tag": "agent-1", "session_id": self.consumer_uuid},
            "reply_to": "hub-nonexistent-999",
            "body": "reply to nowhere",
        }
        result = handle_reply(forged_envelope, "hub-nonexistent-999", spool=self.spool)
        self.assertIsNone(result)

    def test_handle_reply_rejects_sender_tag_mismatch(self):
        self.spool.record_mapping(
            hub_message_id="hub-msg-101",
            workspace="/tmp/ws_legit",
            tag="agent-1",
            consumer_uuid=self.consumer_uuid,
            native_message_id="native-101",
            route="route/agent1",
        )

        # Forged sender tag 'evil-tag'
        forged_envelope = {
            "id": "reply-forged-3",
            "workspace": "/tmp/ws_legit",
            "from": {"tag": "evil-tag", "session_id": self.consumer_uuid},
            "reply_to": "hub-msg-101",
            "body": "spoofed tag reply",
        }
        result = handle_reply(forged_envelope, "hub-msg-101", spool=self.spool)
        self.assertIsNone(result)

    def test_handle_reply_rejects_session_uuid_mismatch(self):
        self.spool.record_mapping(
            hub_message_id="hub-msg-102",
            workspace="/tmp/ws_legit",
            tag="agent-1",
            consumer_uuid=self.consumer_uuid,
            native_message_id="native-102",
            route="route/agent1",
        )

        # Forged session_id 'uuid-attacker'
        forged_envelope = {
            "id": "reply-forged-4",
            "workspace": "/tmp/ws_legit",
            "from": {"tag": "agent-1", "session_id": "00000000-0000-0000-0000-000000000999"},
            "reply_to": "hub-msg-102",
            "body": "spoofed session reply",
        }
        result = handle_reply(forged_envelope, "hub-msg-102", spool=self.spool)
        self.assertIsNone(result)

    def test_process_spool_ignores_sibling_fake_ack_chat_messages(self):
        # Register mapping for agent-1
        self.spool.record_mapping(
            hub_message_id="hub-msg-200",
            workspace="/tmp/ws_legit",
            tag="agent-1",
            consumer_uuid=self.consumer_uuid,
            native_message_id="native-200",
            route="route/agent1",
        )

        # Create real producer fixture on disk without acknowledging native-200
        make_producer_fixture(
            Path(self.tmp.name),
            "/tmp/ws_legit",
            self.consumer_uuid,
            exceptions=[],
        )

        # Sibling workspace posts a chat message with kind='ack' attempting to forge an ACK
        with patch.object(self.bridge, "get_message_log") as mock_log:
            mock_log.return_value = [
                {
                    "id": "sibling-chat-1",
                    "workspace": "/tmp/ws_legit",
                    "from": {"tag": "agent-1", "session_id": self.consumer_uuid},
                    "kind": "ack",  # Fake kind
                    "message_id": "native-200",
                    "data": {"message_id": "native-200"},
                }
            ]

            self.integration.process_spool()

            # Mapping must remain delivered, NOT acked
            m = self.spool.get_message_mapping("hub-msg-200")
            self.assertEqual(m["status"], "delivered")

    def test_track_ack_cursor_provenance_validation(self):
        self.spool.record_mapping(
            hub_message_id="hub-msg-300",
            workspace="/tmp/ws_legit",
            tag="agent-1",
            consumer_uuid=self.consumer_uuid,
            native_message_id="native-300",
            route="route/agent1",
        )

        # Case 1: Cursor file not found -> track_ack returns False
        acked = track_ack("route/agent1", "hub-msg-300", spool=self.spool, bridge=self.bridge)
        self.assertFalse(acked)

        # Case 2: Cursor file exists but does not include native-300 -> returns False
        make_producer_fixture(
            Path(self.tmp.name),
            "/tmp/ws_legit",
            self.consumer_uuid,
            exceptions=[],
        )
        acked = track_ack("route/agent1", "hub-msg-300", spool=self.spool, bridge=self.bridge)
        self.assertFalse(acked)

        # Case 3: Cursor file includes native-300 in exceptions -> returns True and status updated
        make_producer_fixture(
            Path(self.tmp.name),
            "/tmp/ws_legit",
            self.consumer_uuid,
            exceptions=["native-300"],
        )
        acked = track_ack("route/agent1", "hub-msg-300", spool=self.spool, bridge=self.bridge)
        self.assertTrue(acked)
        m = self.spool.get_message_mapping("hub-msg-300")
        self.assertEqual(m["status"], "acked")

    def test_track_ack_rejects_unmapped_route_or_wrong_workspace(self):
        # Route not enrolled in spool
        acked = track_ack("route/unknown", "hub-msg-400", spool=self.spool, bridge=self.bridge)
        self.assertFalse(acked)

    def test_legitimate_exact_positive_e2e_flow(self):
        # 1. Inbound dispatch records mapping
        inbound_envelope = {
            "id": "hub-e2e-001",
            "to": "agent-1",
            "from": "hub-sender",
            "thread_id": "th-e2e",
            "body": "legitimate task",
        }
        with patch.object(self.bridge, "is_available", return_value=True), \
             patch.object(self.bridge, "list_sessions", return_value=[{"workspace": "/tmp/ws_legit", "tag": "agent-1"}]), \
             patch.object(self.bridge, "_run_cmd", return_value=MagicMock(returncode=0, stdout='{"id": "00000000-0000-0000-0000-e2e000000001"}', stderr="")):
            ok, err = dispatch_inbound(
                inbound_msg=inbound_envelope,
                workspace="/tmp/ws_legit",
                tag="agent-1",
                route="route/agent1",
                consumer_uuid=self.consumer_uuid,
                spool=self.spool,
                bridge=self.bridge,
            )
            self.assertTrue(ok, f"dispatch_inbound failed: {err}")

        m = self.spool.get_message_mapping("hub-e2e-001")
        self.assertIsNotNone(m)
        self.assertEqual(m["status"], "delivered")

        # 2. Native agent produces legitimate reply
        valid_reply = {
            "id": "native-reply-001",
            "workspace": "/tmp/ws_legit",
            "from": {"tag": "agent-1", "session_id": self.consumer_uuid},
            "reply_to": "hub-e2e-001",
            "body": "legitimate response",
        }
        reply_key = handle_reply(valid_reply, "hub-e2e-001", spool=self.spool)
        self.assertIsNotNone(reply_key)

        # Verify staged reply payload in spool
        with self.spool._get_conn() as conn:
            spool_row = conn.execute("SELECT * FROM outbound_spool WHERE idempotency_key = ?", (reply_key,)).fetchone()
            self.assertIsNotNone(spool_row)
            payload = json.loads(spool_row["payload"].decode("utf-8"))
            self.assertEqual(payload["reply_to"], "hub-e2e-001")
            self.assertEqual(payload["thread_id"], "th-e2e")

        # 3. Create real producer cursor file on disk confirming consumption
        make_producer_fixture(
            Path(self.tmp.name),
            "/tmp/ws_legit",
            self.consumer_uuid,
            exceptions=["00000000-0000-0000-0000-e2e000000001"],
        )

        acked = track_ack("route/agent1", "hub-e2e-001", spool=self.spool, bridge=self.bridge)
        self.assertTrue(acked)

        # 4. Verify mapping status is 'acked'
        final_m = self.spool.get_message_mapping("hub-e2e-001")
        self.assertEqual(final_m["status"], "acked")


class TestNativeProducerContract(unittest.TestCase):
    """Producer compatibility contract tests matching cloudflare-aplexer-protocol paths & layout."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base_dir = Path(self.tmp.name)
        self.ws = self.base_dir / "test_workspace"
        self.ws.mkdir(parents=True, exist_ok=True)
        self.consumer_uuid = "00000000-0000-0000-0000-000000000001"

    def tearDown(self):
        self.tmp.cleanup()

    def test_resolve_state_root_precedence_and_overrides(self):
        # 1. Configured state_root takes precedence (both absolute and relative resolved against cwd)
        custom_abs = Path("/opt/custom/state")
        self.assertEqual(resolve_state_root(custom_abs), custom_abs)
        self.assertEqual(resolve_state_root("rel/custom/state"), (Path.cwd() / "rel/custom/state").resolve())

        # 2. APLEXER_STATE_DIR env variable
        with patch.dict(os.environ, {"APLEXER_STATE_DIR": "/env/aplexer/state"}):
            self.assertEqual(resolve_state_root(), Path("/env/aplexer/state"))
        with patch.dict(os.environ, {"APLEXER_STATE_DIR": "rel/aplexer/state"}):
            self.assertEqual(resolve_state_root(), (Path.cwd() / "rel/aplexer/state").resolve())

        # 3. XDG_STATE_HOME env variable
        with patch.dict(os.environ, {"XDG_STATE_HOME": "/env/xdg", "APLEXER_STATE_DIR": ""}):
            self.assertEqual(resolve_state_root(), Path("/env/xdg/aplexer"))

        # 4. Fallback when unset
        with patch.dict(os.environ, {"APLEXER_STATE_DIR": "", "XDG_STATE_HOME": ""}):
            expected_fallback = (Path(os.environ.get("HOME", Path.home())) / ".local" / "state" / "aplexer").resolve()
            self.assertEqual(resolve_state_root(), expected_fallback)

    def test_resolve_state_root_xdg_relative_invalid(self):
        with patch.dict(os.environ, {"XDG_STATE_HOME": "relative/path/xdg", "APLEXER_STATE_DIR": ""}):
            with self.assertRaises(ValueError) as ctx:
                resolve_state_root()
            self.assertIn("must be an absolute path", str(ctx.exception))

    def test_canonical_workspace_and_path_aliases(self):
        # Create a directory and a symlink alias
        real_ws = self.base_dir / "canonical_real"
        real_ws.mkdir(parents=True, exist_ok=True)
        symlink_ws = self.base_dir / "symlink_alias"
        symlink_ws.symlink_to(real_ws)

        canon_real = canonical_workspace(real_ws)
        canon_sym = canonical_workspace(symlink_ws)
        self.assertEqual(canon_real, canon_sym)
        self.assertEqual(workspace_key(canon_real), workspace_key(canon_sym))
        # Hash is exactly 32 hex chars (128 bits)
        self.assertEqual(len(workspace_key(canon_real)), 32)

    def test_reverse_map_verification_and_mismatch(self):
        state_root, canon_ws, ws_hash = make_producer_fixture(
            self.base_dir,
            self.ws,
            self.consumer_uuid,
            exceptions=["msg-test-1"],
        )
        bridge = AplexerBridge(state_root=state_root)

        # 1. Matching reverse map succeeds
        cursor = bridge.get_native_cursor(str(self.ws), self.consumer_uuid)
        self.assertIsNotNone(cursor)
        self.assertTrue(bridge.is_native_cursor_acked(cursor, "msg-test-1"))

        # 2. Mismatched reverse map rejected (returns None)
        make_producer_fixture(
            self.base_dir,
            self.ws,
            self.consumer_uuid,
            exceptions=["msg-test-1"],
            custom_reverse_map="/different/workspace/path",
        )
        self.assertIsNone(bridge.get_native_cursor(str(self.ws), self.consumer_uuid))

        # 3. Corrupt reverse map rejected
        make_producer_fixture(
            self.base_dir,
            self.ws,
            self.consumer_uuid,
            exceptions=["msg-test-1"],
            corrupt_reverse_map=True,
        )
        self.assertIsNone(bridge.get_native_cursor(str(self.ws), self.consumer_uuid))

        # 4. Missing workspace.json rejected
        ws_file = state_root / "messages" / ws_hash / "workspace.json"
        if ws_file.exists():
            ws_file.unlink()
        self.assertIsNone(bridge.get_native_cursor(str(self.ws), self.consumer_uuid))

    def test_consumer_uuid_validation_and_path_traversal(self):
        state_root, _, _ = make_producer_fixture(
            self.base_dir,
            self.ws,
            self.consumer_uuid,
            exceptions=["msg-1"],
        )
        bridge = AplexerBridge(state_root=state_root)

        # Traversal attempts rejected
        self.assertIsNone(bridge.get_native_cursor(str(self.ws), "../../../etc/passwd"))
        self.assertIsNone(bridge.get_native_cursor(str(self.ws), "subdir/00000000-0000-0000-0000-000000000001"))
        self.assertIsNone(bridge.get_native_cursor(str(self.ws), "invalid-uuid-string"))
        # Non-canonical uppercase or hyphen-less rejected by validator
        self.assertIsNone(validate_consumer_uuid("00000000000000000000000000000001"))
        self.assertEqual(validate_consumer_uuid(self.consumer_uuid), self.consumer_uuid)

    def test_bounded_regular_cursor_file_safety(self):
        state_root = self.base_dir / "state"
        bridge = AplexerBridge(state_root=state_root)

        # 1. Missing cursor file returns None
        make_producer_fixture(self.base_dir, self.ws, self.consumer_uuid, exceptions=["msg-1"])
        cursor_file = state_root / "messages" / workspace_key(canonical_workspace(self.ws)) / "cursors" / f"{self.consumer_uuid}.json"
        cursor_file.unlink()
        self.assertIsNone(bridge.get_native_cursor(str(self.ws), self.consumer_uuid))

        # 2. Oversize cursor (>64 KiB) returns None
        make_producer_fixture(self.base_dir, self.ws, self.consumer_uuid, cursor_oversize=True)
        self.assertIsNone(bridge.get_native_cursor(str(self.ws), self.consumer_uuid))

        # 3. Symlink cursor file returns None (O_NOFOLLOW check)
        make_producer_fixture(self.base_dir, self.ws, self.consumer_uuid, exceptions=["msg-1"], cursor_symlink=True)
        self.assertIsNone(bridge.get_native_cursor(str(self.ws), self.consumer_uuid))

        # 4. Invalid JSON cursor returns None
        make_producer_fixture(self.base_dir, self.ws, self.consumer_uuid, corrupt_cursor_json=True)
        self.assertIsNone(bridge.get_native_cursor(str(self.ws), self.consumer_uuid))

    def test_sparse_exceptions_and_legacy_acked_through_semantics(self):
        cursor_data = {
            "exceptions": ["msg-sparse-1", "msg-sparse-2"],
            "acked_through": "msg-050",
        }
        bridge = AplexerBridge()
        # Sparse exceptions match exact IDs
        self.assertTrue(bridge.is_native_cursor_acked(cursor_data, "msg-sparse-1"))
        self.assertTrue(bridge.is_native_cursor_acked(cursor_data, "msg-sparse-2"))
        self.assertFalse(bridge.is_native_cursor_acked(cursor_data, "msg-sparse-99"))

        # Legacy acked_through matches id <= mark
        self.assertTrue(bridge.is_native_cursor_acked(cursor_data, "msg-020"))
        self.assertTrue(bridge.is_native_cursor_acked(cursor_data, "msg-050"))
        self.assertFalse(bridge.is_native_cursor_acked(cursor_data, "msg-060"))

    def test_producer_faithful_e2e_pipeline(self):
        db_path = self.base_dir / "e2e_spool.db"
        spool = SQLiteSpool(db_path)
        state_root, canon_ws, _ = make_producer_fixture(
            self.base_dir,
            self.ws,
            self.consumer_uuid,
            exceptions=["native-e2e-100"],
        )
        transport = MagicMock()
        bridge = AplexerBridge(spool=spool, state_root=state_root)
        integration = HubOutboundIntegration(
            spool=spool,
            bridge=bridge,
            transport=transport,
            routes={"route/agent1": {"workspace": str(canon_ws), "tag": "agent-1", "consumer_uuid": self.consumer_uuid}},
            state_root=state_root,
        )

        spool.record_mapping(
            hub_message_id="hub-e2e-100",
            workspace=str(canon_ws),
            tag="agent-1",
            consumer_uuid=self.consumer_uuid,
            native_message_id="native-e2e-100",
            route="route/agent1",
        )

        integration.process_spool()

        m = spool.get_message_mapping("hub-e2e-100")
        self.assertEqual(m["status"], "acked")
        _, ack_cur = spool.get_cursor("route/agent1")
        self.assertEqual(ack_cur, "hub-e2e-100")

    def test_historical_genuine_own_head_cursor_probe_fact(self):
        """Historical observation of genuine head cursor schema (retained separately).
        Marked as: one-host existing state — not physical Win/actor impersonation.
        Read-only inspection of genuine state root without altering or creating state."""
        head_ws = "/home/alexey/git/agent-coordination"
        head_uuid = "ddbeede6-87c9-465d-a393-cf0a3f0aef47"
        genuine_cursor_path = Path("/home/alexey/.local/state/aplexer/messages/25fc70b992d53f0e472ee7b4154233e2/cursors") / f"{head_uuid}.json"

        if not genuine_cursor_path.exists():
            self.skipTest("Genuine head cursor not present on this host environment")

        bridge = AplexerBridge()  # Default state root resolves to ~/.local/state/aplexer
        cursor = bridge.get_native_cursor(head_ws, head_uuid)
        self.assertIsNotNone(cursor, "Genuine own head cursor must be discovered and parsed")
        self.assertIn("exceptions", cursor)
        self.assertIsInstance(cursor["exceptions"], list)

    def test_synthetic_native_cursor_contract_probe(self):
        """Positive hermetic contract probe of a synthetic head cursor using make_producer_fixture.
        Replaces historical genuine observation with independent synthetic fixture authority."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmp_dir:
            head_ws = "/synthetic/agent-coordination"
            head_uuid = "11111111-2222-3333-4444-555555555555"
            
            state_root, canon_ws, ws_hash = make_producer_fixture(
                base_dir=Path(tmp_dir),
                workspace=head_ws,
                consumer_uuid=head_uuid,
                exceptions=[f"msg-{i}" for i in range(50)]
            )
            
            bridge = AplexerBridge(state_root=state_root)
            cursor = bridge.get_native_cursor(head_ws, head_uuid)
            self.assertIsNotNone(cursor, "Synthetic head cursor must be discovered and parsed")
            self.assertIn("exceptions", cursor)
            self.assertIsInstance(cursor["exceptions"], list)
            self.assertGreaterEqual(len(cursor["exceptions"]), 50, "Synthetic head cursor contains >=50 exact exceptions")

            sample_ack_id = cursor["exceptions"][0]
            self.assertTrue(
                bridge.is_native_cursor_acked(cursor, sample_ack_id),
                "Acknowledged message ID must evaluate to acked=True"
            )
            self.assertFalse(
                bridge.is_native_cursor_acked(cursor, "00000000-unacked-probe-id"),
                "Unacknowledged ID must evaluate to acked=False"
            )



class TestStorageContractBounds(unittest.TestCase):
    """Rigorous tests for storage contract criteria:
    - Impossible budget configuration upfront rejection
    - Repeated delivery/retention cycles and bounded tombstones + all metadata
    - Queued ambiguous and unacked work never pruned
    - Same key replays across restart and prune
    - Expired key scenario duplicate effects zero
    - Two concurrent writers atomic insertion and capacity-failure preservation
    - Physical budget and page count enforcement
    - Reconnect and lost HTTP receipt stability
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "contract_spool.db"

    def tearDown(self):
        self.tmp.cleanup()

    def test_impossible_budget_configuration_rejected(self):
        """Rejects impossible physical, page, and storage budgets upfront."""
        # 1. Impossible physical bytes: less than minimum SQLite schema reserve (114688 bytes)
        with self.assertRaises(ValueError) as ctx:
            SQLiteSpool(self.db_path, max_physical_bytes=1000)
        self.assertIn("Impossible physical budget", str(ctx.exception))
        self.assertIn("minimum SQLite schema overhead", str(ctx.exception))

        # 2. Impossible page count: less than minimum SQLite schema pages (28)
        with self.assertRaises(ValueError) as ctx:
            SQLiteSpool(self.db_path, max_pages=10)
        self.assertIn("Impossible page budget", str(ctx.exception))
        self.assertIn("minimum SQLite schema pages", str(ctx.exception))

        # 3. Impossible negative or zero storage
        with self.assertRaises(ValueError):
            SQLiteSpool(self.db_path, max_storage_bytes=-1)
        with self.assertRaises(ValueError):
            SQLiteSpool(self.db_path, max_payload_bytes=0)

        # 4. max_payload_bytes exceeding max_storage_bytes
        with self.assertRaises(ValueError) as ctx:
            SQLiteSpool(self.db_path, max_payload_bytes=5000, max_storage_bytes=2000)
        self.assertIn("cannot exceed", str(ctx.exception))

    def test_repeated_delivery_retention_cycles_bounded_tombstones_and_metadata(self):
        """Repeated delivery/prune cycles maintain strictly bounded tombstones and metadata tables.
        Tombstones do NOT grow forever over repeated cycles."""
        spool = SQLiteSpool(
            self.db_path,
            max_payload_bytes=1000,
            max_storage_bytes=50000,
            retention_sec=0.0,
            tombstone_retention_sec=0.0,
            max_tombstones=10,
            max_mappings=10,
        )

        now = 100000.0
        # Run 25 repeated cycles of enqueue -> deliver -> prune (more than 2x max_tombstones=10)
        for i in range(25):
            now += 10.0
            key = f"cycle-key-{i}"
            spool.enqueue(key, "route/cycle", b"x" * 10, now=now, message_id=f"hub-msg-{i}")
            spool.mark_delivered(i + 1, now=now)
            spool.prune_delivered(now=now)

        counts = spool.get_table_counts()
        # Tombstones must be strictly capped at max_tombstones (10)
        self.assertLessEqual(counts["spool_tombstones"], 10, "Tombstone count must never exceed max_tombstones")
        # outbound_spool delivered rows must be 0
        self.assertEqual(counts["outbound_spool"], 0, "All delivered rows should be pruned")
        # Physical size remains small and bounded
        phys_size = spool.get_physical_size()
        self.assertLess(phys_size, 500 * 1024, "Physical DB size must remain bounded under 500 KiB")

    def test_queued_ambiguous_and_unacked_work_never_pruned(self):
        """Unacknowledged, pending, and ambiguous work is NEVER pruned simply to satisfy capacity."""
        spool = SQLiteSpool(
            self.db_path,
            max_payload_bytes=2000,
            max_storage_bytes=2500,
            retention_sec=0.0,
        )

        now = 1000.0
        # 1. Enqueue pending message
        spool.enqueue("k-pending", "route/a", b"a" * 500, now=now)

        # 2. Enqueue ambiguous message
        spool.enqueue("k-ambiguous", "route/a", b"b" * 500, now=now)
        spool.mark_ambiguous(2, "Network timeout during delivery", now=now)

        # 3. Enqueue unacked mapped message
        spool.enqueue("k-unacked", "route/a", b"c" * 500, now=now, message_id="hub-unacked-1")

        # 4. Enqueue delivered message
        spool.enqueue("k-delivered", "route/a", b"d" * 500, now=now)
        spool.mark_delivered(4, now=now)

        # Run prune_delivered with retention_sec=0
        pruned = spool.prune_delivered(retention_sec=0.0, now=now + 10.0)
        self.assertEqual(pruned, 1, "Only the delivered message should be pruned")

        # Verify status of all rows
        with spool._get_conn() as conn:
            pending_row = conn.execute("SELECT * FROM outbound_spool WHERE idempotency_key='k-pending'").fetchone()
            self.assertIsNotNone(pending_row)
            self.assertEqual(pending_row["status"], "pending")

            ambiguous_row = conn.execute("SELECT * FROM outbound_spool WHERE idempotency_key='k-ambiguous'").fetchone()
            self.assertIsNotNone(ambiguous_row)
            self.assertEqual(ambiguous_row["status"], "ambiguous")

            unacked_map = conn.execute("SELECT * FROM message_mappings WHERE hub_message_id='hub-unacked-1'").fetchone()
            self.assertIsNotNone(unacked_map)
            self.assertEqual(unacked_map["status"], "pending")

            delivered_row = conn.execute("SELECT * FROM outbound_spool WHERE idempotency_key='k-delivered'").fetchone()
            self.assertIsNone(delivered_row, "Delivered row must be pruned")

        # Total unprunable payload is 1500 bytes. Adding 1500 more would reach 3000 > 2500.
        # Spool must fail closed rather than pruning unacked/ambiguous work!
        with self.assertRaises(SpoolStorageLimitReached):
            spool.enqueue("k-overflow", "route/a", b"e" * 1500, now=now + 20.0)

        # Verify ambiguous and unacked work is STILL intact after capacity failure
        with spool._get_conn() as conn:
            ambiguous_row = conn.execute("SELECT * FROM outbound_spool WHERE idempotency_key='k-ambiguous'").fetchone()
            self.assertIsNotNone(ambiguous_row, "Ambiguous work must survive capacity failure")

    def test_same_key_replays_across_restart_and_prune(self):
        """Same key + same route + same payload replay returns True across process restart and prune.
        Differing route or payload on same key is rejected."""
        spool = SQLiteSpool(self.db_path)
        ok1 = spool.enqueue("stable-key", "route/alpha", b"hello payload")
        self.assertTrue(ok1)
        spool.mark_delivered(1, now=100.0)
        spool.prune_delivered(retention_sec=0.0, now=200.0)

        # Simulate process restart by instantiating new spool on same database
        restarted_spool = SQLiteSpool(self.db_path)

        # Exact replay: same key, same route, same payload -> returns True
        replay_ok = restarted_spool.enqueue("stable-key", "route/alpha", b"hello payload")
        self.assertTrue(replay_ok, "Exact same key+route+payload must return True across restart and prune")

        # Collision with different route -> returns False
        collision_route = restarted_spool.enqueue("stable-key", "route/beta", b"hello payload")
        self.assertFalse(collision_route, "Differing route on same key must return False")

        # Collision with different payload -> returns False
        collision_payload = restarted_spool.enqueue("stable-key", "route/alpha", b"different payload")
        self.assertFalse(collision_payload, "Differing payload on same key must return False")

    def test_expired_key_scenario_duplicate_effects_zero(self):
        """In an expired key scenario after prune and cursor advancement,
        duplicate effects on integration transport and native sessions are ZERO."""
        spool = SQLiteSpool(
            self.db_path,
            retention_sec=10.0,
            tombstone_retention_sec=20.0,
            max_tombstones=5,
        )

        class MockTransport:
            def __init__(self):
                self.sent = []
            def send_payload(self, route: str, payload: bytes) -> bool:
                self.sent.append((route, payload))
                return True

        transport = MockTransport()
        mock_bridge = MagicMock(spec=AplexerBridge)
        mock_bridge.list_sessions.return_value = [{"workspace": "/tmp/test-ws", "tag": "agent-1", "reported_state": "idle"}]

        # Native log contains an original message and its reply
        mock_bridge.get_message_log.return_value = [
            {
                "id": "native-msg-1",
                "workspace": "/tmp/test-ws",
                "from": {"tag": "agent-1"},
                "to": {"tag": "host"},
                "kind": "reply",
                "reply_to": "hub-msg-1",
                "body": "first reply",
            }
        ]
        mock_bridge.parse_envelope.side_effect = lambda m: m

        # Enroll route and map hub-msg-1
        spool.register_route("route/test", "/tmp/test-ws", "agent-1")
        spool.record_mapping(
            hub_message_id="hub-msg-1",
            workspace="/tmp/test-ws",
            tag="agent-1",
            from_actor="remote-peer",
            to_actor="agent-1",
            status="delivered",
            now=100.0,
        )

        integration = HubOutboundIntegration(
            spool=spool,
            bridge=mock_bridge,
            transport=transport,
            routes={"route/test": {"workspace": "/tmp/test-ws", "tag": "agent-1"}},
        )

        # Tick 1: Correlates native reply and enqueues to spool, next tick dispatches to transport
        integration.tick(now=100.0)
        integration.tick(now=100.0)
        self.assertEqual(len(transport.sent), 1, "First reply sent to transport")

        # Mark delivered and advance clock past retention & tombstone expiration
        spool.mark_delivered(1, now=100.0)
        spool.prune_delivered(retention_sec=0.0, now=200.0)
        spool.prune_tombstones(tombstone_retention_sec=0.0, now=200.0)

        # Mapping is marked 'replied' and log_cursor is advanced past 'native-msg-1'
        self.assertEqual(spool.get_log_cursor("route/test"), "native-msg-1")

        # Tick 2: integration runs again with same native log
        integration.tick(now=250.0)
        integration.tick(now=250.0)

        # Assert duplicate effects = ZERO
        self.assertEqual(len(transport.sent), 1, "Duplicate effects must be ZERO: no duplicate reply sent")

    def test_two_concurrent_writers_atomic_and_capacity_failure_preservation(self):
        """Two concurrent writers atomically insert records.
        When capacity failure triggers, existing pending records, intents, and cursors are preserved."""
        import concurrent.futures

        spool = SQLiteSpool(
            self.db_path,
            max_payload_bytes=500,
            max_storage_bytes=1000,  # Room for exactly two 500-byte payloads
        )

        results = []
        errors = []

        def worker(key: str, payload: bytes):
            try:
                ok = spool.enqueue(key, "route/concurrent", payload)
                results.append((key, ok))
            except Exception as exc:
                errors.append((key, exc))

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            # Submit 4 requests concurrently for 500-byte payloads
            futures = [
                executor.submit(worker, "c-1", b"1" * 500),
                executor.submit(worker, "c-2", b"2" * 500),
                executor.submit(worker, "c-3", b"3" * 500),
                executor.submit(worker, "c-4", b"4" * 500),
            ]
            concurrent.futures.wait(futures)

        # Exactly 2 inserts should succeed and 2 should raise SpoolStorageLimitReached
        self.assertEqual(len(results), 2, "Exactly 2 payloads fit in 1000-byte capacity")
        self.assertEqual(len(errors), 2, "Overflowing inserts raise capacity failure")
        for k, err in errors:
            self.assertIsInstance(err, SpoolStorageLimitReached)

        # Verify old data is completely preserved
        with spool._get_conn() as conn:
            rows = conn.execute("SELECT * FROM outbound_spool").fetchall()
            self.assertEqual(len(rows), 2, "Database must preserve all admitted rows without data loss")

        # Verify idempotent retry of an admitted key returns True even though spool is full
        first_admitted_key = results[0][0]
        admitted_payload = b"1" * 500 if first_admitted_key == "c-1" else b"2" * 500
        replay_ok = spool.enqueue(first_admitted_key, "route/concurrent", admitted_payload)
        self.assertTrue(replay_ok, "Idempotent retry of admitted key must return True at full capacity")

    def test_reconnect_and_lost_http_receipt_stability(self):
        """Transport network failure on individual rows does not abort subsequent messages;
        reconnect resets backoff for immediate retry."""
        class FlakyMockTransport:
            def __init__(self):
                self.fail_keys = {"fail-key"}
                self.calls = []

            def send_payload(self, route: str, payload: bytes) -> bool:
                data = json.loads(payload.decode("utf-8"))
                key = data.get("idempotency_key", "")
                self.calls.append(key)
                if key in self.fail_keys:
                    raise ConnectionResetError("Connection lost to Hub")
                return True

        spool = SQLiteSpool(self.db_path)
        transport = FlakyMockTransport()
        integration = HubOutboundIntegration(spool=spool, transport=transport)

        # Enqueue 3 messages: fail-key, success-key-1, success-key-2
        spool.enqueue("fail-key", "route/test", json.dumps({"idempotency_key": "fail-key", "body": "f"}).encode("utf-8"))
        spool.enqueue("success-1", "route/test", json.dumps({"idempotency_key": "success-1", "body": "s1"}).encode("utf-8"))
        spool.enqueue("success-2", "route/test", json.dumps({"idempotency_key": "success-2", "body": "s2"}).encode("utf-8"))

        now = 1000.0
        # Tick 1: fail-key encounters ConnectionResetError, but success-1 and success-2 MUST still be processed
        integration.tick(now=now)

        with spool._get_conn() as conn:
            fail_row = conn.execute("SELECT * FROM outbound_spool WHERE idempotency_key='fail-key'").fetchone()
            self.assertEqual(fail_row["status"], "failed")
            self.assertIn("ConnectionResetError", fail_row["error_text"])

            s1_row = conn.execute("SELECT * FROM outbound_spool WHERE idempotency_key='success-1'").fetchone()
            self.assertEqual(s1_row["status"], "delivered")

            s2_row = conn.execute("SELECT * FROM outbound_spool WHERE idempotency_key='success-2'").fetchone()
            self.assertEqual(s2_row["status"], "delivered")

        # Network reconnects
        transport.fail_keys.clear()
        integration.on_reconnect()  # Resets retry backoffs

        # Next tick immediately retries fail-key
        integration.tick(now=now + 1.0)
        with spool._get_conn() as conn:
            retried_row = conn.execute("SELECT * FROM outbound_spool WHERE idempotency_key='fail-key'").fetchone()
            self.assertEqual(retried_row["status"], "delivered")

    def test_physical_storage_budget_enforcement(self):
        """Enforces physical storage budget (max_physical_bytes) and prevents unbounded DB growth."""
        spool = SQLiteSpool(
            self.db_path,
            max_payload_bytes=10000,
            max_storage_bytes=1000000,
            max_physical_bytes=180 * 1024,  # 180 KiB physical budget
            retention_sec=0.0,
            tombstone_retention_sec=0.0,
            max_tombstones=5,
        )

        now = 1000.0
        # Insert pending records (which cannot be pruned) until physical capacity is reached
        reached_limit = False
        for i in range(100):
            now += 1.0
            try:
                spool.enqueue(f"phys-key-{i}", "route/phys", b"z" * 4000, now=now)
            except SpoolStorageLimitReached:
                reached_limit = True
                break

        self.assertTrue(reached_limit, "Physical storage limit must be enforced when physical budget is reached")
        # Physical size remains within budget
        self.assertLessEqual(spool.get_physical_size(), 180 * 1024 + 10000)


class TestR7StorageAntiReplayAndSenderDiscoveryContract(unittest.TestCase):
    """Rigorous qualification tests for R7 storage bounds, persistent anti-replay,
    connection PRAGMA inheritance and closure, and genuine sender discovery."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "r7_contract.db"

    def tearDown(self):
        self.tmp.cleanup()

    def test_unpatched_head_metadata_physical_budget_reproduction(self):
        """Replicates HEAD unpatched b67a scenario: 200,000-char workspace is rejected upfront
        and physical size remains strictly bounded."""
        spool = SQLiteSpool(self.db_path, max_physical_bytes=200000)

        # 1. 200,000-char workspace rejected by input validation
        with self.assertRaises(ValueError) as ctx:
            spool.register_route("route/overflow", "w" * 200000, "tag-1")
        self.assertIn("exceeds maximum length", str(ctx.exception))

        # Ensure physical size did NOT explode to 350,016 bytes (remains within 200,000 bytes)
        self.assertLessEqual(spool.get_physical_size(), 200000)
        self.assertIsNone(spool.get_enrolled_route("route/overflow"))

        # 2. Tight physical budget rejection with atomic rollback
        spool_tight = SQLiteSpool(
            Path(self.tmp.name) / "tight.db",
            max_physical_bytes=MIN_PHYSICAL_SCHEMA_BYTES + 4096,
        )
        # Registering route succeeds within headroom
        spool_tight.register_route("route/valid", "/tmp/ws1", "tag-1")
        self.assertIsNotNone(spool_tight.get_enrolled_route("route/valid"))

    def test_unpatched_head_route_total_cap_reproduction(self):
        """In HEAD unpatched, max_total_records=3 permitted 9 routes. Now strictly capped at 3."""
        spool = SQLiteSpool(self.db_path, max_total_records=3)
        spool.register_route("route/1", "/tmp/ws1", "t1")
        spool.register_route("route/2", "/tmp/ws2", "t2")
        spool.register_route("route/3", "/tmp/ws3", "t3")
        self.assertEqual(spool.get_total_records(), 3)

        # 4th route must be rejected fail-closed
        with self.assertRaises(SpoolStorageLimitReached) as ctx:
            spool.register_route("route/4", "/tmp/ws4", "t4")
        self.assertIn("total records", str(ctx.exception))
        self.assertEqual(spool.get_total_records(), 3)
        self.assertIsNone(spool.get_enrolled_route("route/4"))

    def test_expired_key_probe_1_zero_duplicate_effects(self):
        """Replicates probe_1.py: unmodified exact-key enqueue->transport->delivered->prune->tombstone
        expiry->same-key replay produces ZERO extra transport sends across versioned and opaque keys."""
        spool = SQLiteSpool(
            self.db_path,
            retention_sec=0.0,
            tombstone_retention_sec=10.0,
            max_tombstones=3,
        )

        class MockTransport:
            def __init__(self):
                self.sent = []
            def send_payload(self, route: str, payload: bytes) -> bool:
                self.sent.append((route, payload))
                return True

        transport = MockTransport()
        integration = HubOutboundIntegration(spool=spool, transport=transport)

        # Part A: Versioned key lifecycle
        key_v1 = make_versioned_key("v1-key-001", now=100.0)
        ok = spool.enqueue(key_v1, "route/test", b"payload-v1", now=100.0)
        self.assertTrue(ok)
        integration.tick(now=100.0)
        self.assertEqual(len(transport.sent), 1, "First versioned message sent")

        # Mark delivered and prune into tombstones
        spool.mark_delivered(1, now=100.0)
        spool.prune_delivered(retention_sec=0.0, now=200.0)
        # Advance clock past tombstone retention (prunes versioned tombstone, advances oldest_tombstone_cutoff)
        spool.prune_tombstones(tombstone_retention_sec=10.0, now=250.0)

        # Verify oldest_tombstone_cutoff is watermarked
        cutoff = spool.get_tombstone_cutoff()
        self.assertIsNotNone(cutoff)
        self.assertGreaterEqual(cutoff, 100.0)

        # Replay exact same versioned key: rejected at ingress (returns False)
        replay_v1_ok = spool.enqueue(key_v1, "route/test", b"payload-v1", now=260.0)
        self.assertFalse(replay_v1_ok, "Expired versioned key must be rejected at ingress")
        integration.tick(now=260.0)
        self.assertEqual(len(transport.sent), 1, "Zero extra transport sends for expired versioned key")

        # Part B: Legacy opaque key lifecycle (safe bounded hold)
        key_opaque = "legacy-opaque-002"
        ok2 = spool.enqueue(key_opaque, "route/test", b"payload-opaque", now=100.0)
        self.assertTrue(ok2)
        integration.tick(now=100.0)
        self.assertEqual(len(transport.sent), 2, "Second message sent")

        spool.mark_delivered(2, now=100.0)
        spool.prune_delivered(retention_sec=0.0, now=200.0)
        # Prune tombstones by age does NOT delete legacy opaque keys
        spool.prune_tombstones(tombstone_retention_sec=10.0, now=250.0)

        # Replay exact legacy opaque key: returns True (stable idempotent outcome) without inserting new row
        replay_opaque_ok = spool.enqueue(key_opaque, "route/test", b"payload-opaque", now=260.0)
        self.assertTrue(replay_opaque_ok, "Legacy opaque key returns stable idempotent outcome")
        integration.tick(now=260.0)
        self.assertEqual(len(transport.sent), 2, "Zero extra transport sends for legacy opaque key")

    def test_versioned_key_age_expiry_rejected_at_all_ingress(self):
        """Versioned key older than oldest_tombstone_cutoff is rejected across enqueue, record_mapping, record_intent."""
        spool = SQLiteSpool(self.db_path)
        spool.set_metadata("oldest_tombstone_cutoff", "500.0")

        expired_key = make_versioned_key("expired-probe", now=200.0)

        # 1. enqueue ingress rejects
        self.assertFalse(spool.enqueue(expired_key, "route/test", b"hello", now=600.0))

        # 2. record_mapping ingress rejects
        with self.assertRaises(IdempotencyConflictError) as ctx:
            spool.record_mapping(expired_key, "/tmp/ws", "tag1")
        self.assertIn("Expired message mapping identity", str(ctx.exception))

        # 3. record_intent ingress rejects
        with self.assertRaises(IdempotencyConflictError) as ctx:
            spool.record_intent("intent-exp", expired_key, "/tmp/ws", "tag1", "hello")
        self.assertIn("Expired delivery intent identity", str(ctx.exception))

        # Fresh versioned key is admitted cleanly
        fresh_key = make_versioned_key("fresh-probe", now=800.0)
        self.assertTrue(spool.enqueue(fresh_key, "route/test", b"hello", now=800.0))

    def test_pragma_inherited_on_all_new_connections_and_closed(self):
        """Every SQLite connection enforces PRAGMA limits and is guaranteed closed upon context exit."""
        spool = SQLiteSpool(self.db_path, max_pages=300)

        # Verify PRAGMAs on fresh raw connection
        raw_conn = spool._create_raw_conn()
        try:
            sync = raw_conn.execute("PRAGMA synchronous").fetchone()[0]
            self.assertEqual(sync, 1, "PRAGMA synchronous must be NORMAL (1)")

            jsl = raw_conn.execute("PRAGMA journal_size_limit").fetchone()[0]
            self.assertEqual(jsl, spool.journal_size_limit)

            acp = raw_conn.execute("PRAGMA wal_autocheckpoint").fetchone()[0]
            self.assertEqual(acp, 100)

            mpc = raw_conn.execute("PRAGMA max_page_count").fetchone()[0]
            self.assertEqual(mpc, 300)
        finally:
            raw_conn.close()

        # Verify connection closure in _get_connection context manager
        captured_conn = None
        with spool._get_connection() as conn:
            captured_conn = conn
            row = conn.execute("SELECT 1").fetchone()
            self.assertEqual(row[0], 1)

        # Connection must be closed outside the context
        with self.assertRaises(sqlite3.ProgrammingError):
            captured_conn.execute("SELECT 1")

    def test_all_mutating_methods_enforce_utf8_bounds_and_capacity(self):
        """All mutating methods reject NUL bytes, oversized inputs, and atomic rollbacks preserve state."""
        spool = SQLiteSpool(self.db_path)

        # 1. register_route bounds
        with self.assertRaises(ValueError):
            spool.register_route("route\x00bad", "/tmp/ws", "tag")
        with self.assertRaises(ValueError):
            spool.register_route("route", "/tmp/ws\x00bad", "tag")
        with self.assertRaises(ValueError):
            spool.register_route("route", "/tmp/ws", "tag\x00bad")
        with self.assertRaises(ValueError):
            spool.register_route("r" * 300, "/tmp/ws", "tag")  # >256B

        # 2. record_mapping bounds
        with self.assertRaises(ValueError):
            spool.record_mapping("map\x00bad", "/tmp/ws", "tag")
        with self.assertRaises(ValueError):
            spool.record_mapping("m" * 300, "/tmp/ws", "tag")  # >256B

        # 3. update_mapping_status bounds
        with self.assertRaises(ValueError):
            spool.update_mapping_status("m1", "status\x00bad")

        # 4. record_intent bounds
        with self.assertRaises(ValueError):
            spool.record_intent("intent\x00bad", "k1", "/tmp/ws", "tag", "text")
        with self.assertRaises(ValueError):
            spool.record_intent("i1", "k\x00bad", "/tmp/ws", "tag", "text")
        with self.assertRaises(ValueError):
            spool.record_intent("i1", "k1", "/tmp/ws", "tag", "t" * (MAX_PAYLOAD_TEXT_BYTES + 1))

        # 5. update_intent_status bounds
        with self.assertRaises(ValueError):
            spool.update_intent_status("k\x00bad", "sent")

        # 6. set_cursor bounds
        with self.assertRaises(ValueError):
            spool.set_cursor("route\x00bad", receipt_cursor="c1")
        with self.assertRaises(ValueError):
            spool.set_cursor("route", receipt_cursor="c\x00bad")

        # 7. mark_delivered / mark_ambiguous / mark_failed msg_id type checks
        with self.assertRaises(ValueError):
            spool.mark_delivered("non-int-id")  # type: ignore
        with self.assertRaises(ValueError):
            spool.mark_ambiguous("non-int-id", "err")  # type: ignore
        with self.assertRaises(ValueError):
            spool.mark_failed("non-int-id", "err")  # type: ignore

        # 8. enqueue bounds
        with self.assertRaises(ValueError):
            spool.enqueue("k\x00bad", "route", b"pay")
        with self.assertRaises(ValueError):
            spool.enqueue("k", "route\x00bad", b"pay")

        # Verify no rogue records were inserted
        self.assertEqual(spool.get_total_records(), 0)

    def test_transient_physical_occupancy_with_held_reader(self):
        """Writers and checkpoints do not block or crash while a reader holds a read transaction."""
        spool = SQLiteSpool(self.db_path)
        spool.enqueue("initial-key", "route/concur", b"init-payload")

        # Reader holds open read transaction
        reader = spool._create_raw_conn()
        try:
            reader.execute("BEGIN DEFERRED")
            rows = reader.execute("SELECT * FROM outbound_spool").fetchall()
            self.assertEqual(len(rows), 1)

            # Writer performs mutations while reader is active
            for i in range(5):
                spool.enqueue(f"writer-key-{i}", "route/concur", f"payload-{i}".encode("utf-8"))

            # Checkpoint does NOT hang or raise; uses PASSIVE checkpoint
            spool.checkpoint_and_reclaim()

            # Writer verifies all 6 rows are committed
            self.assertEqual(spool.get_total_records(), 6)
        finally:
            reader.commit()
            reader.close()

        # After reader closes, checkpoint reclaims WAL cleanly
        spool.checkpoint_and_reclaim()
        self.assertLessEqual(spool.get_physical_size(), spool.max_physical_bytes)

    def test_real_rust_shaped_cli_fixture_sender_discovery_and_unbound_denial(self):
        """Comprehensive verification using real-Rust-shaped CLI executable:
        - Forbids --from with cross-workspace --workspace send
        - Refuses unbound sender context truthfully without --from/env impersonation
        - Discovers genuine sender context when bound
        - Full simulated two-way Hub inbound -> native recipient -> exact ACK -> actual reply -> Hub
        - Stable IDs across restart and zero duplicate effects."""
        import stat

        state_dir = Path(self.tmp.name) / "state_root"
        state_dir.mkdir(parents=True, exist_ok=True)
        fake_cli_path = Path(self.tmp.name) / "fake_aplexer"

        # Executable Python script modeling Rust cloudflare-aplexer-protocol message_routing.rs
        cli_code = f"""#!/usr/bin/env python3
import sys
import os
import json
import hashlib
from pathlib import Path

state_root = Path(os.environ.get("APLEXER_STATE_DIR", "{state_dir}"))
args = sys.argv[1:]

if not args:
    sys.exit(0)

cmd = args[0]
if cmd == "list":
    sessions_file = state_root / "sessions.json"
    if sessions_file.is_file():
        sys.stdout.write(sessions_file.read_text(encoding="utf-8"))
    else:
        sys.stdout.write("[]")
    sys.exit(0)

if cmd == "message":
    sub = args[1] if len(args) > 1 else ""
    if sub == "log":
        ws = None
        for i, a in enumerate(args):
            if a == "--workspace" and i + 1 < len(args):
                ws = args[i + 1]
        if not ws:
            sys.exit(1)
        raw_bytes = ws.encode("utf-8")
        h = hashlib.sha256(raw_bytes).hexdigest()[:32]
        log_file = state_root / "messages" / h / "log.json"
        if log_file.is_file():
            sys.stdout.write(log_file.read_text(encoding="utf-8"))
        else:
            sys.stdout.write("[]")
        sys.exit(0)

    if sub == "deliver":
        sys.stdout.write(json.dumps({{"status": "delivered"}}))
        sys.exit(0)

    if sub == "send":
        ws = None
        has_from = False
        to_tag = None
        data_str = None
        text = ""

        i = 2
        while i < len(args):
            a = args[i]
            if a == "--workspace" and i + 1 < len(args):
                ws = args[i + 1]
                i += 2
            elif a == "--from":
                has_from = True
                i += 2
            elif a == "--to" and i + 1 < len(args):
                to_tag = args[i + 1]
                i += 2
            elif a == "--data" and i + 1 < len(args):
                data_str = args[i + 1]
                i += 2
            elif a == "--":
                text = " ".join(args[i + 1:])
                break
            else:
                i += 1

        if ws and has_from:
            sys.stderr.write("error: --from cannot be used with cross-workspace --workspace delivery\\n")
            sys.exit(2)

        session_id = os.environ.get("APLEXER_SESSION_ID")
        if not session_id:
            sys.stderr.write("error: cross-workspace messaging requires an aplexer session identity\\n")
            sys.exit(1)

        sessions_file = state_root / "sessions.json"
        sender_info = {{}}
        if sessions_file.is_file():
            try:
                sessions = json.loads(sessions_file.read_text(encoding="utf-8"))
                for s in sessions:
                    if s.get("id") == session_id:
                        if ws and s.get("workspace") and str(Path(s.get("workspace")).resolve()) != str(Path(ws).resolve()):
                            continue
                        sender_info = s
                        break
            except Exception:
                pass
        
        if not sender_info:
            sys.stderr.write(f"error: calling aplexer session {{session_id}} has no matching session record\\n")
            sys.exit(1)

        raw_bytes = ws.encode("utf-8")
        h = hashlib.sha256(raw_bytes).hexdigest()[:32]
        ws_dir = state_root / "messages" / h
        ws_dir.mkdir(parents=True, exist_ok=True)
        log_file = ws_dir / "log.json"
        existing = []
        if log_file.is_file():
            try:
                existing = json.loads(log_file.read_text(encoding="utf-8"))
            except Exception:
                existing = []

        counter = len(existing) + 1
        msg_id = f"11111111-1111-1111-1111-111111111{{counter:03d}}"
        data_obj = json.loads(data_str) if data_str else {{}}
        envelope = {{
            "id": msg_id,
            "workspace": ws,
            "from": {{"tag": sender_info["tag"], "session_id": sender_info.get("session_id")}},
            "to": {{"tag": to_tag}},
            "body": text,
            "data": data_obj,
            "kind": "note",
        }}
        existing.append(envelope)
        log_file.write_text(json.dumps(existing, indent=2), encoding="utf-8")

        sys.stdout.write(json.dumps({{"id": msg_id, "status": "sent"}}))
        sys.exit(0)

sys.exit(0)
"""
        fake_cli_path.write_text(cli_code, encoding="utf-8")
        fake_cli_path.chmod(fake_cli_path.stat().st_mode | stat.S_IXUSR | stat.S_IRUSR)

        ws_agent = "/tmp/test_workspace_agent"
        tag_agent = "agent-alpha"
        uuid_agent = "11111111-1111-4111-8111-111111111111"

        # Register sessions in mock state root
        sessions = [
            {"id": uuid_agent, "session_id": uuid_agent, "workspace": ws_agent, "tag": tag_agent, "reported_state": "idle"},
            {"id": "00000000-0000-4000-8000-000000000000", "session_id": "00000000-0000-4000-8000-000000000000", "workspace": ws_agent, "tag": "host-hub", "reported_state": "idle"}
        ]
        (state_dir / "sessions.json").write_text(json.dumps(sessions), encoding="utf-8")

        spool = SQLiteSpool(self.db_path)
        bridge = AplexerBridge(aplexer_bin=str(fake_cli_path), spool=spool, state_root=state_dir)

        # 1. Unbound sender denial: no APLEXER_SESSION_ID
        import os
        old_session = os.environ.get("APLEXER_SESSION_ID")
        if "APLEXER_SESSION_ID" in os.environ:
            del os.environ["APLEXER_SESSION_ID"]
            
        unbound_ok, amb, err = bridge.send_message(ws_agent, tag_agent, {"text": "hello"})
        self.assertFalse(unbound_ok, "Send must fail closed when sender context is unbound")
        self.assertIn("requires an aplexer session identity", err)

        # 2. Forbids --from: verify real-Rust shape rejects --from flag
        res_from = bridge._run_cmd(["message", "send", "--workspace", ws_agent, "--from", "impostor", "--to", tag_agent, "--", "test"])
        self.assertEqual(res_from.returncode, 2)
        self.assertIn("--from cannot be used with cross-workspace --workspace delivery", res_from.stderr)

        # 3. Bind genuine sender context
        os.environ["APLEXER_SESSION_ID"] = "00000000-0000-4000-8000-000000000000"
        try:

            # 4. Hub Inbound -> Native recipient
            inbound_payload = {
                "id": "hub-msg-999",
                "body": "Do work task 42",
                "from_actor": "hub-coordinator",
                "to_actor": tag_agent,
                "thread_id": "thread-42",
            }
            spool.register_route("route/agent", ws_agent, tag_agent, consumer_uuid=uuid_agent)

            disp_ok, disp_err = dispatch_inbound(
                inbound_payload,
                workspace=ws_agent,
                tag=tag_agent,
                bridge=bridge,
                spool=spool,
                route="route/agent",
                consumer_uuid=uuid_agent,
            )
            self.assertTrue(disp_ok, f"dispatch_inbound should succeed: {disp_err}")

            # Verify mapping is marked delivered with native message ID
            mapping = spool.get_message_mapping("hub-msg-999")
            self.assertIsNotNone(mapping)
            self.assertEqual(mapping["status"], "delivered")
            self.assertEqual(mapping["native_message_id"], "11111111-1111-1111-1111-111111111001")

            # 5. Native recipient writes genuine ACK into cursor file
            raw_ws = ws_agent.encode("utf-8")
            h = hashlib.sha256(raw_ws).hexdigest()[:32]
            ws_msg_dir = state_dir / "messages" / h
            ws_msg_dir.mkdir(parents=True, exist_ok=True)
            (ws_msg_dir / "workspace.json").write_text(json.dumps({"workspace": ws_agent}), encoding="utf-8")
            cursors_dir = ws_msg_dir / "cursors"
            cursors_dir.mkdir(parents=True, exist_ok=True)
            (cursors_dir / f"{uuid_agent}.json").write_text(
                json.dumps({"acked_through": "11111111-1111-1111-1111-111111111001", "exceptions": []}),
                encoding="utf-8",
            )

            # track_ack verifies recipient-only provenance and marks mapping acked
            ack_ok = track_ack(
                route="route/agent",
                message_id="hub-msg-999",
                consumer_uuid=uuid_agent,
                spool=spool,
                workspace=ws_agent,
                state_root=state_dir,
            )
            self.assertTrue(ack_ok, "Genuine recipient ACK must be verified and accepted")
            mapping = spool.get_message_mapping("hub-msg-999")
            self.assertEqual(mapping["status"], "acked")

            # 6. Native recipient generates actual reply
            reply_envelope = {
                "id": "native-reply-999",
                "workspace": ws_agent,
                "from": {"tag": tag_agent, "session_id": uuid_agent},
                "to": {"tag": "host-hub"},
                "reply_to": "11111111-1111-1111-1111-111111111001",
                "body": "Task 42 complete",
                "kind": "reply",
            }
            reply_key = handle_reply(reply_envelope, original_hub_id="hub-msg-999", spool=spool)
            self.assertIsNotNone(reply_key)
            self.assertTrue(reply_key.startswith("reply-"))

            # Verify staged reply in outbound_spool
            pending_replies = spool.get_pending(route="hub/reply")
            self.assertEqual(len(pending_replies), 1)
            staged_payload = json.loads(pending_replies[0]["payload"].decode("utf-8"))
            self.assertEqual(staged_payload["reply_to"], "hub-msg-999")
            self.assertEqual(staged_payload["body"], "Task 42 complete")
            self.assertEqual(staged_payload["to_actor"], "hub-coordinator")

            # 7. Restart verification: state and IDs are stable
            spool_restarted = SQLiteSpool(self.db_path)
            reply_key_retry = handle_reply(reply_envelope, original_hub_id="hub-msg-999", spool=spool_restarted)
            self.assertEqual(reply_key_retry, reply_key, "Reply key must be stable across restart")
            # Ensure no duplicate was inserted into outbound_spool
            self.assertEqual(len(spool_restarted.get_pending(route="hub/reply")), 1)

        finally:
            if old_session is not None:
                os.environ["APLEXER_SESSION_ID"] = old_session
            else:
                if "APLEXER_SESSION_ID" in os.environ:
                    del os.environ["APLEXER_SESSION_ID"]


class TestR8VerificationDefectsAndContractHardening(unittest.TestCase):
    """Regression suite for R8 defect verifications: exact log reconciliation, deny-redirect opener,
    bounded HTTP response reads, default closed C888 runtime gate, body/schema limits,
    nonfinite versioned key rejection, and held-reader physical budget enforcement."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "test_r8.db"

    def tearDown(self):
        self.tmp.cleanup()

    def test_r8_send_message_exact_reconciliation_positive_and_mismatches(self):
        """Validates exact log reconciliation: mismatched body, recipient tag, workspace, or multiple
        matches remain held as ambiguous with zero premature success; exact match reconciles and updates
        intent status to sent."""
        state_dir = Path(self.tmp.name) / "aplexer_state"
        state_dir.mkdir(parents=True, exist_ok=True)
        ws_expected = str(Path(self.tmp.name) / "ws_target")
        tag_expected = "target-recipient"
        uuid_expected = "11111111-1111-4111-8111-111111111111"

        # Active sender context bound
        (state_dir / "active_sender.json").write_text(
            json.dumps({"tag": "host-hub", "session_id": "00000000-0000-4000-8000-000000000000"}),
            encoding="utf-8",
        )
        # Target session in sessions.json
        (state_dir / "sessions.json").write_text(
            json.dumps([{"session_id": uuid_expected, "workspace": ws_expected, "tag": tag_expected}]),
            encoding="utf-8",
        )

        mock_logs_file = Path(self.tmp.name) / "mock_logs.json"
        mock_cli_script = Path(self.tmp.name) / "mock_aplexer.py"
        mock_cli_script.write_text(f"""#!/usr/bin/env python3
import sys, json
from pathlib import Path

args = sys.argv[1:]
if not args:
    sys.exit(1)

if args[0] == "list":
    sessions = [{{"id": "{uuid_expected}", "workspace": "{ws_expected}", "tag": "{tag_expected}"}}]
    print(json.dumps(sessions))
    sys.exit(0)

if args[:2] == ["message", "send"]:
    # Simulate lost IPC receipt: command fails after partial effect
    sys.stderr.write("simulated lost IPC receipt\\n")
    sys.exit(1)

if args[:2] == ["message", "log"]:
    log_path = Path("{mock_logs_file}")
    if log_path.exists():
        print(log_path.read_text(encoding="utf-8"))
    else:
        print("[]")
    sys.exit(0)

sys.exit(2)
""")
        mock_cli_script.chmod(0o755)

        spool = SQLiteSpool(self.db_path)
        bridge = AplexerBridge(str(mock_cli_script), spool=spool, state_root=state_dir)

        # 1. Mismatched body: log body differs from expected body
        key_1 = "key-mismatch-body"
        mock_logs_file.write_text(json.dumps([{
            "schema_version": 1,
            "id": "0190abc0-0000-7000-8000-000000000001",
            "workspace": ws_expected,
            "to": {"tag": tag_expected, "session_id": uuid_expected},
            "body": "DIFFERENT body content",
            "data": {"idempotency_key": key_1, "workspace": ws_expected, "recipient": tag_expected},
        }]))
        ok, amb, err = bridge.send_message(ws_expected, tag_expected, {"text": "EXPECTED body"}, idempotency_key=key_1)
        self.assertFalse(ok)
        self.assertTrue(amb)
        self.assertIn("Mismatched body text", err)
        intent = spool.get_intent(key_1)
        self.assertNotEqual(intent["status"], "sent")

        # 2. Mismatched recipient: log recipient differs
        key_2 = "key-mismatch-recipient"
        mock_logs_file.write_text(json.dumps([{
            "schema_version": 1,
            "id": "0190abc0-0000-7000-8000-000000000002",
            "workspace": ws_expected,
            "to": {"tag": "OTHER-tag", "session_id": uuid_expected},
            "body": "EXPECTED body",
            "data": {"idempotency_key": key_2, "workspace": ws_expected, "recipient": "OTHER-tag"},
        }]))
        ok, amb, err = bridge.send_message(ws_expected, tag_expected, {"text": "EXPECTED body"}, idempotency_key=key_2)
        self.assertFalse(ok)
        self.assertTrue(amb)
        self.assertIn("Mismatched recipient tag", err)
        intent = spool.get_intent(key_2)
        self.assertNotEqual(intent["status"], "sent")

        # 3. Mismatched workspace: log workspace differs
        key_3 = "key-mismatch-workspace"
        mock_logs_file.write_text(json.dumps([{
            "schema_version": 1,
            "id": "0190abc0-0000-7000-8000-000000000003",
            "workspace": "/different/workspace",
            "to": {"tag": tag_expected, "session_id": uuid_expected},
            "body": "EXPECTED body",
            "data": {"idempotency_key": key_3, "workspace": "/different/workspace", "recipient": tag_expected},
        }]))
        ok, amb, err = bridge.send_message(ws_expected, tag_expected, {"text": "EXPECTED body"}, idempotency_key=key_3)
        self.assertFalse(ok)
        self.assertTrue(amb)
        self.assertIn("Mismatched workspace", err)
        intent = spool.get_intent(key_3)
        self.assertNotEqual(intent["status"], "sent")

        # 4. Multiple matches: ambiguous multiple records with same key
        key_4 = "key-multiple-matches"
        mock_logs_file.write_text(json.dumps([
            {
                "schema_version": 1,
                "id": "0190abc0-0000-7000-8000-000000000004",
                "workspace": ws_expected,
                "to": {"tag": tag_expected, "session_id": uuid_expected},
                "body": "EXPECTED body",
                "data": {"idempotency_key": key_4, "workspace": ws_expected, "recipient": tag_expected},
            },
            {
                "schema_version": 1,
                "id": "0190abc0-0000-7000-8000-000000000005",
                "workspace": ws_expected,
                "to": {"tag": tag_expected, "session_id": uuid_expected},
                "body": "EXPECTED body",
                "data": {"idempotency_key": key_4, "workspace": ws_expected, "recipient": tag_expected},
            }
        ]))
        ok, amb, err = bridge.send_message(ws_expected, tag_expected, {"text": "EXPECTED body"}, idempotency_key=key_4)
        self.assertFalse(ok)
        self.assertTrue(amb)
        self.assertIn("Multiple matching native log entries", err)

        # 5. Exact match across all fields: reconciles successfully
        key_5 = "key-exact-match"
        native_id = "0190abc0-0000-7000-8000-000000000006"
        mock_logs_file.write_text(json.dumps([{
            "schema_version": 1,
            "id": native_id,
            "workspace": ws_expected,
            "to": {"tag": tag_expected, "session_id": uuid_expected},
            "body": "EXPECTED body",
            "data": {"idempotency_key": key_5, "workspace": ws_expected, "recipient": tag_expected},
        }]))
        ok, amb, mid = bridge.send_message(ws_expected, tag_expected, {"text": "EXPECTED body"}, idempotency_key=key_5)
        self.assertTrue(ok)
        self.assertFalse(amb)
        self.assertEqual(mid, native_id)
        intent = spool.get_intent(key_5)
        self.assertEqual(intent["status"], "sent")

    def test_r8_c888_deny_redirect_opener_blocks_all_redirects(self):
        """Verifies that C888BusClient refuses 301, 302, 303, 307, 308 redirects fail-closed,
        preventing cross-origin or redirect credential forwarding."""
        sink_requests = []

        class SinkHandler(BaseHTTPRequestHandler):
            def log_message(self, *args): pass
            def do_GET(self):
                sink_requests.append({
                    "path": self.path,
                    "auth": self.headers.get("Authorization"),
                })
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"sink": true}')

        sink_server = HTTPServer(("127.0.0.1", 0), SinkHandler)
        sink_thread = threading.Thread(target=sink_server.serve_forever, daemon=True)
        sink_thread.start()

        class RedirectHandler(BaseHTTPRequestHandler):
            def log_message(self, *args): pass
            def do_GET(self):
                target = f"http://127.0.0.1:{sink_server.server_port}/leaked"
                if self.path == "/301":
                    code = 301
                elif self.path == "/307":
                    code = 307
                elif self.path == "/308":
                    code = 308
                else:
                    code = 302
                self.send_response(code)
                self.send_header("Location", target)
                self.send_header("Content-Length", "0")
                self.end_headers()

        redir_server = HTTPServer(("127.0.0.1", 0), RedirectHandler)
        redir_thread = threading.Thread(target=redir_server.serve_forever, daemon=True)
        redir_thread.start()

        try:
            client = C888BusClient(
                f"http://127.0.0.1:{redir_server.server_port}",
                token_provider=lambda: "SECRET-TOKEN-12345",
                allow_loopback_http=True,
                fixture_opt_in=True,
            )

            for path, expected_code in [("/302", 302), ("/301", 301), ("/307", 307), ("/308", 308)]:
                status, data = client._execute_http("GET", path)
                self.assertEqual(status, expected_code, f"Redirect status should be returned fail-closed for {path}")

            # Sink must have received ZERO requests; secret was never leaked
            self.assertEqual(len(sink_requests), 0, "No credentials or requests must reach redirected sink")
        finally:
            redir_server.shutdown()
            sink_server.shutdown()
            redir_server.server_close()
            sink_server.server_close()

    def test_r8_c888_runtime_gate_default_closed(self):
        """Verifies C888BusClient runtime gate: default closed absent explicit candidate/fixture opt-in
        or accepted Hub owner handoff."""
        # 1. Plain loopback http without allow_loopback_http raises InsecureTransportError
        with self.assertRaises(InsecureTransportError) as ctx:
            C888BusClient("http://127.0.0.1:9999")
        self.assertIn("HTTPS required for non-loopback endpoints", str(ctx.exception))

        # 2. HTTPS without fixture_opt_in or owner_handoff raises when executing HTTP
        client_no_opt_in = C888BusClient(
            "https://127.0.0.1:9999",
            fixture_opt_in=False,
        )
        with self.assertRaises(WireContractError) as ctx:
            client_no_opt_in._execute_http("GET", "/test")
        self.assertIn("closed by default", str(ctx.exception))

        # 3. Explicit fixture_opt_in=True passes runtime gate check (fails on connection refused, not gate)
        client_opted_in = C888BusClient(
            "http://127.0.0.1:9999",
            allow_loopback_http=True,
            fixture_opt_in=True,
        )
        with self.assertRaises(WireContractError) as ctx:
            client_opted_in._execute_http("GET", "/test")
        # Connection error, not gate error
        self.assertNotIn("closed by default", str(ctx.exception))

    def test_r8_c888_oversized_body_and_schema_validation(self):
        """Verifies incoming message body cap (16384 bytes) and schema validation."""
        class BodyFixtureHandler(BaseHTTPRequestHandler):
            def log_message(self, *args): pass
            def do_GET(self):
                if self.path.endswith("/oversized"):
                    msg = {"id": "msg-over", "body": "x" * 17000, "created_at": 1700000000000, "expires_at": 1800000000000}
                elif self.path.endswith("/nul-byte"):
                    msg = {"id": "msg-nul", "body": "hello\x00world", "created_at": 1700000000000, "expires_at": 1800000000000}
                elif self.path.endswith("/nan-time"):
                    msg = {"id": "msg-nan", "body": "valid", "created_at": float("nan"), "expires_at": 1800000000000}
                elif self.path.endswith("/valid"):
                    msg = {"id": "msg-valid", "body": "x" * 16384, "created_at": 1700000000000, "expires_at": 1800000000000}
                else:
                    self.send_response(404); self.end_headers(); return
                data = json.dumps(msg).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

        server = HTTPServer(("127.0.0.1", 0), BodyFixtureHandler)
        threading.Thread(target=server.serve_forever, daemon=True).start()

        try:
            client = C888BusClient(
                f"http://127.0.0.1:{server.server_port}",
                allow_loopback_http=True,
                fixture_opt_in=True,
            )

            # Oversized 17000 bytes > 16384
            with self.assertRaises(WireContractError) as ctx:
                client.show_bus_message("oversized")
            self.assertIn("exceeds 16KB UTF-8 limit", str(ctx.exception))

            # Null byte in body
            with self.assertRaises(WireContractError) as ctx:
                client.show_bus_message("nul-byte")
            self.assertIn("null bytes", str(ctx.exception))

            # NaN created_at
            with self.assertRaises(WireContractError) as ctx:
                client.show_bus_message("nan-time")
            self.assertIn("integral epoch timestamp", str(ctx.exception))

            # Exactly 16384 bytes passes
            valid = client.show_bus_message("valid")
            self.assertEqual(len(valid["body"]), 16384)
        finally:
            server.shutdown()
            server.server_close()

    def test_r8_bounded_http_response_reads(self):
        """Verifies _read_bounded_response raises WireContractError when responses exceed bounds."""
        import io
        stream = io.BytesIO(b"x" * 1000)
        with self.assertRaises(WireContractError) as ctx:
            _read_bounded_response(stream, max_bytes=500)
        self.assertIn("exceeded maximum ceiling", str(ctx.exception))

        # Under limit reads successfully
        stream_ok = io.BytesIO(b"x" * 500)
        result = _read_bounded_response(stream_ok, max_bytes=500)
        self.assertEqual(len(result), 500)

    def test_r8_nonfinite_and_malformed_versioned_keys_rejected(self):
        """Verifies nonfinite (v1:nan:...), negative, future, or malformed versioned keys
        are strictly rejected across all ingress points with zero extra transport effects."""
        spool = SQLiteSpool(self.db_path, retention_sec=1, tombstone_retention_sec=1)

        for bad_key in ["v1:nan:test", "v1:inf:test", "v1:-inf:test", "v1:-1:test", "v1:abc:test", "v1:99999999999:test"]:
            self.assertFalse(spool.enqueue(bad_key, "route", b"data"))

            with self.assertRaises(IdempotencyConflictError):
                spool.record_intent(f"intent-{bad_key}", bad_key, "/tmp/ws", "tag", "body")

            with self.assertRaises(IdempotencyConflictError):
                spool.record_mapping(bad_key, "/tmp/ws", "tag", "11111111-1111-4111-8111-111111111111")

            valid, val_err = validate_native_args("/tmp/ws", "tag", "body", idempotency_key=bad_key)
            self.assertFalse(valid)
            self.assertIn("Invalid versioned idempotency key", val_err)

        # Reproduce probe_nonfinite_key: verify 0 extra effects
        class MockTransport:
            def __init__(self): self.effects = 0
            def send_payload(self, r, p): self.effects += 1; return True

        transport = MockTransport()
        loop = HubOutboundIntegration(spool=spool, transport=transport)

        # Enqueue legitimate key
        good_key = make_versioned_key("legitimate-actor", 1000.0)
        first = spool.enqueue(good_key, "route", b"fixture", now=1000.0)
        self.assertTrue(first)
        loop.process_spool(now=1000.0)
        self.assertEqual(transport.effects, 1)

        # Prune delivered and tombstones
        spool.prune_delivered(retention_sec=1, now=1010.0)
        spool.prune_tombstones(now=1020.0)

        # Attempting bad key replay returns False and produces ZERO transport effects
        self.assertFalse(spool.enqueue("v1:nan:legitimate-actor", "route", b"fixture", now=1030.0))
        loop.process_spool(now=1030.0)
        self.assertEqual(transport.effects, 1, "Transport effects must not increase on rejected key")

    def test_r8_held_reader_physical_budget_enforcement(self):
        """Replicates probe_held_reader.py: with budget 400,000 bytes, writer refuses
        before crossing cap; reader release allows fresh ingress."""
        db = Path(self.tmp.name) / "held_reader.db"
        budget = 400000
        spool = SQLiteSpool(db, max_physical_bytes=budget, max_pages=64, max_payload_bytes=2048, max_storage_bytes=65536)

        # Open held reader holding shared lock
        reader = sqlite3.connect(db)
        reader.execute("BEGIN")
        reader.execute("SELECT * FROM outbound_spool").fetchall()

        rows = []
        try:
            for i in range(20):
                try:
                    ok = spool.enqueue(f"held-{i}", "sim-route", b"x" * 2048, now=1000)
                    err = None
                except SpoolStorageLimitReached as exc:
                    ok = False
                    err = type(exc).__name__
                size = spool.get_physical_size()
                rows.append({"iteration": i, "accepted": ok, "error": err, "size": size})
        finally:
            reader.rollback()
            reader.close()

        # Check physical budget was strictly respected on EVERY iteration
        for r in rows:
            self.assertLessEqual(r["size"], budget, f"Iteration {r['iteration']} exceeded budget {budget}: {r['size']}")

        # Ensure some writes succeeded, and later writes were refused before crossing budget
        accepted_count = sum(1 for r in rows if r["accepted"])
        refused_count = sum(1 for r in rows if not r["accepted"])
        self.assertGreater(accepted_count, 0)
        self.assertGreater(refused_count, 0)

        # Checkpoint and reclaim
        spool.checkpoint_and_reclaim()

        # Fresh write succeeds after reader release
        fresh = spool.enqueue("fresh-key", "sim-route", b"fresh-data", now=1001)
        self.assertTrue(fresh, "Fresh ingress must succeed after reader release and checkpoint")



class TestR10bRegressions(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.tmp_dir) / "spool.db"

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_r10b_physical_budget_under_held_reader(self):
        """Regression 1: physical budget <= 400000 breached under held reader."""
        spool = SQLiteSpool(
            self.db_path,
            max_physical_bytes=400000,
            max_pages=64,
            max_payload_bytes=10240,
            max_storage_bytes=400000,
            retention_sec=3600
        )
        spool.enqueue("init", "r", b"a" * 10011)
        
        # Hold a reader
        reader = sqlite3.connect(self.db_path)
        reader.execute("BEGIN DEFERRED")
        reader.execute("SELECT * FROM outbound_spool")

        peak = spool.get_physical_size()
        accepted = 0
        refused = 0
        for i in range(25):
            try:
                spool.enqueue(f"k{i}", "r", b"b" * 10011)
                accepted += 1
            except SpoolStorageLimitReached:
                refused += 1
            sz = spool.get_physical_size()
            if sz > peak:
                peak = sz

        reader.execute("ROLLBACK")
        reader.close()
        
        self.assertLessEqual(peak, 400000)
        self.assertGreater(accepted, 0)
        self.assertGreater(refused, 0)

    def test_r10b_100_escaped_messages_inbox(self):
        """Regression 2: 100-message permitted batch with escaped text rejected by 2 MiB ceiling."""
        # A single message with lots of backslashes expands to up to 16384*6 bytes
        from adapters.hub_outbound import C888BusClient
        import json
        import threading
        from http.server import BaseHTTPRequestHandler, HTTPServer
        
        # Create a payload of 100 valid messages, each ~16KB when decoded, but ~90KB when JSON escaped
        body_text = "\\" * 16000  # valid string
        messages = []
        for i in range(100):
            messages.append({
                "id": f"msg-{i}",
                "route": "some-route",
                "body": body_text,
                "created_at": 1234567890000,
                "expires_at": 1234567890000,
                "from_actor": "a",
                "to_actor": "b",
                "kind": "k"
            })
        encoded_response = json.dumps(messages).encode("utf-8")
        self.assertGreater(len(encoded_response), 2 * 1024 * 1024)
        
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(encoded_response)))
                self.end_headers()
                self.wfile.write(encoded_response)
            def log_message(self, format, *args): pass
        
        server = HTTPServer(("127.0.0.1", 0), Handler)
        port = server.server_port
        t = threading.Thread(target=server.serve_forever)
        t.daemon = True
        t.start()
        
        try:
            client = C888BusClient(f"http://127.0.0.1:{port}", allow_loopback_http=True)
            res = client.get_bus_inbox("actor", limit=100)
            self.assertEqual(len(res), 100)
            self.assertEqual(res[0]["body"], body_text)
        finally:
            server.shutdown()
            server.server_close()
            t.join()

    def test_r10b_watermark_empty_tombstones(self):
        """Regression 3: prune_tombstones watermarks oldest_tombstone_cutoff to curr_time on empty tombstones, causing freshly minted versioned keys to be rejected."""
        spool = SQLiteSpool(
            self.db_path,
            retention_sec=3600
        )
        import time
        from adapters.hub_outbound import make_versioned_key
        
        # Prune with empty tombstones
        now = time.time()
        spool.prune_tombstones(now=now)
        
        # Generate a fresh versioned key
        fresh_key = make_versioned_key("token", now=now)
        
        # It should be accepted
        res = spool.enqueue(fresh_key, "r", b"fresh", now=now)
        self.assertTrue(res)

class TestHttpLoopbackProducerContractR10b(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base_dir = Path(self.tmp.name)
        self.ws = self.base_dir / "test_workspace"
        self.ws.mkdir(parents=True, exist_ok=True)
        self.db_path = self.base_dir / "spool.db"

    def tearDown(self):
        self.tmp.cleanup()

    def test_native_producer_unique_mutation_with_lost_response(self):
        """Regression 4: true UUID producer fixture and actual server unique mutation count1.
        Newfixture MUSTstoreoriginalkey/payload/ID andcountmutationsindependently, 
        committhenlostresponse thenretryoriginalID/uniqueeffect1 plusdifferentpayloadsamekey409."""
        from adapters.hub_outbound import C888BusClient
        from http.server import BaseHTTPRequestHandler, HTTPServer
        import threading, json, time, uuid

        # A "server" that stores original key/payload/ID and counts mutations independently
        # It simulates a lost response on the first commit.
        state = {
            "mutations": 0,
            "stored": {},
            "requests_received": 0
        }

        class FakeHubServer(BaseHTTPRequestHandler):
            def do_POST(self):
                if self.path == "/api/bus/send":
                    content_length = int(self.headers.get("Content-Length", 0))
                    body = self.rfile.read(content_length).decode("utf-8")
                    req_data = json.loads(body)

                    state["requests_received"] += 1
                    key = req_data.get("idempotency_key")
                    payload = req_data.get("body")
                    
                    if key in state["stored"]:
                        # Retry
                        stored = state["stored"][key]
                        if stored["payload"] != payload:
                            self.send_response(409)
                            self.end_headers()
                            self.wfile.write(b'{"error": "Idempotency conflict"}')
                            return
                        else:
                            # Exact retry, return original ID
                            self.send_response(200)
                            self.end_headers()
                            self.wfile.write(json.dumps({
                                "id": stored["id"],
                                "status": "delivered",
                                "mutations": state["mutations"]
                            }).encode("utf-8"))
                            return
                    else:
                        # Initial commit
                        state["mutations"] += 1
                        msg_id = str(uuid.uuid4())
                        state["stored"][key] = {
                            "payload": payload,
                            "id": msg_id
                        }
                        
                        if state["requests_received"] == 1:
                            # Simulate lost response (close connection without HTTP response)
                            self.wfile.close()
                            return
                        else:
                            self.send_response(200)
                            self.end_headers()
                            self.wfile.write(json.dumps({
                                "id": msg_id,
                                "status": "delivered",
                                "mutations": state["mutations"]
                            }).encode("utf-8"))
                            return

            def log_message(self, format, *args): pass

        server = HTTPServer(("127.0.0.1", 0), FakeHubServer)
        port = server.server_port
        t = threading.Thread(target=server.serve_forever)
        t.daemon = True
        t.start()

        try:
            client = C888BusClient(f"http://127.0.0.1:{port}", allow_loopback_http=True)
            
            # Request 1: will fail with connection closed (lost response)
            key1 = f"v1:{time.time()}:key1"
            payload1 = "test_payload"
            try:
                client.send_bus_message("actorA", "actorB", "kindX", payload1, key1)
                self.fail("Expected WireContractError due to lost response")
            except WireContractError as e:
                # Expecting an error due to connection closed
                pass
                
            # Request 2: retry exact same ID, should succeed and return unique effect (mutations=1)
            res = client.send_bus_message("actorA", "actorB", "kindX", payload1, key1)
            self.assertEqual(state["mutations"], 1)
            self.assertEqual(state["requests_received"], 2)
            self.assertEqual(res["mutations"], 1)
            
            # Request 3: different payload, same key, should 409
            payload2 = "different_payload"
            try:
                client.send_bus_message("actorA", "actorB", "kindX", payload2, key1)
                self.fail('Expected 409')
            except IdempotencyConflictError:
                pass
            self.assertEqual(state["mutations"], 1)
            self.assertEqual(state["requests_received"], 3)
            
        finally:
            server.shutdown()
            server.server_close()
            t.join()



class IsolatedAplexerBridge(AplexerBridge):
    def __init__(self, *args, session_id=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.test_session_id = session_id
        
    def _run_cmd(self, args):
        import subprocess, os
        env = os.environ.copy()
        if self.state_root:
            env["APLEXER_STATE_DIR"] = str(self.state_root)
        if self.test_session_id:
            env["APLEXER_SESSION_ID"] = self.test_session_id
        elif "APLEXER_SESSION_ID" in env:
            del env["APLEXER_SESSION_ID"]
        return subprocess.run([self.aplexer_bin] + args, capture_output=True, text=True, env=env)

class TestGenuineNativeProducerContract(unittest.TestCase):
    def setUp(self):
        import tempfile
        from pathlib import Path
        self.tmp = tempfile.TemporaryDirectory()
        self.base_dir = Path(self.tmp.name)
        self.ws = self.base_dir / "workspace"
        self.ws.mkdir(parents=True, exist_ok=True)
        self.db_path = self.base_dir / "spool.db"

    def tearDown(self):
        self.tmp.cleanup()

    def test_native_producer_synthetic_discovery_and_routing(self):
        import os, stat, json, hashlib, uuid
        head_ws = str(self.ws)
        head_uuid = str(uuid.uuid4())
        native_mid = str(uuid.uuid4())
        
        state_dir = self.base_dir / "state_root"
        state_dir.mkdir(parents=True, exist_ok=True)
        fake_cli_path = self.base_dir / "fake_aplexer"

        cli_code = f"""#!/usr/bin/env python3
import sys, os, json, hashlib
from pathlib import Path

args = sys.argv[1:]
if not args: sys.exit(0)

if args[0] == "list":
    sys.stdout.write(json.dumps([{{
        "id": "{head_uuid}",
        "session_id": "{head_uuid}",
        "workspace": "{head_ws}",
        "tag": "agent-1",
        "reported_state": "idle"
    }}]))
    sys.exit(0)

if args[0] == "message" and len(args) > 1 and args[1] == "send":
    if "--from" in args:
        sys.stderr.write("error: --from cannot be used with cross-workspace --workspace delivery\\n")
        sys.exit(2)
    session_id = os.environ.get("APLEXER_SESSION_ID")
    if not session_id:
        sys.stderr.write("error: cross-workspace messaging requires an aplexer session identity\\n")
        sys.exit(1)
        
    sys.stdout.write(json.dumps({{"id": "{native_mid}", "status": "sent"}}))
    sys.exit(0)

sys.exit(0)
"""
        fake_cli_path.write_text(cli_code, encoding="utf-8")
        fake_cli_path.chmod(fake_cli_path.stat().st_mode | stat.S_IXUSR | stat.S_IRUSR)

        spool = SQLiteSpoolStorage(self.db_path) if "SQLiteSpoolStorage" in globals() else SQLiteSpool(self.db_path)
        bridge = IsolatedAplexerBridge(aplexer_bin=str(fake_cli_path), spool=spool, state_root=state_dir, session_id=head_uuid)
        
        # Sender discovery
        active_sessions = bridge.list_sessions() or []
        active_uuids = [s["uuid"] if "uuid" in s else s["id"] for s in active_sessions if s.get("workspace") == head_ws]
        self.assertIn(head_uuid, active_uuids, "Sender discovery must find the synthetic session by workspace")

        # Routing and Cursor tracking with HubOutboundIntegration
        integration = HubOutboundIntegration(
            spool=spool,
            bridge=bridge,
            state_root=state_dir,
            routes={"route/synthetic": {"workspace": head_ws, "tag": "agent-1", "consumer_uuid": head_uuid}}
        )

        inbound_msg = {
            "id": "hub-msg-999",
            "from_actor": "remote-actor",
            "to_actor": "agent-1",
            "body": "test dispatch"
        }
        
        ok = integration.on_inbound(inbound_msg, "route/synthetic")
        self.assertTrue(ok)
        mapping = spool.get_message_mapping("hub-msg-999")
        self.assertIsNotNone(mapping)
        self.assertEqual(mapping["status"], "delivered")

        raw_ws = head_ws.encode("utf-8")
        h = hashlib.sha256(raw_ws).hexdigest()[:32]
        ws_msg_dir = state_dir / "messages" / h
        ws_msg_dir.mkdir(parents=True, exist_ok=True)
        (ws_msg_dir / "workspace.json").write_text(json.dumps({"workspace": head_ws}), encoding="utf-8")
        cursors_dir = ws_msg_dir / "cursors"
        cursors_dir.mkdir(parents=True, exist_ok=True)
        (cursors_dir / f"{head_uuid}.json").write_text(
            json.dumps({"acked_through": native_mid, "exceptions": []}),
            encoding="utf-8",
        )
        
        integration.process_spool()
        mapping = spool.get_message_mapping("hub-msg-999")
        self.assertEqual(mapping["status"], "acked")

    def test_native_producer_negative_unbound_and_from(self):
        import stat, json, uuid
        head_ws = str(self.ws)
        
        state_dir = self.base_dir / "state_root"
        state_dir.mkdir(parents=True, exist_ok=True)
        fake_cli_path = self.base_dir / "fake_aplexer_neg"

        cli_code = f"""#!/usr/bin/env python3
import sys, os, json
args = sys.argv[1:]
if not args: sys.exit(0)

if args[0] == "list":
    sys.stdout.write(json.dumps([{{"id": "test-uuid", "workspace": "{head_ws}", "tag": "agent-1"}}]))
    sys.exit(0)

if args[0] == "message" and len(args) > 1 and args[1] == "send":
    if "--from" in args:
        sys.stderr.write("error: --from cannot be used with cross-workspace --workspace delivery\\n")
        sys.exit(2)
    session_id = os.environ.get("APLEXER_SESSION_ID")
    if not session_id:
        sys.stderr.write("error: cross-workspace messaging requires an aplexer session identity\\n")
        sys.exit(1)
sys.exit(0)
"""
        fake_cli_path.write_text(cli_code, encoding="utf-8")
        fake_cli_path.chmod(fake_cli_path.stat().st_mode | stat.S_IXUSR | stat.S_IRUSR)

        spool = SQLiteSpoolStorage(self.db_path) if "SQLiteSpoolStorage" in globals() else SQLiteSpool(self.db_path)
        bridge_unbound = IsolatedAplexerBridge(aplexer_bin=str(fake_cli_path), spool=spool, state_root=state_dir, session_id=None)
        
        # Test 1: unbound sender denial
        unbound_ok, amb, err = bridge_unbound.send_message(head_ws, "agent-1", {"text": "hello"})
        self.assertFalse(unbound_ok)
        self.assertIn("requires an aplexer session identity", err)

        # Test 2: --from rejection (invoked directly to test CLI guard)
        res_from = bridge_unbound._run_cmd(["message", "send", "--workspace", head_ws, "--from", "impostor", "--to", "agent-1", "--", "test"])
        self.assertEqual(res_from.returncode, 2)
        self.assertIn("--from cannot be used", res_from.stderr)

class TestNativeProducerTimeoutAndLostStdout(unittest.TestCase):
    def setUp(self):
        import tempfile
        from pathlib import Path
        self.tmp = tempfile.TemporaryDirectory()
        self.base_dir = Path(self.tmp.name)
        self.ws = self.base_dir / "workspace"
        self.ws.mkdir(parents=True, exist_ok=True)
        self.db_path = self.base_dir / "spool.db"

    def tearDown(self):
        self.tmp.cleanup()

    def test_timeout_and_lost_stdout_before_after_effect(self):
        import stat, json, uuid
        head_ws = str(self.ws)
        head_uuid = str(uuid.uuid4())
        native_mid = str(uuid.uuid4())

        state_dir = self.base_dir / "state_root"
        state_dir.mkdir(parents=True, exist_ok=True)
        fake_cli_path = self.base_dir / "fake_aplexer_timeout"

        control_file = self.base_dir / "control.json"

        cli_code = f"""#!/usr/bin/env python3
import sys, os, json, time

control_file = "{control_file}"
with open(control_file, "r") as f:
    ctrl = json.load(f)

args = sys.argv[1:]
if not args: sys.exit(0)

if args[0] == "list":
    sys.stdout.write(json.dumps([{{"id": "{head_uuid}", "workspace": "{head_ws}", "tag": "agent-1"}}]))
    sys.exit(0)

if args[0] == "message" and len(args) > 1 and args[1] == "send":
    if ctrl["mode"] == "timeout_before_effect":
        time.sleep(0.5)
        sys.exit(124) # timeout
    elif ctrl["mode"] == "exit1_after_effect":
        log_file = "{state_dir}/effect.log"
        with open(log_file, "a") as f:
            f.write(json.dumps({{"id": "{native_mid}", "tag": "agent-1", "data": {{"recipient": "agent-1", "idempotency_key": "exit1-key-1", "bridge_id": "exit1-key-1"}}, "body": "test exit1", "workspace": "{head_ws}"}}) + "\\n")
        sys.exit(1)
    elif ctrl["mode"] == "exit0_lost_stdout":
        log_file = "{state_dir}/effect.log"
        with open(log_file, "a") as f:
            f.write(json.dumps({{"id": "{native_mid}", "tag": "agent-1", "data": {{"recipient": "agent-1", "idempotency_key": "exit0-key-1", "bridge_id": "exit0-key-1"}}, "body": "test exit0", "workspace": "{head_ws}"}}) + "\\n")
        # Exit 0 but output nothing
        sys.exit(0)
    elif ctrl["mode"] == "exit0_non_uuid1":
        sys.stdout.write(json.dumps({{"id": "non-uuid-1234", "status": "sent"}}))
        sys.exit(0)
    elif ctrl["mode"] == "exit0_non_uuid2":
        sys.stdout.write(json.dumps({{"id": "native-mid-001", "status": "sent"}}))
        sys.exit(0)
    elif ctrl["mode"] == "success":
        sys.stdout.write(json.dumps({{"id": "{native_mid}", "status": "sent"}}))
        sys.exit(0)

if args[0] == "message" and len(args) > 1 and args[1] == "log":
    if ctrl["mode"] in ["exit1_after_effect", "exit0_lost_stdout", "success"]:
        log_file = "{state_dir}/effect.log"
        if os.path.exists(log_file):
            with open(log_file, "r") as f:
                logs = [json.loads(line) for line in f if line.strip()]
            sys.stdout.write(json.dumps(logs))
            sys.exit(0)
    sys.stdout.write("[]")
    sys.exit(0)
"""
        fake_cli_path.write_text(cli_code, encoding="utf-8")
        fake_cli_path.chmod(fake_cli_path.stat().st_mode | stat.S_IXUSR | stat.S_IRUSR)

        spool = SQLiteSpoolStorage(self.db_path) if "SQLiteSpoolStorage" in globals() else SQLiteSpool(self.db_path)
        bridge = IsolatedAplexerBridge(aplexer_bin=str(fake_cli_path), spool=spool, state_root=state_dir, session_id=head_uuid)

        # 1. Timeout before effect (no log)
        control_file.write_text(json.dumps({"mode": "timeout_before_effect"}))
        ok, amb, err = bridge.send_message(head_ws, "agent-1", {"text": "test timeout"}, idempotency_key="timeout-key-1")
        self.assertFalse(ok)
        self.assertTrue(amb, f"Timeout should result in ambiguous state. Err: {err}")
        intent = spool.get_intent("timeout-key-1")
        self.assertIsNotNone(intent)
        self.assertEqual(intent["status"], "ambiguous")

        # 2. Exit 1 after effect
        control_file.write_text(json.dumps({"mode": "exit1_after_effect"}))
        ok, amb, err = bridge.send_message(head_ws, "agent-1", {"text": "test exit1"}, idempotency_key="exit1-key-1")
        self.assertTrue(ok)
        self.assertFalse(amb)
        intent = spool.get_intent("exit1-key-1")
        self.assertEqual(intent["status"], "sent")

        # 3. Exit 0 but lost stdout
        control_file.write_text(json.dumps({"mode": "exit0_lost_stdout"}))
        ok, amb, err = bridge.send_message(head_ws, "agent-1", {"text": "test exit0"}, idempotency_key="exit0-key-1")
        self.assertTrue(ok)
        self.assertFalse(amb)
        intent = spool.get_intent("exit0-key-1")
        self.assertEqual(intent["status"], "sent")

        # 4. Ambiguous retry reconciliation (duplicate log entries)
        control_file.write_text(json.dumps({"mode": "exit0_lost_stdout"}))
        ok, amb, err = bridge.send_message(head_ws, "agent-1", {"text": "test exit0"}, idempotency_key="exit0-key-1")
        self.assertFalse(ok)
        self.assertTrue(amb)
        intent = spool.get_intent("exit0-key-1")
        self.assertEqual(intent["status"], "ambiguous")

        # 5. Non-UUID exit-0 stdout is ambiguous
        control_file.write_text(json.dumps({"mode": "exit0_non_uuid1"}))
        ok, amb, err = bridge.send_message(head_ws, "agent-1", {"text": "test non uuid1"}, idempotency_key="non-uuid1-key")
        self.assertFalse(ok)
        self.assertTrue(amb)
        
        control_file.write_text(json.dumps({"mode": "exit0_non_uuid2"}))
        ok, amb, err = bridge.send_message(head_ws, "agent-1", {"text": "test non uuid2"}, idempotency_key="non-uuid2-key")
        self.assertFalse(ok)
        self.assertTrue(amb)

if __name__ == "__main__":
    unittest.main()
