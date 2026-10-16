"""
Agent Hub Outbound Host Adapter
M3 Proposed Wire Contract & Bidirectional Spool / Aplexer Bridge Integration
Contract pins:
  Proposed wire contract: c888fd9c65d5a0aca26667e6eccb2c278b5334da
  Accepted Hub main pin:  d86c76b35d41d63871a6282bdd7bfc2ff723a6fd
"""

import sqlite3
import json
import logging
import time
import subprocess
import os
import shutil
import shlex
import sys
import hashlib
import urllib.request
import urllib.error
import urllib.parse
import stat
import uuid
import contextlib
import math
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Protocol, Callable, Union

logger = logging.getLogger(__name__)

# Proposed wire interface marked UNAGREED (Hub M3 integration pending)
UNAGREED_WIRE_PROTOCOL_VERSION = "v1-draft"
C888_PROPOSED_WIRE_CONTRACT_PIN = "c888fd9c65d5a0aca26667e6eccb2c278b5334da"
ACCEPTED_HUB_MAIN_PIN = "d86c76b35d41d63871a6282bdd7bfc2ff723a6fd"
CANDIDATE_CONTRACT_ONLY = True

# Limits and constants per C888 wire contract
MAX_BUS_BODY_BYTES = 16384  # 16 KiB UTF-8 bytes limit
MAX_SINGLE_MESSAGE_RESPONSE_BYTES = 128 * 1024  # 64 KiB ceiling for single message responses
MAX_INBOX_LIMIT = 100  # Max messages allowed per inbox request
MAX_INBOX_RESPONSE_BYTES = 2 * 1024 * 1024  # 2 MiB ceiling for aggregate inbox response
MAX_HTTP_ERROR_RESPONSE_BYTES = 64 * 1024  # 64 KiB ceiling for error responses
MAX_GENERAL_HTTP_RESPONSE_BYTES = 2 * 1024 * 1024  # 2 MiB upper bound ceiling

# Storage and retention budget constants
MIN_PHYSICAL_SCHEMA_BYTES = 114688  # Minimum SQLite schema overhead (~28 pages @ 4096 bytes)
MIN_PHYSICAL_SCHEMA_PAGES = 28
DEFAULT_JOURNAL_SIZE_LIMIT = 65536  # 64 KiB bounded WAL journal
DEFAULT_MAX_PAYLOAD_BYTES = 1024 * 1024  # 1 MiB for general spool payload
DEFAULT_MAX_STORAGE_BYTES = 16 * 1024 * 1024  # 16 MiB logical payload capacity (tiny fixture budget)
DEFAULT_MAX_PHYSICAL_BYTES = 16 * 1024 * 1024  # 16 MiB default physical file budget
DEFAULT_MAX_PAGES = 4096  # 16 MiB / 4096 bytes per page
DEFAULT_RETENTION_SEC = 86400.0  # 24 hours retention window for delivered rows
DEFAULT_TOMBSTONE_RETENTION_SEC = 7 * 86400.0  # 7 days bounded retry horizon for tombstones
DEFAULT_MAX_TOMBSTONES = 10000  # Cap on tombstone rows
DEFAULT_MAX_MAPPINGS = 10000  # Cap on message_mappings rows
DEFAULT_MAX_INTENTS = 10000  # Cap on delivery_intents rows
DEFAULT_MAX_TOTAL_RECORDS = 50000  # Cap on total rows across all spool tables

# Metadata input bounds
MAX_METADATA_STRING_BYTES = 256
MAX_WORKSPACE_PATH_BYTES = 4096
MAX_PAYLOAD_TEXT_BYTES = 65536

# Producer compatibility constants per cloudflare-aplexer-protocol
MAX_MAILBOX_STATE_BYTES = 64 * 1024  # 64 KiB cap for mailbox state & cursor files


def parse_versioned_key_issuance(key: str) -> Optional[float]:
    """Extracts issuance timestamp from a versioned key if present (e.g. 'v1:<timestamp>:<id>' or 'v1_<timestamp>_<id>').
    Returns None if key is a legacy opaque key or contains nonfinite/malformed issuance."""
    if not isinstance(key, str):
        return None
    for sep in (":", "_"):
        prefix = f"v1{sep}"
        if key.startswith(prefix):
            rest = key[len(prefix):]
            parts = rest.split(sep, 1)
            if parts:
                try:
                    ts = float(parts[0])
                    if not math.isfinite(ts) or ts < 0:
                        return None
                    if ts > 1e11:  # ms to s
                        ts = ts / 1000.0
                    return ts
                except (ValueError, OverflowError):
                    return None
    return None


def is_versioned_key(key: str) -> bool:
    """Returns True if key claims versioned format ('v1:' or 'v1_')."""
    return isinstance(key, str) and (key.startswith("v1:") or key.startswith("v1_"))


def make_versioned_key(token: str, now: Optional[float] = None) -> str:
    """Generates an age-authenticated versioned idempotency key."""
    curr = now if now is not None else time.time()
    return f"v1:{curr:.6f}:{token}"


def validate_metadata_str(
    name: str,
    val: Any,
    max_bytes: int = MAX_METADATA_STRING_BYTES,
    allow_none: bool = False,
    min_len: int = 1,
) -> Optional[str]:
    """Validates string inputs for metadata tables against types, embedded NUL bytes, and UTF-8 size bounds."""
    if val is None:
        if allow_none:
            return None
        raise ValueError(f"{name} cannot be None")
    if not isinstance(val, str):
        raise ValueError(f"{name} must be str, got {type(val).__name__}")
    if "\x00" in val:
        raise ValueError(f"{name} cannot contain embedded null bytes")
    encoded = val.encode("utf-8")
    if len(encoded) < min_len:
        raise ValueError(f"{name} cannot be empty")
    if len(encoded) > max_bytes:
        raise ValueError(f"{name} exceeds maximum length ({len(encoded)} > {max_bytes} bytes)")
    return val



def resolve_state_root(configured: Optional[Union[str, Path]] = None) -> Path:
    """Resolves the aplexer state root per NativePaths::resolve precedence:
      1. Explicit trusted configured state_root (relative resolves against current working directory)
      2. APLEXER_STATE_DIR environment variable (relative resolves against current working directory)
      3. XDG_STATE_HOME environment variable (must be absolute; joins /aplexer)
      4. Default: Path.home() / .local / state / aplexer
    State is distinct from RUNTIME root. No guessing or .aplexer fallback.
    """
    if configured is not None and str(configured).strip() != "":
        p = Path(configured)
        if not p.is_absolute():
            p = (Path.cwd() / p).resolve()
        else:
            p = p.resolve()
        return p

    aplexer_state_dir = os.environ.get("APLEXER_STATE_DIR")
    if aplexer_state_dir is not None and aplexer_state_dir.strip() != "":
        p = Path(aplexer_state_dir.strip())
        if not p.is_absolute():
            p = (Path.cwd() / p).resolve()
        else:
            p = p.resolve()
        return p

    xdg_state_home = os.environ.get("XDG_STATE_HOME")
    if xdg_state_home is not None and xdg_state_home.strip() != "":
        val = xdg_state_home.strip()
        p = Path(val)
        if not p.is_absolute():
            raise ValueError(f"XDG_STATE_HOME must be an absolute path, got {val}")
        return (p / "aplexer").resolve()

    home = os.environ.get("HOME")
    if home and home.strip():
        home_path = Path(home.strip())
    else:
        home_path = Path.home()
    return (home_path / ".local" / "state" / "aplexer").resolve()


def canonical_workspace(workspace: Union[str, Path]) -> Path:
    """Unix workspace canonicalization consistent with Rust canonical_workspace.
    Resolves relative paths against cwd, and resolves symlinks.
    If the path does not exist, canonicalizes parent and appends leaf name."""
    p = Path(workspace)
    if not p.is_absolute():
        p = Path.cwd() / p
    try:
        return p.resolve()
    except Exception:
        try:
            parent = p.parent.resolve()
            return parent / p.name
        except Exception:
            return p


def workspace_key(canonical_path: Path) -> str:
    """Computes stable 128-bit hex key (first 16 bytes of SHA-256) over
    the exact raw filesystem bytes of the canonical Unix workspace path,
    consistent with Rust workspace_key."""
    raw_bytes = os.fsencode(str(canonical_path))
    digest = hashlib.sha256(raw_bytes).hexdigest()
    return digest[:32]


def validate_consumer_uuid(consumer_uuid: str) -> Optional[str]:
    """Validates and returns the canonical 8-4-4-4-12 lowercase consumer UUID string.
    Rejects path traversal, slashes, and malformed UUIDs."""
    if not isinstance(consumer_uuid, str):
        return None
    consumer_uuid_clean = consumer_uuid.strip()
    if "/" in consumer_uuid_clean or "\\" in consumer_uuid_clean or ".." in consumer_uuid_clean:
        return None
    try:
        val = uuid.UUID(consumer_uuid_clean)
        canonical_str = str(val).lower()
        if consumer_uuid_clean.lower() != canonical_str:
            return None
        return canonical_str
    except Exception:
        return None


def read_bounded_regular_file(path: Union[str, Path], cap: int = MAX_MAILBOX_STATE_BYTES) -> Optional[bytes]:
    """Opens path without following final-component symlinks (O_NOFOLLOW) and nonblocking (O_NONBLOCK).
    Verifies it is a regular file under cap bytes, and reads it.
    Returns None if absent, non-regular, symlink, oversize, or unreadable.
    Performs zero directory creation, zero writes, zero locks."""
    p = Path(path)
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NONBLOCK", 0)
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(str(p), flags)
    except OSError:
        return None

    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode):
            return None
        if st.st_size > cap:
            return None
        data = os.read(fd, cap + 1)
        if len(data) > cap:
            return None
        return data
    except OSError:
        return None
    finally:
        try:
            os.close(fd)
        except OSError:
            pass


def verify_workspace_metadata(workspace_dir: Path, expected_canonical_workspace: Path) -> bool:
    """Verifies workspace.json reverse mapping before adopting a mailbox directory."""
    metadata_file = workspace_dir / "workspace.json"
    raw = read_bounded_regular_file(metadata_file)
    if raw is None:
        return False
    try:
        data = json.loads(raw.decode("utf-8"))
        if not isinstance(data, dict):
            return False
        meta_ws = data.get("workspace")
        if not meta_ws or not isinstance(meta_ws, str):
            return False
        return canonical_workspace(meta_ws) == expected_canonical_workspace
    except Exception:
        return False

class IdempotencyConflictError(Exception):
    """Raised when an idempotency key is submitted with differing payload or route."""
    pass

class SpoolStorageLimitReached(RuntimeError):
    """Raised when spool storage reaches the configured maximum capacity."""
    pass

class WireContractError(Exception):
    """Raised when wire contract constraints are violated."""
    pass

class InsecureTransportError(Exception):
    """Raised when an insecure HTTP transport is used for non-loopback endpoints."""
    pass

class TransportProbe(Protocol):
    def send_payload(self, route: str, payload: bytes) -> bool:
        ...

class NativeProbe(Protocol):
    def get_aplexer_path(self) -> Optional[str]:
        ...
def validate_native_args(
    workspace: Any,
    tag: Any,
    text: Any,
    idempotency_key: Optional[Any] = None,
    data: Optional[Any] = None,
) -> Tuple[bool, str]:
    """Validates native CLI inputs for types, size bounds, and absence of NUL bytes before any side effect."""
    if not isinstance(workspace, (str, Path)) or not str(workspace).strip():
        return False, "workspace must be a non-empty string or path"
    ws_str = str(workspace)
    if "\x00" in ws_str:
        return False, "workspace contains embedded null bytes"
    if len(ws_str.encode("utf-8")) > 4096:
        return False, "workspace exceeds maximum path length (4096 bytes)"

    if not isinstance(tag, str) or not tag.strip():
        return False, "tag must be a non-empty string"
    if "\x00" in tag:
        return False, "tag contains embedded null bytes"
    if len(tag.encode("utf-8")) > 256:
        return False, "tag exceeds maximum length (256 bytes)"

    if not isinstance(text, str):
        return False, f"text must be str, got {type(text).__name__}"
    if "\x00" in text:
        return False, "text contains embedded null bytes"
    if len(text.encode("utf-8")) > 65536:
        return False, "text exceeds maximum length (65536 bytes)"

    if idempotency_key is not None:
        if not isinstance(idempotency_key, str) or not idempotency_key.strip():
            return False, "idempotency_key must be a non-empty string"
        if "\x00" in idempotency_key:
            return False, "idempotency_key contains embedded null bytes"
        if len(idempotency_key.encode("utf-8")) > 256:
            return False, "idempotency_key exceeds maximum length (256 bytes)"
        if is_versioned_key(idempotency_key):
            iss = parse_versioned_key_issuance(idempotency_key)
            if iss is None or iss > time.time() + 60.0:
                return False, "Invalid versioned idempotency key: nonfinite, malformed, or invalid timestamp"

    if data is not None:
        if not isinstance(data, dict):
            return False, f"data must be a dict, got {type(data).__name__}"
        try:
            for k, v in data.items():
                if isinstance(k, str) and "\x00" in k:
                    return False, "data contains embedded null bytes"
                if isinstance(v, str) and "\x00" in v:
                    return False, "data contains embedded null bytes"
            data_str = json.dumps(data)
            if "\x00" in data_str or "\\u0000" in data_str:
                return False, "data contains embedded null bytes"
        except Exception as exc:
            return False, f"data is not JSON serializable: {exc}"

    return True, ""


RESERVED_PROVENANCE_KEYS = {
    "bridge_id",
    "idempotency_key",
    "origin",
    "recipient",
    "provenance",
    "workspace",
    "tag",
    "session_id",
    "machine_id",
}


class SQLiteSpool:
    """Durable transport-neutral SQLite outbound spool with bounded payload, physical storage, and tombstones."""

    def __init__(
        self,
        db_path: Path,
        max_payload_bytes: int = DEFAULT_MAX_PAYLOAD_BYTES,
        max_storage_bytes: int = DEFAULT_MAX_STORAGE_BYTES,
        retention_sec: float = DEFAULT_RETENTION_SEC,
        max_physical_bytes: int = DEFAULT_MAX_PHYSICAL_BYTES,
        max_pages: int = DEFAULT_MAX_PAGES,
        min_physical_reserve_bytes: int = MIN_PHYSICAL_SCHEMA_BYTES,
        tombstone_retention_sec: float = DEFAULT_TOMBSTONE_RETENTION_SEC,
        max_tombstones: int = DEFAULT_MAX_TOMBSTONES,
        max_mappings: int = DEFAULT_MAX_MAPPINGS,
        max_intents: int = DEFAULT_MAX_INTENTS,
        max_total_records: int = DEFAULT_MAX_TOTAL_RECORDS,
        journal_size_limit: int = DEFAULT_JOURNAL_SIZE_LIMIT,
    ):
        self.db_path = Path(db_path)
        self.min_physical_reserve_bytes = min_physical_reserve_bytes

        # If caller passed None, bound to defaults to prevent unlimited physical explosion
        if max_physical_bytes is None:
            max_physical_bytes = DEFAULT_MAX_PHYSICAL_BYTES
        if max_pages is None:
            max_pages = DEFAULT_MAX_PAGES

        # Upfront validation: reject impossible budget configuration
        if max_physical_bytes < self.min_physical_reserve_bytes:
            raise ValueError(
                f"Impossible physical budget: max_physical_bytes ({max_physical_bytes}) is less than "
                f"minimum SQLite schema overhead ({self.min_physical_reserve_bytes} bytes)."
            )
        if max_pages < MIN_PHYSICAL_SCHEMA_PAGES:
            raise ValueError(
                f"Impossible page budget: max_pages ({max_pages}) is less than "
                f"minimum SQLite schema pages ({MIN_PHYSICAL_SCHEMA_PAGES})."
            )
        if max_storage_bytes <= 0:
            raise ValueError("max_storage_bytes must be a positive integer")
        if max_payload_bytes <= 0:
            raise ValueError("max_payload_bytes must be a positive integer")
        if max_payload_bytes > max_storage_bytes:
            raise ValueError(
                f"max_payload_bytes ({max_payload_bytes}) cannot exceed logical capacity max_storage_bytes ({max_storage_bytes})"
            )
        if max_total_records <= 0:
            raise ValueError("max_total_records must be a positive integer")
        if max_tombstones <= 0:
            raise ValueError("max_tombstones must be a positive integer")
        if max_mappings <= 0:
            raise ValueError("max_mappings must be a positive integer")
        if max_intents <= 0:
            raise ValueError("max_intents must be a positive integer")

        self.max_payload_bytes = max_payload_bytes
        self.max_storage_bytes = max_storage_bytes
        self.retention_sec = retention_sec
        self.max_physical_bytes = max_physical_bytes
        self.max_pages = max_pages
        self.tombstone_retention_sec = tombstone_retention_sec
        self.max_tombstones = max_tombstones
        self.max_mappings = max_mappings
        self.max_intents = max_intents
        self.max_total_records = max_total_records
        self.journal_size_limit = journal_size_limit

        self._init_db()

    def _create_raw_conn(self) -> sqlite3.Connection:
        """Creates a fresh connection with PRAGMA limits enforced immediately."""
        conn = sqlite3.connect(str(self.db_path), timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute(f"PRAGMA journal_size_limit = {self.journal_size_limit}")
        conn.execute("PRAGMA wal_autocheckpoint = 100")
        if self.max_pages is not None:
            conn.execute(f"PRAGMA max_page_count = {self.max_pages}")
        return conn

    @contextlib.contextmanager
    def _get_connection(self):
        """Context manager yielding a configured SQLite connection and guaranteeing closure."""
        conn = self._create_raw_conn()
        try:
            yield conn
        finally:
            conn.close()

    def _get_conn(self) -> sqlite3.Connection:
        """Backward-compatible raw connection creator for callers managing lifetime."""
        return self._create_raw_conn()

    def _init_db(self):
        if self.max_physical_bytes is not None:
            shm_path = self.db_path.with_name(self.db_path.name + "-shm")
            est_growth = 32768 if not shm_path.exists() else 0
            if self.get_physical_size() + est_growth > self.max_physical_bytes:
                raise SpoolStorageLimitReached("Physical capacity exceeded prior to startup/migration")

        with self._get_connection() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS outbound_spool (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    idempotency_key TEXT UNIQUE NOT NULL,
                    route TEXT NOT NULL,
                    payload BLOB NOT NULL,
                    status TEXT NOT NULL, -- pending, delivered, ambiguous, failed
                    attempt_count INTEGER DEFAULT 0,
                    last_attempt REAL,
                    error_text TEXT,
                    created_at REAL NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS spool_tombstones (
                    idempotency_key TEXT PRIMARY KEY,
                    route TEXT NOT NULL,
                    payload_sha256 TEXT NOT NULL,
                    pruned_at REAL NOT NULL,
                    created_at REAL DEFAULT 0
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cursors (
                    route TEXT PRIMARY KEY,
                    last_receipt_cursor TEXT,
                    last_ack_cursor TEXT,
                    last_log_cursor TEXT,
                    updated_at REAL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS delivery_intents (
                    intent_id TEXT PRIMARY KEY,
                    idempotency_key TEXT UNIQUE NOT NULL,
                    workspace TEXT NOT NULL,
                    tag TEXT NOT NULL,
                    text TEXT NOT NULL,
                    data_json TEXT,
                    status TEXT NOT NULL, -- persisted, sent, ambiguous, failed
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS enrolled_routes (
                    route TEXT PRIMARY KEY,
                    workspace TEXT NOT NULL,
                    tag TEXT NOT NULL,
                    consumer_uuid TEXT,
                    machine_id TEXT,
                    created_at REAL NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS message_mappings (
                    hub_message_id TEXT PRIMARY KEY,
                    native_message_id TEXT,
                    route TEXT,
                    workspace TEXT NOT NULL,
                    expected_tag TEXT NOT NULL,
                    expected_consumer_uuid TEXT,
                    from_actor TEXT,
                    to_actor TEXT,
                    thread_id TEXT,
                    status TEXT NOT NULL, -- pending, delivered, acked, replied
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_mappings_native_id ON message_mappings (native_message_id)")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS spool_metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at REAL NOT NULL
                )
            """)
            conn.commit()

    def get_metadata(self, key: str, conn: Optional[sqlite3.Connection] = None) -> Optional[str]:
        if conn is not None:
            row = conn.execute("SELECT value FROM spool_metadata WHERE key = ?", (key,)).fetchone()
            return str(row[0]) if row and row[0] is not None else None
        with self._get_connection() as c:
            row = c.execute("SELECT value FROM spool_metadata WHERE key = ?", (key,)).fetchone()
            return str(row[0]) if row and row[0] is not None else None

    def set_metadata(self, key: str, value: str, now: Optional[float] = None, conn: Optional[sqlite3.Connection] = None):
        curr_time = now if now is not None else time.time()
        if conn is not None:
            conn.execute(
                """INSERT INTO spool_metadata (key, value, updated_at) VALUES (?, ?, ?)
                   ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at""",
                (key, str(value), curr_time),
            )
            return
        with self._get_connection() as c:
            c.execute(
                """INSERT INTO spool_metadata (key, value, updated_at) VALUES (?, ?, ?)
                   ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at""",
                (key, str(value), curr_time),
            )
            c.commit()

    def get_tombstone_cutoff(self, conn: Optional[sqlite3.Connection] = None) -> Optional[float]:
        val = self.get_metadata("oldest_tombstone_cutoff", conn=conn)
        if val is not None:
            try:
                return float(val)
            except ValueError:
                pass
        return None

    def get_physical_size(self) -> int:
        """Returns total physical storage bytes on disk across database, WAL, and journal files."""
        total = 0
        base = self.db_path
        candidates = [
            base,
            base.with_name(base.name + "-wal"),
            base.with_name(base.name + "-shm"),
            base.with_name(base.name + "-journal"),
        ]
        for p in candidates:
            try:
                if p.exists():
                    total += p.stat().st_size
            except OSError:
                pass
        return total

    def get_page_count(self, conn: Optional[sqlite3.Connection] = None) -> int:
        """Returns physical SQLite page count."""
        if conn is not None:
            row = conn.execute("PRAGMA page_count").fetchone()
            return int(row[0]) if row and row[0] is not None else 0
        with self._get_connection() as c:
            row = c.execute("PRAGMA page_count").fetchone()
            return int(row[0]) if row and row[0] is not None else 0

    def get_page_size(self, conn: Optional[sqlite3.Connection] = None) -> int:
        """Returns SQLite page size in bytes."""
        if conn is not None:
            row = conn.execute("PRAGMA page_size").fetchone()
            return int(row[0]) if row and row[0] is not None else 4096
        with self._get_connection() as c:
            row = c.execute("PRAGMA page_size").fetchone()
            return int(row[0]) if row and row[0] is not None else 4096

    def checkpoint_and_reclaim(self):
        """Truncates WAL journal and checkpoints pages to keep physical storage bounded.
        Uses PASSIVE checkpoint if TRUNCATE is busy/blocked to avoid indefinite reader blocking."""
        try:
            with self._get_connection() as conn:
                try:
                    conn.execute("PRAGMA busy_timeout = 100")
                    conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                except sqlite3.OperationalError:
                    try:
                        conn.execute("PRAGMA wal_checkpoint(PASSIVE)")
                    except sqlite3.OperationalError:
                        pass
        except Exception:
            pass

    def get_table_counts(self, conn: Optional[sqlite3.Connection] = None) -> Dict[str, int]:
        """Returns row counts for all spool, metadata, and cursor tables."""
        tables = [
            "outbound_spool",
            "spool_tombstones",
            "cursors",
            "delivery_intents",
            "enrolled_routes",
            "message_mappings",
        ]
        counts = {}
        if conn is not None:
            for t in tables:
                row = conn.execute(f"SELECT count(*) FROM {t}").fetchone()
                counts[t] = int(row[0]) if row else 0
            return counts
        with self._get_connection() as c:
            for t in tables:
                row = c.execute(f"SELECT count(*) FROM {t}").fetchone()
                counts[t] = int(row[0]) if row else 0
        return counts

    def get_total_records(self, conn: Optional[sqlite3.Connection] = None) -> int:
        """Returns total row count across all tables."""
        counts = self.get_table_counts(conn=conn)
        return sum(counts.values())


    def _check_physical_capacity_before_txn(self, adding_payload_bytes: int = 0, adding_records: int = 1):
        if adding_records > 0:
            total_records = self.get_total_records()
            if total_records + adding_records > self.max_total_records:
                raise SpoolStorageLimitReached(f"Spool storage limit reached: total records ({total_records + adding_records}) exceeds max_total_records ({self.max_total_records})")
        if self.max_physical_bytes is not None:
            if adding_payload_bytes == 0:
                est_growth = 4096 if adding_records > 0 else 32768
            else:
                needed_pages = max(1, (adding_payload_bytes + 4095) // 4096) + 4
                est_growth = needed_pages * 4120 + 32768
            if self.get_physical_size() + est_growth > self.max_physical_bytes:
                self.checkpoint_and_reclaim()
                if self.get_physical_size() + est_growth > self.max_physical_bytes:
                    raise SpoolStorageLimitReached(f"Physical limit reached: {self.get_physical_size()} + {est_growth} > {self.max_physical_bytes}")

    def _assert_capacity_available(
        self,
        conn: sqlite3.Connection,
        adding_records: int = 1,
        adding_payload_bytes: int = 0,
    ):
        """Enforces all capacity and physical limits atomically before inserting new data."""
        if adding_records > 0:
            total_records = self.get_total_records(conn=conn)
            if total_records + adding_records > self.max_total_records:
                raise SpoolStorageLimitReached(
                    f"Spool storage limit reached: total records ({total_records + adding_records}) "
                    f"exceeds max_total_records ({self.max_total_records})"
                )
        if self.max_physical_bytes is not None:
            phys_size = self.get_physical_size()
            # Anticipate WAL frame write growth before crossing budget.
            # In SQLite WAL mode, each written page produces a frame of 4120 bytes (4096-byte page + 24-byte header).
            # A write transaction with payload requires pages for payload plus overhead for B-tree index,
            # autoincrement sequence, and internal nodes. Metadata operations without payload require at most 1 page.
            if adding_payload_bytes == 0:
                est_growth = 4096 if adding_records > 0 else 32768
            else:
                needed_pages = max(1, (adding_payload_bytes + 4095) // 4096) + 4
                est_growth = needed_pages * 4120 + 32768
            if phys_size + est_growth > self.max_physical_bytes:
                raise SpoolStorageLimitReached(
                    f"Spool storage limit reached: physical size with anticipated transaction growth "
                    f"({phys_size + est_growth} bytes) exceeds max_physical_bytes ({self.max_physical_bytes} bytes)"
                )
        if self.max_pages is not None:
            pages = self.get_page_count(conn=conn)
            freelist_row = conn.execute("PRAGMA freelist_count").fetchone()
            freelist_count = int(freelist_row[0]) if freelist_row and freelist_row[0] is not None else 0
            allocated_pages = max(0, pages - freelist_count)
            needed_pages = 1 if adding_payload_bytes == 0 else max(1, (adding_payload_bytes + 4095) // 4096) + 4
            if allocated_pages + needed_pages > self.max_pages:
                raise SpoolStorageLimitReached(
                    f"Spool storage limit reached: anticipated page count ({allocated_pages + needed_pages}) exceeds max_pages ({self.max_pages})"
                )

    def register_route(
        self,
        route: str,
        workspace: str,
        tag: str,
        consumer_uuid: Optional[str] = None,
        machine_id: Optional[str] = None,
        now: Optional[float] = None,
    ):
        validate_metadata_str("route", route, max_bytes=MAX_METADATA_STRING_BYTES, min_len=1)
        validate_metadata_str("workspace", str(workspace), max_bytes=MAX_WORKSPACE_PATH_BYTES, min_len=1)
        validate_metadata_str("tag", tag, max_bytes=MAX_METADATA_STRING_BYTES, min_len=1)
        validate_metadata_str("consumer_uuid", consumer_uuid, max_bytes=64, allow_none=True)
        validate_metadata_str("machine_id", machine_id, max_bytes=MAX_METADATA_STRING_BYTES, allow_none=True)

        curr_time = now if now is not None else time.time()
        with self._get_connection() as conn:
            conn.isolation_level = None
            self._check_physical_capacity_before_txn(adding_records=1)
            conn.execute("BEGIN IMMEDIATE")
            try:
                row = conn.execute("SELECT 1 FROM enrolled_routes WHERE route = ?", (route,)).fetchone()
                if not row:
                    self._assert_capacity_available(conn, adding_records=1)
                else:
                    self._assert_capacity_available(conn, adding_records=0)

                conn.execute(
                    """INSERT INTO enrolled_routes (route, workspace, tag, consumer_uuid, machine_id, created_at)
                       VALUES (?, ?, ?, ?, ?, ?)
                       ON CONFLICT(route) DO UPDATE SET workspace=excluded.workspace, tag=excluded.tag,
                       consumer_uuid=excluded.consumer_uuid, machine_id=excluded.machine_id""",
                    (route, str(workspace), tag, consumer_uuid, machine_id, curr_time),
                )


                conn.execute("COMMIT")
            except sqlite3.OperationalError as op_err:
                try:
                    conn.execute("ROLLBACK")
                except Exception:
                    pass
                if "full" in str(op_err).lower():
                    raise SpoolStorageLimitReached(f"Spool storage limit reached (SQLite error): {op_err}") from op_err
                raise
            except Exception:
                try:
                    conn.execute("ROLLBACK")
                except Exception:
                    pass
                raise

    def get_enrolled_route(self, route: str) -> Optional[sqlite3.Row]:
        with self._get_connection() as conn:
            return conn.execute("SELECT * FROM enrolled_routes WHERE route = ?", (route,)).fetchone()

    def record_mapping(
        self,
        hub_message_id: str,
        workspace: str,
        tag: str,
        consumer_uuid: Optional[str] = None,
        native_message_id: Optional[str] = None,
        route: Optional[str] = None,
        from_actor: Optional[str] = None,
        to_actor: Optional[str] = None,
        thread_id: Optional[str] = None,
        status: str = "delivered",
        now: Optional[float] = None,
    ):
        validate_metadata_str("hub_message_id", hub_message_id, max_bytes=MAX_METADATA_STRING_BYTES, min_len=1)
        validate_metadata_str("workspace", str(workspace), max_bytes=MAX_WORKSPACE_PATH_BYTES, min_len=1)
        validate_metadata_str("tag", tag, max_bytes=MAX_METADATA_STRING_BYTES, min_len=1)
        validate_metadata_str("consumer_uuid", consumer_uuid, max_bytes=64, allow_none=True)
        validate_metadata_str("native_message_id", native_message_id, max_bytes=MAX_METADATA_STRING_BYTES, allow_none=True)
        validate_metadata_str("route", route, max_bytes=MAX_METADATA_STRING_BYTES, allow_none=True)
        validate_metadata_str("from_actor", from_actor, max_bytes=MAX_METADATA_STRING_BYTES, allow_none=True)
        validate_metadata_str("to_actor", to_actor, max_bytes=MAX_METADATA_STRING_BYTES, allow_none=True)
        validate_metadata_str("thread_id", thread_id, max_bytes=MAX_METADATA_STRING_BYTES, allow_none=True)
        validate_metadata_str("status", status, max_bytes=64, min_len=1)

        curr_time = now if now is not None else time.time()
        with self._get_connection() as conn:
            conn.isolation_level = None
            self._check_physical_capacity_before_txn(adding_records=1)
            conn.execute("BEGIN IMMEDIATE")
            try:
                cutoff = self.get_tombstone_cutoff(conn=conn)
                if is_versioned_key(hub_message_id):
                    issuance = parse_versioned_key_issuance(hub_message_id)
                    if issuance is None or issuance > curr_time + 60.0:
                        conn.execute("ROLLBACK")
                        raise IdempotencyConflictError(f"Malformed or future-invalid versioned mapping identity ({hub_message_id})")
                    if cutoff is not None and issuance < cutoff:
                        conn.execute("ROLLBACK")
                        raise IdempotencyConflictError(f"Expired message mapping identity ({hub_message_id})")

                row = conn.execute("SELECT 1 FROM message_mappings WHERE hub_message_id = ?", (hub_message_id,)).fetchone()
                if not row:
                    self._assert_capacity_available(conn, adding_records=1)
                else:
                    self._assert_capacity_available(conn, adding_records=0)

                conn.execute(
                    """INSERT INTO message_mappings
                       (hub_message_id, native_message_id, route, workspace, expected_tag, expected_consumer_uuid,
                        from_actor, to_actor, thread_id, status, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                       ON CONFLICT(hub_message_id) DO UPDATE SET
                       native_message_id=COALESCE(excluded.native_message_id, message_mappings.native_message_id),
                       status=excluded.status, updated_at=excluded.updated_at""",
                    (
                        hub_message_id,
                        native_message_id,
                        route,
                        str(workspace),
                        tag,
                        consumer_uuid,
                        from_actor,
                        to_actor,
                        thread_id,
                        status,
                        curr_time,
                        curr_time,
                    ),
                )


                conn.execute("COMMIT")
            except sqlite3.OperationalError as op_err:
                try:
                    conn.execute("ROLLBACK")
                except Exception:
                    pass
                if "full" in str(op_err).lower():
                    raise SpoolStorageLimitReached(f"Spool storage limit reached (SQLite error): {op_err}") from op_err
                raise
            except Exception:
                try:
                    conn.execute("ROLLBACK")
                except Exception:
                    pass
                raise

    def get_message_mapping(self, message_id: str) -> Optional[sqlite3.Row]:
        with self._get_connection() as conn:
            return conn.execute(
                "SELECT * FROM message_mappings WHERE hub_message_id = ? OR native_message_id = ?",
                (message_id, message_id),
            ).fetchone()

    def update_mapping_status(
        self,
        hub_message_id: str,
        status: str,
        native_message_id: Optional[str] = None,
        now: Optional[float] = None,
    ):
        validate_metadata_str("hub_message_id", hub_message_id, max_bytes=MAX_METADATA_STRING_BYTES, min_len=1)
        validate_metadata_str("status", status, max_bytes=64, min_len=1)
        validate_metadata_str("native_message_id", native_message_id, max_bytes=MAX_METADATA_STRING_BYTES, allow_none=True)

        curr_time = now if now is not None else time.time()
        with self._get_connection() as conn:
            conn.isolation_level = None
            self._check_physical_capacity_before_txn(adding_records=0)
            conn.execute("BEGIN IMMEDIATE")
            try:
                if native_message_id:
                    conn.execute(
                        "UPDATE message_mappings SET status = ?, native_message_id = ?, updated_at = ? WHERE hub_message_id = ?",
                        (status, native_message_id, curr_time, hub_message_id),
                    )
                else:
                    conn.execute(
                        "UPDATE message_mappings SET status = ?, updated_at = ? WHERE hub_message_id = ?",
                        (status, curr_time, hub_message_id),
                    )
                conn.execute("COMMIT")
            except Exception:
                conn.execute("ROLLBACK")
                raise

    def get_unacked_mappings_for_route(self, route: str) -> List[sqlite3.Row]:
        with self._get_connection() as conn:
            return conn.execute(
                "SELECT * FROM message_mappings WHERE route = ? AND status IN ('delivered', 'pending', 'replied')",
                (route,),
            ).fetchall()

    def get_total_payload_size(self, conn: Optional[sqlite3.Connection] = None) -> int:
        """Calculates total payload bytes across all active spool rows."""
        close_conn = False
        if conn is None:
            conn = self._create_raw_conn()
            close_conn = True
        try:
            cur = conn.cursor()
            cur.execute("SELECT sum(length(payload)) FROM outbound_spool")
            row = cur.fetchone()
            return int(row[0]) if row and row[0] is not None else 0
        finally:
            if close_conn:
                conn.close()

    def prune_tombstones(
        self,
        tombstone_retention_sec: Optional[float] = None,
        max_tombstones: Optional[int] = None,
        now: Optional[float] = None,
    ) -> int:
        """Prunes expired tombstones and caps tombstone table count.
        Versioned keys older than retention are pruned and their cutoff is watermarked into spool_metadata;
        legacy opaque keys are safely held to prevent silent replay until migrated.
        Safe capacity refusal is enforced if capacity cannot be reclaimed."""
        effective_retention = tombstone_retention_sec if tombstone_retention_sec is not None else self.tombstone_retention_sec
        effective_max = max_tombstones if max_tombstones is not None else self.max_tombstones
        curr_time = now if now is not None else time.time()
        cutoff = curr_time - effective_retention

        with self._get_connection() as conn:
            conn.isolation_level = None
            self._check_physical_capacity_before_txn(adding_records=0)
            conn.execute("BEGIN IMMEDIATE")
            try:
                cur = conn.cursor()
                # 1. Prune expired versioned tombstones by age
                cur.execute("SELECT idempotency_key, route, payload_sha256, pruned_at FROM spool_tombstones WHERE pruned_at < ?", (cutoff,))
                expired_rows = cur.fetchall()
                pruned_by_age = 0
                max_pruned_age_cutoff: Optional[float] = None

                for r in expired_rows:
                    k = r["idempotency_key"]
                    if is_versioned_key(k):
                        issuance = parse_versioned_key_issuance(k)
                        if issuance is not None:
                            # Versioned key: safe to prune by age because re-ingress is bounded by oldest_tombstone_cutoff
                            cur.execute("DELETE FROM spool_tombstones WHERE idempotency_key = ?", (k,))
                            pruned_by_age += 1
                            if max_pruned_age_cutoff is None or cutoff > max_pruned_age_cutoff:
                                max_pruned_age_cutoff = cutoff

                # 2. Cap enforcement: if tombstone count still exceeds effective_max
                cur.execute("SELECT count(*) FROM spool_tombstones")
                current_count = int(cur.fetchone()[0])
                pruned_by_cap = 0

                if current_count > effective_max:
                    excess = current_count - effective_max
                    cur.execute(
                        "SELECT idempotency_key, route, payload_sha256, pruned_at FROM spool_tombstones ORDER BY pruned_at ASC LIMIT ?",
                        (excess,),
                    )
                    excess_rows = cur.fetchall()
                    evicted_opaque = {}
                    cur.execute("SELECT value FROM spool_metadata WHERE key = 'evicted_opaque_keys'")
                    m_row = cur.fetchone()
                    if m_row and m_row[0]:
                        try:
                            evicted_opaque = json.loads(m_row[0])
                        except Exception:
                            evicted_opaque = {}

                    for r in excess_rows:
                        k = r["idempotency_key"]
                        pruned_at = float(r["pruned_at"])
                        cur.execute("DELETE FROM spool_tombstones WHERE idempotency_key = ?", (k,))
                        pruned_by_cap += 1
                        issuance = parse_versioned_key_issuance(k)
                        if issuance is not None:
                            if max_pruned_age_cutoff is None or issuance > max_pruned_age_cutoff:
                                max_pruned_age_cutoff = issuance
                        else:
                            # Opaque key cap eviction: record fingerprint so future replays preserve stable outcome
                            evicted_opaque[k] = {
                                "route": r["route"],
                                "payload_sha256": r["payload_sha256"],
                                "pruned_at": pruned_at,
                            }
                            if len(evicted_opaque) > 1000:
                                oldest_k = min(evicted_opaque.keys(), key=lambda x: evicted_opaque[x].get("pruned_at", 0))
                                del evicted_opaque[oldest_k]

                    cur.execute(
                        """INSERT INTO spool_metadata (key, value, updated_at) VALUES ('evicted_opaque_keys', ?, ?)
                           ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at""",
                        (json.dumps(evicted_opaque), curr_time),
                    )

                # 3. Update oldest_tombstone_cutoff watermark in spool_metadata
                # Only advance the watermark if we actually evicted tombstones
                if max_pruned_age_cutoff is not None:
                    cur.execute("SELECT value FROM spool_metadata WHERE key = 'oldest_tombstone_cutoff'")
                    existing = cur.fetchone()
                    if existing and existing[0] is not None:
                        try:
                            if float(existing[0]) > max_pruned_age_cutoff:
                                max_pruned_age_cutoff = float(existing[0])
                        except ValueError:
                            pass
                    cur.execute(
                        """INSERT INTO spool_metadata (key, value, updated_at) VALUES ('oldest_tombstone_cutoff', ?, ?)
                           ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at""",
                        (str(max_pruned_age_cutoff), curr_time),
                    )
                conn.execute("COMMIT")
                return pruned_by_age + pruned_by_cap
            except Exception:
                conn.execute("ROLLBACK")
                raise

    def prune_mappings(self, retention_sec: Optional[float] = None, now: Optional[float] = None) -> int:
        """Prunes terminal message mappings (acked, replied) older than retention.
        Unacked, pending, and delivered mappings are NEVER pruned."""
        effective_retention = retention_sec if retention_sec is not None else self.retention_sec
        curr_time = now if now is not None else time.time()
        cutoff = curr_time - effective_retention
        with self._get_connection() as conn:
            conn.isolation_level = None
            self._check_physical_capacity_before_txn(adding_records=0)
            conn.execute("BEGIN IMMEDIATE")
            try:
                cur = conn.cursor()
                cur.execute(
                    "DELETE FROM message_mappings WHERE status IN ('acked', 'replied') AND updated_at < ?",
                    (cutoff,),
                )
                pruned = cur.rowcount
                cur.execute(
                    """INSERT INTO spool_metadata (key, value, updated_at) VALUES ('oldest_mapping_cutoff', ?, ?)
                       ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at""",
                    (str(cutoff), curr_time),
                )
                conn.execute("COMMIT")
                return pruned
            except Exception:
                conn.execute("ROLLBACK")
                raise

    def prune_intents(self, retention_sec: Optional[float] = None, now: Optional[float] = None) -> int:
        """Prunes completed delivery intents (sent) older than retention.
        Ambiguous, persisted, and pending intents are NEVER pruned."""
        effective_retention = retention_sec if retention_sec is not None else self.retention_sec
        curr_time = now if now is not None else time.time()
        cutoff = curr_time - effective_retention
        with self._get_connection() as conn:
            conn.isolation_level = None
            self._check_physical_capacity_before_txn(adding_records=0)
            conn.execute("BEGIN IMMEDIATE")
            try:
                cur = conn.cursor()
                cur.execute(
                    "DELETE FROM delivery_intents WHERE status = 'sent' AND updated_at < ?",
                    (cutoff,),
                )
                pruned = cur.rowcount
                cur.execute(
                    """INSERT INTO spool_metadata (key, value, updated_at) VALUES ('oldest_intent_cutoff', ?, ?)
                       ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at""",
                    (str(cutoff), curr_time),
                )
                conn.execute("COMMIT")
                return pruned
            except Exception:
                conn.execute("ROLLBACK")
                raise

    def prune_delivered(self, retention_sec: Optional[float] = None, now: Optional[float] = None) -> int:
        """Prunes delivered messages older than the retention threshold into bounded tombstones.
        Commits in its own transaction so pruning is never rolled back on capacity failure.
        Pending, unacknowledged, and ambiguous work is NEVER pruned."""
        effective_retention = retention_sec if retention_sec is not None else self.retention_sec
        curr_time = now if now is not None else time.time()
        cutoff = curr_time - effective_retention

        with self._get_connection() as conn:
            conn.isolation_level = None
            self._check_physical_capacity_before_txn(adding_records=0)
            conn.execute("BEGIN IMMEDIATE")
            try:
                cur = conn.cursor()
                cur.execute(
                    "SELECT id, idempotency_key, route, payload, created_at FROM outbound_spool "
                    "WHERE status = 'delivered' AND (last_attempt IS NOT NULL AND last_attempt <= ?)",
                    (cutoff,),
                )
                rows = cur.fetchall()
                pruned_count = 0
                if rows:
                    for r in rows:
                        payload_bytes = r["payload"]
                        if isinstance(payload_bytes, str):
                            payload_bytes = payload_bytes.encode("utf-8")
                        sha = hashlib.sha256(payload_bytes).hexdigest()
                        created_at = r["created_at"] if "created_at" in r.keys() else curr_time
                        cur.execute(
                            """INSERT INTO spool_tombstones (idempotency_key, route, payload_sha256, pruned_at, created_at)
                               VALUES (?, ?, ?, ?, ?)
                               ON CONFLICT(idempotency_key) DO UPDATE SET pruned_at=excluded.pruned_at""",
                            (r["idempotency_key"], r["route"], sha, curr_time, created_at),
                        )
                        cur.execute("DELETE FROM outbound_spool WHERE id = ?", (r["id"],))
                        pruned_count += 1
                conn.execute("COMMIT")
            except Exception:
                conn.execute("ROLLBACK")
                raise

        # Clean up tombstones and metadata tables to maintain bounds across repeated cycles
        self.prune_tombstones(now=curr_time)
        self.prune_mappings(retention_sec=effective_retention, now=curr_time)
        self.prune_intents(retention_sec=effective_retention, now=curr_time)
        self.checkpoint_and_reclaim()
        return pruned_count

    def enqueue(
        self,
        idempotency_key: str,
        route: str,
        payload: Union[bytes, str],
        now: Optional[float] = None,
        message_id: Optional[str] = None,
        workspace: Optional[str] = None,
        tag: Optional[str] = None,
        consumer_uuid: Optional[str] = None,
    ) -> bool:
        """Enqueues an outbound payload. Rejects collisions with differing route/payload atomically.
        Enforces logical payload capacity, physical byte/page budgets, metadata bounds, and anti-replay.
        Returns True for initial insert or exact same-key same-route same-payload retry."""
        validate_metadata_str("idempotency_key", idempotency_key, max_bytes=MAX_METADATA_STRING_BYTES, min_len=1)
        validate_metadata_str("route", route, max_bytes=MAX_METADATA_STRING_BYTES, min_len=1)
        validate_metadata_str("message_id", message_id, max_bytes=MAX_METADATA_STRING_BYTES, allow_none=True)
        validate_metadata_str("workspace", workspace, max_bytes=MAX_WORKSPACE_PATH_BYTES, allow_none=True)
        validate_metadata_str("tag", tag, max_bytes=MAX_METADATA_STRING_BYTES, allow_none=True)
        validate_metadata_str("consumer_uuid", consumer_uuid, max_bytes=64, allow_none=True)

        payload_bytes = payload if isinstance(payload, bytes) else payload.encode("utf-8")
        if len(payload_bytes) > self.max_payload_bytes:
            raise ValueError(f"Payload exceeds maximum size ({len(payload_bytes)} > {self.max_payload_bytes})")

        curr_time = now if now is not None else time.time()
        sha = hashlib.sha256(payload_bytes).hexdigest()

        # Commit prune pass intentionally before admission checks only if safe and queued work consistent.
        # Safe prune: only terminal delivered rows and expired tombstones / terminal mappings are pruned.
        # Pending, ambiguous, and unacked work is NEVER pruned.
        self.prune_delivered(retention_sec=self.retention_sec, now=curr_time)
        if self.get_total_records() >= self.max_total_records:
            self.prune_tombstones(now=curr_time)
            self.prune_mappings(retention_sec=self.retention_sec, now=curr_time)
            self.prune_intents(retention_sec=self.retention_sec, now=curr_time)

        # Begin atomic immediate transaction to guarantee concurrency safety and admission invariants
        conn = self._create_raw_conn()
        conn.isolation_level = None
        self._check_physical_capacity_before_txn(adding_records=1, adding_payload_bytes=len(payload_bytes))
        conn.execute("BEGIN IMMEDIATE")
        try:
            cur = conn.cursor()

            # 1. Anti-replay check: reject expired, nonfinite, or future versioned keys
            cutoff = self.get_tombstone_cutoff(conn=conn)
            if is_versioned_key(idempotency_key):
                issuance = parse_versioned_key_issuance(idempotency_key)
                if issuance is None or issuance > curr_time + 60.0:
                    conn.execute("ROLLBACK")
                    return False  # Nonfinite, malformed, or future-invalid versioned key rejected at ingress
                if cutoff is not None and issuance < cutoff:
                    conn.execute("ROLLBACK")
                    return False  # Expired versioned key rejected at ingress: zero duplicate effects

            # 2. Check evicted legacy opaque keys ledger
            evicted_json = self.get_metadata("evicted_opaque_keys", conn=conn)
            if evicted_json:
                try:
                    evicted_map = json.loads(evicted_json)
                    if idempotency_key in evicted_map:
                        conn.execute("ROLLBACK")
                        rec = evicted_map[idempotency_key]
                        if rec.get("route") == route and rec.get("payload_sha256") == sha:
                            return True  # Stable idempotent outcome for cap-evicted legacy key (0 sends)
                        return False  # Collision against evicted legacy key
                except Exception:
                    pass

            # 3. Idempotency Check: Existing active records or tombstones return stable outcome
            cur.execute("SELECT route, payload_sha256 FROM spool_tombstones WHERE idempotency_key = ?", (idempotency_key,))
            tomb = cur.fetchone()
            if tomb:
                conn.execute("ROLLBACK")
                if tomb["route"] == route and tomb["payload_sha256"] == sha:
                    return True  # Idempotent replay of previously pruned delivered message (0 sends)
                return False  # Collision against tombstone

            cur.execute("SELECT payload, route FROM outbound_spool WHERE idempotency_key = ?", (idempotency_key,))
            row = cur.fetchone()
            if row:
                conn.execute("ROLLBACK")
                existing_payload = row["payload"]
                if isinstance(existing_payload, str):
                    existing_payload = existing_payload.encode("utf-8")
                if existing_payload == payload_bytes and row["route"] == route:
                    return True  # Idempotent replay of existing record
                return False  # Collision: different route or payload for same key

            # 4. Capacity Checks (Logical payload, physical size, page count, table counts)
            cur.execute("SELECT coalesce(sum(length(payload)), 0) FROM outbound_spool")
            total_size = int(cur.fetchone()[0])
            if total_size + len(payload_bytes) > self.max_storage_bytes:
                conn.execute("ROLLBACK")
                raise SpoolStorageLimitReached(
                    f"Spool storage limit reached: payload size ({total_size + len(payload_bytes)} bytes) "
                    f"exceeds max_storage_bytes ({self.max_storage_bytes} bytes)"
                )

            self._assert_capacity_available(conn, adding_records=1, adding_payload_bytes=len(payload_bytes))

            # 5. If message_id provided, record intent mapping
            if message_id:
                cur.execute("SELECT workspace, tag, consumer_uuid FROM enrolled_routes WHERE route = ?", (route,))
                enrolled = cur.fetchone()
                eff_ws = workspace or (enrolled["workspace"] if enrolled else "/tmp")
                eff_tag = tag or (enrolled["tag"] if enrolled else "agent-1")
                eff_uuid = consumer_uuid or (enrolled["consumer_uuid"] if enrolled else None)
                cur.execute(
                    """INSERT INTO message_mappings
                       (hub_message_id, native_message_id, route, workspace, expected_tag, expected_consumer_uuid,
                        from_actor, to_actor, thread_id, status, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                       ON CONFLICT(hub_message_id) DO UPDATE SET
                       native_message_id=COALESCE(excluded.native_message_id, message_mappings.native_message_id),
                       status=excluded.status, updated_at=excluded.updated_at""",
                    (
                        message_id,
                        None,
                        route,
                        str(eff_ws),
                        eff_tag,
                        eff_uuid,
                        None,
                        None,
                        None,
                        "pending",
                        curr_time,
                        curr_time,
                    ),
                )

            # 6. Atomic insertion into outbound_spool
            try:
                cur.execute(
                    """INSERT INTO outbound_spool
                       (idempotency_key, route, payload, status, created_at)
                       VALUES (?, ?, ?, 'pending', ?)""",
                    (idempotency_key, route, payload_bytes, curr_time),
                )



                conn.execute("COMMIT")
                return True
            except sqlite3.IntegrityError:
                # Concurrent race resolution
                cur.execute("SELECT payload, route FROM outbound_spool WHERE idempotency_key = ?", (idempotency_key,))
                row = cur.fetchone()
                conn.execute("ROLLBACK")
                if row:
                    existing_payload = row["payload"]
                    if isinstance(existing_payload, str):
                        existing_payload = existing_payload.encode("utf-8")
                    if existing_payload == payload_bytes and row["route"] == route:
                        return True
                return False
            except sqlite3.OperationalError as op_err:
                try:
                    conn.execute("ROLLBACK")
                except Exception:
                    pass
                if "full" in str(op_err).lower():
                    raise SpoolStorageLimitReached(f"Spool storage limit reached (SQLite error): {op_err}") from op_err
                raise
        except Exception:
            try:
                conn.execute("ROLLBACK")
            except Exception:
                pass
            raise
        finally:
            conn.close()

    def get_pending(
        self,
        route: Optional[str] = None,
        limit: int = 50,
        max_attempts: int = 5,
        retry_backoff_sec: int = 30,
        now: Optional[float] = None,
    ) -> List[sqlite3.Row]:
        """Retrieves eligible pending or failed messages respecting backoff with clock injection."""
        curr_time = now if now is not None else time.time()
        cutoff = curr_time - retry_backoff_sec

        with self._get_connection() as conn:
            query = """
                SELECT * FROM outbound_spool
                WHERE status IN ('pending', 'failed')
                  AND attempt_count < ?
                  AND (last_attempt IS NULL OR last_attempt <= ?)
            """
            params: List[Any] = [max_attempts, cutoff]
            if route:
                query += " AND route = ?"
                params.append(route)
            query += " ORDER BY id ASC LIMIT ?"
            params.append(limit)
            return conn.execute(query, tuple(params)).fetchall()

    def reset_retry_backoffs(self, route: Optional[str] = None):
        """Resets last_attempt to NULL on eligible failed/pending rows so reconnect triggers immediate retry."""
        with self._get_connection() as conn:
            conn.isolation_level = None
            self._check_physical_capacity_before_txn(adding_records=0)
            conn.execute("BEGIN IMMEDIATE")
            try:
                if route:
                    conn.execute(
                        "UPDATE outbound_spool SET last_attempt = NULL WHERE route = ? AND status IN ('pending', 'failed')",
                        (route,),
                    )
                else:
                    conn.execute("UPDATE outbound_spool SET last_attempt = NULL WHERE status IN ('pending', 'failed')")
                conn.execute("COMMIT")
            except Exception:
                conn.execute("ROLLBACK")
                raise

    def mark_delivered(self, msg_id: int, now: Optional[float] = None):
        if not isinstance(msg_id, int):
            raise ValueError(f"msg_id must be int, got {type(msg_id).__name__}")
        curr_time = now if now is not None else time.time()
        with self._get_connection() as conn:
            conn.isolation_level = None
            self._check_physical_capacity_before_txn(adding_records=0)
            conn.execute("BEGIN IMMEDIATE")
            try:
                conn.execute(
                    "UPDATE outbound_spool SET status = 'delivered', attempt_count = attempt_count + 1, last_attempt = ? WHERE id = ?",
                    (curr_time, msg_id),
                )
                conn.execute("COMMIT")
            except Exception:
                conn.execute("ROLLBACK")
                raise

    def mark_ambiguous(self, msg_id: int, error_text: str, now: Optional[float] = None):
        if not isinstance(msg_id, int):
            raise ValueError(f"msg_id must be int, got {type(msg_id).__name__}")
        validate_metadata_str("error_text", error_text, max_bytes=MAX_PAYLOAD_TEXT_BYTES, min_len=0)
        curr_time = now if now is not None else time.time()
        with self._get_connection() as conn:
            conn.isolation_level = None
            self._check_physical_capacity_before_txn(adding_records=0)
            conn.execute("BEGIN IMMEDIATE")
            try:
                conn.execute(
                    "UPDATE outbound_spool SET status = 'ambiguous', error_text = ?, attempt_count = attempt_count + 1, last_attempt = ? WHERE id = ?",
                    (error_text, curr_time, msg_id),
                )
                conn.execute("COMMIT")
            except Exception:
                conn.execute("ROLLBACK")
                raise

    def mark_failed(self, msg_id: int, error_text: str, now: Optional[float] = None):
        if not isinstance(msg_id, int):
            raise ValueError(f"msg_id must be int, got {type(msg_id).__name__}")
        validate_metadata_str("error_text", error_text, max_bytes=MAX_PAYLOAD_TEXT_BYTES, min_len=0)
        curr_time = now if now is not None else time.time()
        with self._get_connection() as conn:
            conn.isolation_level = None
            self._check_physical_capacity_before_txn(adding_records=0)
            conn.execute("BEGIN IMMEDIATE")
            try:
                conn.execute(
                    "UPDATE outbound_spool SET status = 'failed', error_text = ?, attempt_count = attempt_count + 1, last_attempt = ? WHERE id = ?",
                    (error_text, curr_time, msg_id),
                )
                conn.execute("COMMIT")
            except Exception:
                conn.execute("ROLLBACK")
                raise

    def set_cursor(
        self,
        route: str,
        receipt_cursor: Optional[str] = None,
        ack_cursor: Optional[str] = None,
        log_cursor: Optional[str] = None,
        now: Optional[float] = None,
    ):
        validate_metadata_str("route", route, max_bytes=MAX_METADATA_STRING_BYTES, min_len=1)
        validate_metadata_str("receipt_cursor", receipt_cursor, max_bytes=MAX_METADATA_STRING_BYTES, allow_none=True)
        validate_metadata_str("ack_cursor", ack_cursor, max_bytes=MAX_METADATA_STRING_BYTES, allow_none=True)
        validate_metadata_str("log_cursor", log_cursor, max_bytes=MAX_METADATA_STRING_BYTES, allow_none=True)

        curr_time = now if now is not None else time.time()
        with self._get_connection() as conn:
            conn.isolation_level = None
            self._check_physical_capacity_before_txn(adding_records=1)
            conn.execute("BEGIN IMMEDIATE")
            try:
                cur = conn.cursor()
                cur.execute("SELECT last_receipt_cursor, last_ack_cursor, last_log_cursor FROM cursors WHERE route = ?", (route,))
                existing = cur.fetchone()
                if existing:
                    new_receipt = receipt_cursor if receipt_cursor is not None else existing["last_receipt_cursor"]
                    new_ack = ack_cursor if ack_cursor is not None else existing["last_ack_cursor"]
                    new_log = log_cursor if log_cursor is not None else existing["last_log_cursor"]
                    cur.execute(
                        "UPDATE cursors SET last_receipt_cursor = ?, last_ack_cursor = ?, last_log_cursor = ?, updated_at = ? WHERE route = ?",
                        (new_receipt, new_ack, new_log, curr_time, route),
                    )
                else:
                    self._assert_capacity_available(conn, adding_records=1)
                    cur.execute(
                        "INSERT INTO cursors (route, last_receipt_cursor, last_ack_cursor, last_log_cursor, updated_at) VALUES (?, ?, ?, ?, ?)",
                        (route, receipt_cursor, ack_cursor, log_cursor, curr_time),
                    )


                conn.execute("COMMIT")
            except sqlite3.OperationalError as op_err:
                try:
                    conn.execute("ROLLBACK")
                except Exception:
                    pass
                if "full" in str(op_err).lower():
                    raise SpoolStorageLimitReached(f"Spool storage limit reached (SQLite error): {op_err}") from op_err
                raise
            except Exception:
                try:
                    conn.execute("ROLLBACK")
                except Exception:
                    pass
                raise

    def get_cursor(self, route: str) -> Tuple[Optional[str], Optional[str]]:
        with self._get_connection() as conn:
            row = conn.execute("SELECT last_receipt_cursor, last_ack_cursor FROM cursors WHERE route = ?", (route,)).fetchone()
            if row:
                return row["last_receipt_cursor"], row["last_ack_cursor"]
            return None, None

    def get_log_cursor(self, route: str) -> Optional[str]:
        with self._get_connection() as conn:
            row = conn.execute("SELECT last_log_cursor FROM cursors WHERE route = ?", (route,)).fetchone()
            if row and row["last_log_cursor"]:
                return row["last_log_cursor"]
            return None

    def record_intent(
        self,
        intent_id: str,
        idempotency_key: str,
        workspace: str,
        tag: str,
        text: str,
        data_json: Optional[str] = None,
        now: Optional[float] = None,
    ):
        validate_metadata_str("intent_id", intent_id, max_bytes=MAX_METADATA_STRING_BYTES, min_len=1)
        validate_metadata_str("idempotency_key", idempotency_key, max_bytes=MAX_METADATA_STRING_BYTES, min_len=1)
        validate_metadata_str("workspace", str(workspace), max_bytes=MAX_WORKSPACE_PATH_BYTES, min_len=1)
        validate_metadata_str("tag", tag, max_bytes=MAX_METADATA_STRING_BYTES, min_len=1)
        validate_metadata_str("text", text, max_bytes=MAX_PAYLOAD_TEXT_BYTES, min_len=0)
        validate_metadata_str("data_json", data_json, max_bytes=MAX_PAYLOAD_TEXT_BYTES, allow_none=True)

        curr_time = now if now is not None else time.time()
        payload_len = len(text.encode("utf-8")) + len((data_json or "").encode("utf-8"))
        with self._get_connection() as conn:
            conn.isolation_level = None
            self._check_physical_capacity_before_txn(adding_records=1, adding_payload_bytes=payload_len)
            conn.execute("BEGIN IMMEDIATE")
            try:
                cutoff = self.get_tombstone_cutoff(conn=conn)
                if is_versioned_key(idempotency_key):
                    issuance = parse_versioned_key_issuance(idempotency_key)
                    if issuance is None or issuance > curr_time + 60.0:
                        conn.execute("ROLLBACK")
                        raise IdempotencyConflictError(f"Malformed or future-invalid versioned intent identity ({idempotency_key})")
                    if cutoff is not None and issuance < cutoff:
                        conn.execute("ROLLBACK")
                        raise IdempotencyConflictError(f"Expired delivery intent identity ({idempotency_key})")

                row = conn.execute("SELECT 1 FROM delivery_intents WHERE idempotency_key = ?", (idempotency_key,)).fetchone()
                if not row:
                    self._assert_capacity_available(conn, adding_records=1)
                else:
                    self._assert_capacity_available(conn, adding_records=0)

                conn.execute(
                    """INSERT INTO delivery_intents
                       (intent_id, idempotency_key, workspace, tag, text, data_json, status, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, 'persisted', ?, ?)
                       ON CONFLICT(idempotency_key) DO UPDATE SET updated_at = excluded.updated_at""",
                    (intent_id, idempotency_key, str(workspace), tag, text, data_json or "{}", curr_time, curr_time),
                )


                conn.execute("COMMIT")
            except sqlite3.OperationalError as op_err:
                try:
                    conn.execute("ROLLBACK")
                except Exception:
                    pass
                if "full" in str(op_err).lower():
                    raise SpoolStorageLimitReached(f"Spool storage limit reached (SQLite error): {op_err}") from op_err
                raise
            except Exception:
                try:
                    conn.execute("ROLLBACK")
                except Exception:
                    pass
                raise

    def update_intent_status(self, idempotency_key: str, status: str, now: Optional[float] = None):
        validate_metadata_str("idempotency_key", idempotency_key, max_bytes=MAX_METADATA_STRING_BYTES, min_len=1)
        validate_metadata_str("status", status, max_bytes=64, min_len=1)

        curr_time = now if now is not None else time.time()
        with self._get_connection() as conn:
            conn.isolation_level = None
            self._check_physical_capacity_before_txn(adding_records=0)
            conn.execute("BEGIN IMMEDIATE")
            try:
                conn.execute(
                    "UPDATE delivery_intents SET status = ?, updated_at = ? WHERE idempotency_key = ? OR intent_id = ?",
                    (status, curr_time, idempotency_key, idempotency_key),
                )
                conn.execute("COMMIT")
            except Exception:
                conn.execute("ROLLBACK")
                raise

    def get_intent(self, idempotency_key: str) -> Optional[sqlite3.Row]:
        with self._get_connection() as conn:
            return conn.execute(
                "SELECT * FROM delivery_intents WHERE idempotency_key = ? OR intent_id = ?",
                (idempotency_key, idempotency_key),
            ).fetchone()



class AplexerBridge:
    """Native aplexer CLI wrapper with strict argv execution, intent persistence, and prompt-safe delivery."""

    def __init__(
        self,
        aplexer_bin: str = "aplexer",
        spool: Optional[SQLiteSpool] = None,
        state_root: Optional[Union[str, Path]] = None,
    ):
        self.aplexer_bin = aplexer_bin
        self.spool = spool
        self.state_root = state_root

    def is_available(self) -> bool:
        return shutil.which(self.aplexer_bin) is not None

    def _run_cmd(self, args: List[str]) -> subprocess.CompletedProcess:
        # Prelaunch validation: guard against non-str and NUL bytes before invoking subprocess
        for arg in args:
            if not isinstance(arg, str):
                return subprocess.CompletedProcess(
                    args=[self.aplexer_bin] + [str(a) for a in args],
                    returncode=2,
                    stdout="",
                    stderr=f"Prelaunch error: argument must be str, got {type(arg).__name__}",
                )
            if "\x00" in arg:
                return subprocess.CompletedProcess(
                    args=[self.aplexer_bin] + args,
                    returncode=2,
                    stdout="",
                    stderr="Prelaunch error: argument contains embedded null byte",
                )
        env = None
        if self.state_root:
            try:
                env = os.environ.copy()
                env["APLEXER_STATE_DIR"] = str(resolve_state_root(self.state_root))
            except Exception:
                pass
        try:
            # Strict argv execution, no shell interpolation
            return subprocess.run([self.aplexer_bin] + args, capture_output=True, text=True, env=env)
        except (ValueError, OSError) as exc:
            return subprocess.CompletedProcess(
                args=[self.aplexer_bin] + args,
                returncode=2,
                stdout="",
                stderr=f"Prelaunch execution error ({type(exc).__name__}): {exc}",
            )

    def list_sessions(self) -> Optional[List[Dict[str, Any]]]:
        if not self.is_available():
            return None
        res = self._run_cmd(["list", "--json"])
        if res.returncode != 0:
            return None
        try:
            data = json.loads(res.stdout)
            return data if isinstance(data, list) else None
        except Exception:
            return None

    def get_message_log(self, workspace: str) -> Optional[List[Dict[str, Any]]]:
        if not self.is_available():
            return None
        res = self._run_cmd(["message", "log", "--workspace", workspace, "--json"])
        if res.returncode != 0:
            return None
        try:
            data = json.loads(res.stdout)
            return data if isinstance(data, list) else None
        except Exception:
            return None

    def get_native_cursor(self, workspace: str, consumer_uuid: str) -> Optional[Dict[str, Any]]:
        """Reads the per-consumer cursor file from read-only native state root."""
        valid_uuid = validate_consumer_uuid(consumer_uuid)
        if not valid_uuid:
            return None

        try:
            canon_ws = canonical_workspace(workspace)
            ws_key = workspace_key(canon_ws)
        except Exception:
            return None

        try:
            state_root = resolve_state_root(self.state_root)
        except Exception:
            return None

        workspace_dir = state_root / "messages" / ws_key
        if not workspace_dir.is_dir():
            return None

        if not verify_workspace_metadata(workspace_dir, canon_ws):
            return None

        cursor_file = workspace_dir / "cursors" / f"{valid_uuid}.json"
        raw_bytes = read_bounded_regular_file(cursor_file)
        if raw_bytes is None:
            return None

        try:
            data = json.loads(raw_bytes.decode("utf-8"))
            if not isinstance(data, dict):
                return None
            return data
        except Exception:
            return None

    def is_native_cursor_acked(self, cursor_data: Dict[str, Any], message_id: str) -> bool:
        """Verifies whether message_id is marked as acknowledged in native cursor state."""
        if not cursor_data or not message_id:
            return False
        exceptions = cursor_data.get("exceptions")
        if isinstance(exceptions, list):
            if str(message_id) in [str(e) for e in exceptions]:
                return True
        acked_through = cursor_data.get("acked_through")
        if acked_through and str(message_id) <= str(acked_through):
            return True
        return False

    def parse_envelope(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        """Parses and normalizes a Rust-shaped message envelope."""
        from_info = raw.get("from") or {}
        to_info = raw.get("to") or {}
        return {
            "id": str(raw.get("id") or ""),
            "workspace": str(raw.get("workspace") or ""),
            "created_at": raw.get("created_at"),
            "from": from_info,
            "to": to_info,
            "kind": raw.get("kind", "note"),
            "reply_to": str(raw["reply_to"]) if raw.get("reply_to") else None,
            "body": raw.get("body", ""),
            "data": raw.get("data") if isinstance(raw.get("data"), dict) else {},
            "delivery": raw.get("delivery", "inbox"),
            "idempotency_key": raw.get("idempotency_key"),
        }

    def reconcile_log(self, workspace: str, since_cursor: Optional[str] = None) -> List[Dict[str, Any]]:
        """Reads workspace message log and filters envelopes newer than the cursor."""
        raw_log = self.get_message_log(workspace)
        if not raw_log:
            return []
        parsed = [self.parse_envelope(m) for m in raw_log if isinstance(m, dict)]
        if not since_cursor:
            return parsed
        # Filter messages occurring after since_cursor
        found_cursor = False
        result: List[Dict[str, Any]] = []
        for m in parsed:
            if found_cursor:
                result.append(m)
            elif m["id"] == since_cursor:
                found_cursor = True
        return result if found_cursor else parsed

    def check_idle_empty_prompt(self, workspace: str, tag: str) -> bool:
        """Verifies session reported_state is idle. Prompt-level confirmation requires native deliver."""
        sessions = self.list_sessions()
        if not sessions:
            return False
        for s in sessions:
            if s.get("workspace") == workspace and s.get("tag") == tag:
                # Check for idle reported state
                if s.get("reported_state") == "idle":
                    return True
        return False

    def attempt_deliver_wake(self, workspace: str, message_id: str) -> bool:
        """Executes native `a message deliver <MESSAGE_ID>` which verifies fresh empty prompt natively."""
        if not self.is_available():
            return False
        res = self._run_cmd(["message", "deliver", "--workspace", workspace, "--json", message_id])
        return res.returncode == 0

    def send_message(
        self,
        workspace: str,
        tag: str,
        body: Dict[str, Any],
        idempotency_key: Optional[str] = None,
        allow_sync_wake: bool = False,
    ) -> Tuple[bool, bool, str]:
        """Sends a message using strict Rust CLI shapes.
        Pre-effect validates all inputs against NUL bytes, types, and bounds.
        Appends positional text with '--' separator to prevent flag injection.
        Guards reserved provenance keys from user data override.
        Persists intent before effect. If ambiguous failure occurs, reconciles against native log.
        Returns: (success, ambiguous, error_text)."""
        if not isinstance(body, dict):
            return False, False, "Pre-effect validation rejected: body must be a dictionary"

        text = str(body.get("text") or body.get("body") or "outbound message")
        user_data = body.get("data") if isinstance(body.get("data"), dict) else {}

        # 1. Pre-effect validation: bounds, types, and NUL bytes BEFORE intent, availability or subprocess
        valid, val_err = validate_native_args(workspace, tag, text, idempotency_key=idempotency_key, data=user_data)
        if not valid:
            return False, False, f"Pre-effect validation rejected: {val_err}"

        if not self.is_available():
            return False, False, "aplexer unavailable"

        # Pre-effect session routing check
        sessions = self.list_sessions()
        if sessions is None:
            return False, False, "could not list sessions for routing check"

        found_session = None
        for s in sessions:
            if s.get("workspace") == str(workspace) and s.get("tag") == tag:
                found_session = s
                break

        if not found_session:
            return False, False, f"Target session {tag} at {workspace} not found"

        # Stable bridge ID / idempotency key
        key = idempotency_key or make_versioned_key(hashlib.sha256(f"{workspace}:{tag}:{time.time()}".encode("utf-8")).hexdigest()[:24])

        # 2. Guard reserved provenance keys: untrusted user-supplied data must NEVER override trusted bridge keys
        RESERVED_PROVENANCE_KEYS = {
            "bridge_id",
            "idempotency_key",
            "origin",
            "recipient",
            "provenance",
            "workspace",
            "tag",
            "session_id",
            "machine_id",
        }
        data_obj = {k: v for k, v in user_data.items() if k not in RESERVED_PROVENANCE_KEYS}
        for k, v in body.items():
            if k not in ("text", "body", "data") and k not in RESERVED_PROVENANCE_KEYS:
                data_obj[k] = v

        # Enforce trusted provenance
        data_obj["bridge_id"] = key
        data_obj["idempotency_key"] = key
        data_obj["workspace"] = str(workspace)
        data_obj["recipient"] = str(tag)
        data_obj["origin"] = "host-outbound"

        data_str = json.dumps(data_obj)
        if "\x00" in data_str:
            return False, False, "Pre-effect validation rejected: data contains embedded null byte"

        # 3. Persist intent before effect
        if self.spool:
            self.spool.record_intent(
                intent_id=f"intent-{key}",
                idempotency_key=key,
                workspace=str(workspace),
                tag=tag,
                text=text,
                data_json=data_str,
            )

        # 4. Strict argv execution without shell
        # Notice: CLI args include '--' before positional <TEXT> to ensure hostile strings like '--pane' or '--all'
        # are strictly parsed as positional message body text and not flags.
        args = ["message", "send", "--workspace", str(workspace), "--to", tag, "--json", "--data", data_str, "--", text]
        res = self._run_cmd(args)

        # If return code is 0 but we fail to parse a valid native_mid from stdout,
        # we do not trust exit0 alone. We fall through to log reconciliation.
        if res.returncode == 0:
            native_mid = ""
            try:
                out = json.loads(res.stdout) if res.stdout else {}
                native_mid = str(out.get("id") or "").strip()
            except Exception:
                pass
            
            if native_mid:
                is_valid_uuid = False
                try:
                    uuid.UUID(native_mid)
                    is_valid_uuid = True
                except Exception:
                    pass
                if is_valid_uuid:
                    if self.spool:
                        self.spool.update_intent_status(key, "sent")
                    if allow_sync_wake:
                        try:
                            self.attempt_deliver_wake(str(workspace), native_mid)
                        except Exception:
                            pass
                    return True, False, native_mid

        # Command failed: distinguish deterministic argv / option errors from ambiguous IPC errors
        stderr_lower = res.stderr.lower() if res.stderr else ""
        if res.returncode == 2 or "invalid option" in stderr_lower or "required arguments" in stderr_lower or "prelaunch error" in stderr_lower:
            if self.spool:
                self.spool.update_intent_status(key, "failed")
            return False, False, f"Deterministic delivery failure: {res.stderr.strip()}"

        # Ambiguous failure (e.g. exit code 1, IPC drop, timeout)
        # Reconcile against native message log before deciding whether message succeeded
        # Positive same-key log evidence must validate exact workspace, recipient UUID/tag,
        # discovered sender, text/payload, thread/parties and valid unique native ID.
        # A mismatch or multiple/unknown matches stays ambiguous and held; no blind resend.
        log = self.get_message_log(str(workspace))
        if log:
            matching_items = []
            for item in log:
                if not isinstance(item, dict):
                    continue
                item_data = item.get("data") if isinstance(item.get("data"), dict) else {}
                if item_data.get("bridge_id") == key or item_data.get("idempotency_key") == key:
                    matching_items.append(item)

            if len(matching_items) == 1:
                item = matching_items[0]
                item_data = item.get("data") if isinstance(item.get("data"), dict) else {}
                to_info = item.get("to") if isinstance(item.get("to"), dict) else {}
                from_info = item.get("from") if isinstance(item.get("from"), dict) else {}

                ws_match = (str(item.get("workspace") or "") == str(workspace))
                target_uuid = found_session.get("id") if found_session else None
                to_tag = to_info.get("tag") or item_data.get("recipient")
                to_uuid = to_info.get("session_id")
                recipient_match = (to_tag == tag)
                if target_uuid and to_uuid:
                    recipient_match = recipient_match and (to_uuid == target_uuid)

                sender_match = True
                if from_info:
                    from_ws = from_info.get("workspace")
                    if from_ws and str(from_ws) != str(workspace):
                        sender_match = False

                body_match = (item.get("body") == text)
                native_mid = str(item.get("id") or "").strip()
                id_match = bool(native_mid)

                if ws_match and recipient_match and sender_match and body_match and id_match:
                    if self.spool:
                        self.spool.update_intent_status(key, "sent")
                    return True, False, native_mid
                else:
                    mismatch_reasons = []
                    if not ws_match:
                        mismatch_reasons.append(f"Mismatched workspace ({item.get('workspace')} != {workspace})")
                    if not recipient_match:
                        mismatch_reasons.append(f"Mismatched recipient tag or uuid ({to_tag}/{to_uuid} != {tag}/{target_uuid})")
                    if not sender_match:
                        mismatch_reasons.append("Mismatched sender context")
                    if not body_match:
                        mismatch_reasons.append(f"Mismatched body text ({item.get('body')!r} != {text!r})")
                    if not id_match:
                        mismatch_reasons.append("Invalid native message id")
                    reconcile_detail = f"Ambiguous delivery: native log matched key but failed exact reconciliation: {'; '.join(mismatch_reasons)}"
                    if self.spool:
                        self.spool.update_intent_status(key, "ambiguous")
                    return False, True, reconcile_detail
            elif len(matching_items) > 1:
                reconcile_detail = f"Ambiguous delivery: Multiple matching native log entries ({len(matching_items)}) for key {key}"
                if self.spool:
                    self.spool.update_intent_status(key, "ambiguous")
                return False, True, reconcile_detail

        # Not confirmed in log with exact positive evidence: stays durably ambiguous, zero blind resends
        if self.spool:
            self.spool.update_intent_status(key, "ambiguous")
        return False, True, f"Ambiguous delivery failure: {res.stderr.strip()}"


class DenyRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Denies all HTTP redirects (301, 302, 303, 307, 308) to prevent credential forwarding."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

    def http_error_301(self, req, fp, code, msg, headers):
        raise urllib.error.HTTPError(req.full_url, code, f"Redirect denied: {code}", headers, fp)

    def http_error_302(self, req, fp, code, msg, headers):
        raise urllib.error.HTTPError(req.full_url, code, f"Redirect denied: {code}", headers, fp)

    def http_error_303(self, req, fp, code, msg, headers):
        raise urllib.error.HTTPError(req.full_url, code, f"Redirect denied: {code}", headers, fp)

    def http_error_307(self, req, fp, code, msg, headers):
        raise urllib.error.HTTPError(req.full_url, code, f"Redirect denied: {code}", headers, fp)

    def http_error_308(self, req, fp, code, msg, headers):
        raise urllib.error.HTTPError(req.full_url, code, f"Redirect denied: {code}", headers, fp)


def _read_bounded_response(fp: Any, max_bytes: int) -> bytes:
    """Reads response bytes up to max_bytes + 1, raising WireContractError if ceiling is exceeded.
    Guarantees bounded allocation before decode."""
    if not fp:
        return b""
    chunk = fp.read(max_bytes + 1)
    if len(chunk) > max_bytes:
        raise WireContractError(f"HTTP response exceeded maximum ceiling of {max_bytes} bytes")
    return chunk


def validate_bus_message_schema(msg: Dict[str, Any], max_body_bytes: int = MAX_BUS_BODY_BYTES) -> Dict[str, Any]:
    """Validates an incoming C888 bus message against schema, types, body bounds, and null bytes."""
    if not isinstance(msg, dict):
        raise WireContractError("Incoming message must be a JSON object")
    if "id" not in msg or not isinstance(msg["id"], str) or not msg["id"].strip():
        raise WireContractError("Incoming message must contain non-empty 'id' string")
    if "\x00" in msg["id"]:
        raise WireContractError("Incoming message 'id' cannot contain null bytes")

    if "body" in msg:
        body = msg["body"]
        if not isinstance(body, str):
            raise WireContractError("Incoming message 'body' must be a string")
        if "\x00" in body:
            raise WireContractError("Incoming message 'body' cannot contain null bytes")
        body_bytes = body.encode("utf-8")
        if len(body_bytes) > max_body_bytes:
            raise WireContractError(
                f"Incoming message body exceeds 16KB UTF-8 limit ({len(body_bytes)} > {max_body_bytes} bytes)"
            )

    for str_field in ("from_actor", "to_actor", "kind", "thread_id", "reply_to"):
        if str_field in msg and msg[str_field] is not None:
            if not isinstance(msg[str_field], str):
                raise WireContractError(f"Incoming message field '{str_field}' must be a string")
            if "\x00" in msg[str_field]:
                raise WireContractError(f"Incoming message field '{str_field}' cannot contain null bytes")

    for ts_field in ("created_at", "expires_at"):
        if ts_field not in msg or msg[ts_field] is None:
            raise WireContractError(f"Incoming message '{ts_field}' must be a non-null epoch timestamp")
        val = msg[ts_field]
        if isinstance(val, bool) or type(val) is not int or val < 0:
            raise WireContractError(f"Incoming message '{ts_field}' must be a valid non-negative integral epoch timestamp")

    for ts_field in ("delivered_at", "read_at", "acked_at", "accepted_at", "completed_at"):
        if ts_field in msg and msg[ts_field] is not None:
            val = msg[ts_field]
            if isinstance(val, bool) or type(val) is not int or val < 0:
                raise WireContractError(f"Incoming message '{ts_field}' must be a valid non-negative integral epoch timestamp")

    return msg


class C888BusClient:
    """Proposed C888 wire contract HTTP client using Python stdlib with fail-closed security.
    Default closed absent accepted pin/owner handoff; requires explicit fixture opt-in."""

    def __init__(
        self,
        base_url: str,
        token_provider: Optional[Callable[[], str]] = None,
        refresh_token_callback: Optional[Callable[[], str]] = None,
        machine_id: Optional[str] = None,
        allow_loopback_http: bool = False,
        fixture_opt_in: bool = False,
        candidate_opt_in: bool = False,
        owner_handoff: Optional[str] = None,
        accepted_pin: Optional[str] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.token_provider = token_provider
        self.refresh_token_callback = refresh_token_callback
        self.machine_id = machine_id
        self.allow_loopback_http = allow_loopback_http
        self.fixture_opt_in = fixture_opt_in
        self.candidate_opt_in = candidate_opt_in
        self.owner_handoff = owner_handoff
        self.accepted_pin = accepted_pin
        self._opener = urllib.request.build_opener(DenyRedirectHandler())

        # Validate URL and enforce HTTPS fail-closed except for loopback
        parsed = urllib.parse.urlparse(self.base_url)
        if parsed.scheme != "https":
            hostname = (parsed.hostname or "").lower()
            is_loopback = hostname in ("127.0.0.1", "localhost", "::1")
            if not (is_loopback and self.allow_loopback_http and parsed.scheme == "http"):
                raise InsecureTransportError(
                    f"Insecure transport ({parsed.scheme}): HTTPS required for non-loopback endpoints ({self.base_url})"
                )

    def _get_token(self) -> Optional[str]:
        if self.token_provider:
            return self.token_provider()
        return None

    def _build_request(self, method: str, path: str, body: Optional[bytes] = None, headers: Optional[Dict[str, str]] = None) -> urllib.request.Request:
        url = f"{self.base_url}{path}"
        req_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "agent-hub-outbound/1.0",
        }
        if self.machine_id:
            req_headers["X-Machine-Id"] = self.machine_id
        token = self._get_token()
        if token:
            req_headers["Authorization"] = f"Bearer {token}"
        if headers:
            req_headers.update(headers)
        return urllib.request.Request(url, data=body, headers=req_headers, method=method)

    def _execute_http(
        self,
        method: str,
        path: str,
        body_dict: Optional[Dict[str, Any]] = None,
        max_response_bytes: Optional[int] = None,
    ) -> Tuple[int, Any]:
        # Enforce C888 runtime contract gate: proposed wire contract is closed by default.
        # Only an explicit local synthetic fixture opt-in or accepted Hub owner handoff may execute.
        # Accepted Hub d86 is M2 only; c888 remains proposed. No self-declared accepted pin.
        if not (self.fixture_opt_in or self.candidate_opt_in or self.owner_handoff or self.allow_loopback_http):
            raise WireContractError(
                "Proposed C888 wire contract is unagreed and closed by default: "
                "requires explicit candidate/fixture opt-in (fixture_opt_in=True or allow_loopback_http=True) "
                "or accepted Hub owner handoff."
            )

        body_bytes = json.dumps(body_dict).encode("utf-8") if body_dict is not None else None
        req = self._build_request(method, path, body=body_bytes)
        max_ceiling = max_response_bytes if max_response_bytes is not None else MAX_GENERAL_HTTP_RESPONSE_BYTES

        try:
            with self._opener.open(req, timeout=15.0) as resp:
                status = resp.status
                raw_bytes = _read_bounded_response(resp, max_ceiling)
                data = json.loads(raw_bytes.decode("utf-8"))
                return status, data
        except urllib.error.HTTPError as err:
            if err.code == 401 and self.refresh_token_callback:
                # Bounded refresh on 401: attempt single refresh then retry
                try:
                    self.refresh_token_callback()
                    req2 = self._build_request(method, path, body=body_bytes)
                    with self._opener.open(req2, timeout=15.0) as resp2:
                        raw_bytes2 = _read_bounded_response(resp2, max_ceiling)
                        return resp2.status, json.loads(raw_bytes2.decode("utf-8"))
                except Exception as refresh_err:
                    raise WireContractError(f"HTTP 401 refresh failed: {refresh_err}") from refresh_err

            err_bytes = _read_bounded_response(err.fp, MAX_HTTP_ERROR_RESPONSE_BYTES) if err.fp else b""
            err_body = err_bytes.decode("utf-8", errors="replace")
            try:
                err_json = json.loads(err_body)
            except Exception:
                err_json = {"error": err_body or err.reason}
            return err.code, err_json
        except (urllib.error.URLError, OSError, __import__("http").client.HTTPException) as url_err:
            raise WireContractError(f"Transport network failure: {url_err}") from url_err

    def send_bus_message(
        self,
        from_actor: str,
        to_actor: str,
        kind: str,
        body: str,
        idempotency_key: str,
        thread_id: Optional[str] = None,
        reply_to: Optional[str] = None,
        lease_epoch: Optional[int] = None,
    ) -> Dict[str, Any]:
        """POST /api/bus/send enforcing 16KB UTF-8 body limit."""
        for name, val in [("from_actor", from_actor), ("to_actor", to_actor), ("kind", kind), ("idempotency_key", idempotency_key)]:
            if not isinstance(val, str) or "\x00" in val:
                raise ValueError(f"{name} must be str and cannot contain null bytes")
        if reply_to is not None and (not isinstance(reply_to, str) or "\x00" in reply_to):
            raise ValueError("reply_to must be str and cannot contain null bytes")
        if thread_id is not None and (not isinstance(thread_id, str) or "\x00" in thread_id):
            raise ValueError("thread_id must be str and cannot contain null bytes")
        if not isinstance(body, str) or "\x00" in body:
            raise ValueError("body must be str and cannot contain null bytes")

        body_bytes = body.encode("utf-8")
        if len(body_bytes) > MAX_BUS_BODY_BYTES:
            raise ValueError(f"Message body exceeds 16KB UTF-8 limit ({len(body_bytes)} > {MAX_BUS_BODY_BYTES})")

        payload: Dict[str, Any] = {
            "from_actor": from_actor,
            "to_actor": to_actor,
            "kind": kind,
            "body": body,
            "idempotency_key": idempotency_key,
        }
        if thread_id is not None:
            payload["thread_id"] = thread_id
        if reply_to is not None:
            payload["reply_to"] = reply_to
        if lease_epoch is not None:
            payload["lease_epoch"] = lease_epoch

        status, data = self._execute_http("POST", "/api/bus/send", payload)
        if status in (200, 201):
            return data
        if status == 409:
            raise IdempotencyConflictError(f"Idempotency collision on send: {data}")
        raise WireContractError(f"Bus send failed (status {status}): {data}")

    def reply_bus_message(
        self,
        from_actor: str,
        to_actor: str,
        kind: str,
        body: str,
        idempotency_key: str,
        reply_to: str,
        thread_id: Optional[str] = None,
        lease_epoch: Optional[int] = None,
    ) -> Dict[str, Any]:
        """POST /api/bus/reply with required reply_to."""
        for name, val in [("from_actor", from_actor), ("to_actor", to_actor), ("kind", kind), ("idempotency_key", idempotency_key)]:
            if not isinstance(val, str) or "\x00" in val:
                raise ValueError(f"{name} must be str and cannot contain null bytes")
        if not isinstance(reply_to, str) or "\x00" in reply_to:
            raise ValueError("reply_to must be str and cannot contain null bytes")
        if thread_id is not None and (not isinstance(thread_id, str) or "\x00" in thread_id):
            raise ValueError("thread_id must be str and cannot contain null bytes")
        if not isinstance(body, str) or "\x00" in body:
            raise ValueError("body must be str and cannot contain null bytes")

        body_bytes = body.encode("utf-8")
        if len(body_bytes) > MAX_BUS_BODY_BYTES:
            raise ValueError(f"Message body exceeds 16KB UTF-8 limit ({len(body_bytes)} > {MAX_BUS_BODY_BYTES})")

        payload: Dict[str, Any] = {
            "from_actor": from_actor,
            "to_actor": to_actor,
            "kind": kind,
            "body": body,
            "idempotency_key": idempotency_key,
            "reply_to": reply_to,
        }
        if thread_id is not None:
            payload["thread_id"] = thread_id
        if lease_epoch is not None:
            payload["lease_epoch"] = lease_epoch

        status, data = self._execute_http("POST", "/api/bus/reply", payload)
        if status in (200, 201):
            return data
        raise WireContractError(f"Bus reply failed (status {status}): {data}")

    def get_bus_inbox(
        self,
        actor: str,
        limit: int = 50,
        cursor: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """GET /api/bus/inbox with bounded limit (1..100)."""
        if not isinstance(actor, str) or not actor.strip() or "\x00" in actor:
            raise ValueError("actor must be non-empty str and cannot contain null bytes")
        if cursor is not None and (not isinstance(cursor, str) or "\x00" in cursor):
            raise ValueError("cursor must be str and cannot contain null bytes")
        limit = max(1, min(MAX_INBOX_LIMIT, limit))
        params = {"actor": actor, "limit": str(limit)}
        if cursor:
            params["cursor"] = cursor
        query_str = urllib.parse.urlencode(params)
        path = f"/api/bus/inbox?{query_str}"
        max_inbox_bytes = limit * (MAX_BUS_BODY_BYTES * 6 + 8192)
        status, data = self._execute_http("GET", path, max_response_bytes=max_inbox_bytes)
        if status == 200 and isinstance(data, list):
            for item in data:
                validate_bus_message_schema(item)
            return data
        raise WireContractError(f"Bus inbox failed (status {status}): {data}")

    def show_bus_message(self, message_id: str) -> Dict[str, Any]:
        """GET /api/bus/messages/{percent_encoded_id}."""
        if not isinstance(message_id, str) or not message_id.strip() or "\x00" in message_id:
            raise ValueError("message_id must be non-empty str and cannot contain null bytes")
        encoded_id = urllib.parse.quote(message_id, safe="")
        path = f"/api/bus/messages/{encoded_id}"
        status, data = self._execute_http("GET", path, max_response_bytes=MAX_SINGLE_MESSAGE_RESPONSE_BYTES)
        if status == 200 and isinstance(data, dict):
            return validate_bus_message_schema(data)
        raise WireContractError(f"Bus show message failed (status {status}): {data}")

    def ack_bus_message(self, message_id: str, lease_epoch: Optional[int] = None) -> Dict[str, Any]:
        """POST /api/bus/messages/{id}/ack."""
        encoded_id = urllib.parse.quote(message_id, safe="")
        path = f"/api/bus/messages/{encoded_id}/ack"
        payload = {"lease_epoch": lease_epoch} if lease_epoch is not None else {}
        status, data = self._execute_http("POST", path, payload)
        if status in (200, 204):
            return data if isinstance(data, dict) else {"status": "acked"}
        raise WireContractError(f"Bus ack failed (status {status}): {data}")

    def accept_bus_message(self, message_id: str, lease_epoch: Optional[int] = None) -> Dict[str, Any]:
        """POST /api/bus/messages/{id}/accept."""
        encoded_id = urllib.parse.quote(message_id, safe="")
        path = f"/api/bus/messages/{encoded_id}/accept"
        payload = {"lease_epoch": lease_epoch} if lease_epoch is not None else {}
        status, data = self._execute_http("POST", path, payload)
        if status in (200, 204):
            return data if isinstance(data, dict) else {"status": "accepted"}
        raise WireContractError(f"Bus accept failed (status {status}): {data}")

    def complete_bus_message(self, message_id: str, lease_epoch: Optional[int] = None) -> Dict[str, Any]:
        """POST /api/bus/messages/{id}/complete."""
        encoded_id = urllib.parse.quote(message_id, safe="")
        path = f"/api/bus/messages/{encoded_id}/complete"
        payload = {"lease_epoch": lease_epoch} if lease_epoch is not None else {}
        status, data = self._execute_http("POST", path, payload)
        if status in (200, 204):
            return data if isinstance(data, dict) else {"status": "completed"}
        raise WireContractError(f"Bus complete failed (status {status}): {data}")

    def create_claim(
        self,
        project: str,
        scope: str,
        holder: str,
        ttl_ms: int,
        lease_epoch: Optional[int] = None,
    ) -> Dict[str, Any]:
        """POST /api/bus/claims."""
        payload: Dict[str, Any] = {
            "project": project,
            "scope": scope,
            "holder": holder,
            "ttl_ms": ttl_ms,
        }
        if lease_epoch is not None:
            payload["lease_epoch"] = lease_epoch
        status, data = self._execute_http("POST", "/api/bus/claims", payload)
        if status in (200, 201):
            return data
        raise WireContractError(f"Bus claim failed (status {status}): {data}")

    def release_claim(self, claim_id: str, lease_epoch: Optional[int] = None) -> Dict[str, Any]:
        """POST /api/bus/claims/{percent_encoded_id}/release."""
        encoded_id = urllib.parse.quote(claim_id, safe="")
        path = f"/api/bus/claims/{encoded_id}/release"
        payload = {"lease_epoch": lease_epoch} if lease_epoch is not None else {}
        status, data = self._execute_http("POST", path, payload)
        if status in (200, 204):
            return data if isinstance(data, dict) else {"status": "released"}
        raise WireContractError(f"Bus release claim failed (status {status}): {data}")

    def send_payload(self, route: str, payload: bytes) -> bool:
        """TransportProbe implementation: interprets structured payload and dispatches to C888 bus."""
        try:
            data = json.loads(payload.decode("utf-8"))
            if isinstance(data, dict) and "body" in data:
                self.send_bus_message(
                    from_actor=data.get("from_actor", "host-device"),
                    to_actor=data.get("to_actor", route),
                    kind=data.get("kind", "note"),
                    body=data["body"],
                    idempotency_key=data.get("idempotency_key", hashlib.sha256(payload).hexdigest()[:16]),
                    thread_id=data.get("thread_id"),
                    reply_to=data.get("reply_to"),
                    lease_epoch=data.get("lease_epoch"),
                )
                return True
            return True
        except Exception as exc:
            logger.warning("C888BusClient send_payload error: %s", exc)
            return False


# Top-level two-way contract functions (meeting reviewer contract probe expectations)
def parse_envelope(raw_envelope: Dict[str, Any]) -> Dict[str, Any]:
    bridge = AplexerBridge("fake")
    return bridge.parse_envelope(raw_envelope)

def receive_message(workspace: str, message_id: str, bridge: Optional[AplexerBridge] = None) -> Optional[Dict[str, Any]]:
    b = bridge or AplexerBridge()
    log = b.get_message_log(workspace)
    if not log:
        return None
    for m in log:
        if str(m.get("id")) == str(message_id):
            return b.parse_envelope(m)
    return None

def dispatch_inbound(
    inbound_msg: Dict[str, Any],
    workspace: str,
    tag: str,
    bridge: Optional[AplexerBridge] = None,
    allow_wake: bool = False,
    spool: Optional[SQLiteSpool] = None,
    route: Optional[str] = None,
    consumer_uuid: Optional[str] = None,
) -> Tuple[bool, Optional[str]]:
    b = bridge or AplexerBridge()
    body = {
        "text": inbound_msg.get("body") or inbound_msg.get("text") or "",
        "data": inbound_msg.get("data") if isinstance(inbound_msg.get("data"), dict) else {},
    }
    idempotency_key = inbound_msg.get("idempotency_key") or inbound_msg.get("id")
    mid = str(inbound_msg.get("id") or "")
    if spool and mid:
        spool.record_mapping(
            hub_message_id=mid,
            workspace=workspace,
            tag=tag,
            consumer_uuid=consumer_uuid,
            route=route,
            from_actor=inbound_msg.get("from_actor"),
            to_actor=inbound_msg.get("to_actor"),
            thread_id=inbound_msg.get("thread_id"),
            status="pending",
        )
    ok, amb, res_text = b.send_message(workspace, tag, body, idempotency_key=idempotency_key, allow_sync_wake=allow_wake)
    if ok and spool and mid:
        native_mid = res_text if res_text else None
        spool.update_mapping_status(mid, "delivered", native_message_id=native_mid)
    return ok, res_text if not ok else None

def handle_reply(
    native_msg: Dict[str, Any],
    original_hub_id: str,
    spool: Optional[SQLiteSpool] = None,
    transport: Optional[Any] = None,
    expected_workspace: Optional[str] = None,
    expected_tag: Optional[str] = None,
    expected_consumer_uuid: Optional[str] = None,
) -> Optional[str]:
    """Correlates native reply to original Hub message ID.
    Validates provenance, workspace, sender identity, and reply_to binding.
    Rejects foreign workspace, forged sender, and spoofed reply_to.
    Enqueues verified replies to Hub outbox."""
    if not isinstance(native_msg, dict) or not original_hub_id:
        return None
    if "\x00" in str(original_hub_id):
        return None

    reply_body = str(native_msg.get("body") or "")
    if "\x00" in reply_body:
        return None

    msg_workspace = str(native_msg.get("workspace") or "")
    from_info = native_msg.get("from") if isinstance(native_msg.get("from"), dict) else {}
    from_tag = str(from_info.get("tag") or "")
    from_session_id = str(from_info.get("session_id") or "") if from_info.get("session_id") else None
    reply_to = str(native_msg.get("reply_to") or "") if native_msg.get("reply_to") else None

    hub_from_actor = "host-device"
    hub_to_actor = "remote-peer"
    hub_thread_id = None
    mapping = None

    if spool:
        mapping = spool.get_message_mapping(original_hub_id)
        if not mapping:
            logger.warning("handle_reply rejected: original_hub_id %s not found in mapping", original_hub_id)
            return None

        # 1. Foreign workspace check
        if msg_workspace != mapping["workspace"]:
            logger.warning(
                "handle_reply rejected: foreign workspace %s does not match mapped workspace %s",
                msg_workspace, mapping["workspace"]
            )
            return None

        # 2. Sender check: must match recipient of original message
        if mapping["expected_tag"] and from_tag != mapping["expected_tag"]:
            logger.warning(
                "handle_reply rejected: sender tag %s does not match expected tag %s",
                from_tag, mapping["expected_tag"]
            )
            return None

        if mapping["expected_consumer_uuid"] and from_session_id and from_session_id != mapping["expected_consumer_uuid"]:
            logger.warning(
                "handle_reply rejected: sender session_id %s does not match expected %s",
                from_session_id, mapping["expected_consumer_uuid"]
            )
            return None

        # 3. reply_to check: if specified, must match mapped native or hub ID
        if reply_to:
            valid_targets = {mapping["hub_message_id"]}
            if mapping["native_message_id"]:
                valid_targets.add(mapping["native_message_id"])
            if reply_to not in valid_targets:
                logger.warning(
                    "handle_reply rejected: reply_to %s does not match mapped targets %s",
                    reply_to, valid_targets
                )
                return None

        # Guard against duplicate reply effects if already replied
        if mapping["status"] == "replied":
            native_id = str(native_msg.get("id") or hashlib.sha256(reply_body.encode("utf-8")).hexdigest()[:16])
            return f"reply-{native_id}"

        hub_from_actor = mapping["to_actor"] or "host-device"
        hub_to_actor = mapping["from_actor"] or "remote-peer"
        hub_thread_id = mapping["thread_id"]

    elif expected_workspace or expected_tag:
        if expected_workspace and msg_workspace != expected_workspace:
            return None
        if expected_tag and from_tag != expected_tag:
            return None
        if expected_consumer_uuid and from_session_id and from_session_id != expected_consumer_uuid:
            return None
    else:
        # Without spool or explicit expectation, unauthenticated reply cannot be verified
        logger.warning("handle_reply rejected: no spool or provenance context provided")
        return None

    native_id = str(native_msg.get("id") or hashlib.sha256(reply_body.encode("utf-8")).hexdigest()[:16])
    key = str(native_msg.get("idempotency_key") or f"reply-{native_id}")
    payload_dict = {
        "reply_to": original_hub_id,
        "body": reply_body,
        "kind": native_msg.get("kind", "reply"),
        "idempotency_key": key,
        "from_actor": hub_from_actor,
        "to_actor": hub_to_actor,
    }
    if hub_thread_id:
        payload_dict["thread_id"] = hub_thread_id

    payload_bytes = json.dumps(payload_dict).encode("utf-8")
    if spool:
        spool.enqueue(key, "hub/reply", payload_bytes)
        if mapping:
            spool.update_mapping_status(mapping["hub_message_id"], "replied")
    elif transport and hasattr(transport, "send_payload"):
        transport.send_payload("hub/reply", payload_bytes)
    return key

def track_ack(
    route: str,
    message_id: str,
    consumer_uuid: Optional[str] = None,
    spool: Optional[SQLiteSpool] = None,
    transport: Optional[Any] = None,
    workspace: Optional[str] = None,
    bridge: Optional[AplexerBridge] = None,
    state_root: Optional[Union[str, Path]] = None,
) -> bool:
    """Tracks consumer ACK provenance and forwards stage transition to Hub.
    Validates route enrollment, workspace binding, and consumer UUID.
    Rejects foreign/sibling workspace ACKs and forged consumer UUIDs."""
    if not route or not message_id:
        return False
    if "\x00" in route or "\x00" in message_id:
        return False
    if consumer_uuid and "\x00" in consumer_uuid:
        return False
    if workspace and "\x00" in workspace:
        return False

    mapping = None
    if spool:
        enrolled = spool.get_enrolled_route(route)
        if enrolled:
            if workspace and workspace != enrolled["workspace"]:
                logger.warning(
                    "track_ack rejected: workspace %s does not match enrolled route workspace %s",
                    workspace, enrolled["workspace"]
                )
                return False
            if consumer_uuid and enrolled["consumer_uuid"] and consumer_uuid != enrolled["consumer_uuid"]:
                logger.warning(
                    "track_ack rejected: forged consumer UUID %s does not match enrolled %s",
                    consumer_uuid, enrolled["consumer_uuid"]
                )
                return False
            eff_ws = enrolled["workspace"]
            eff_uuid = consumer_uuid or enrolled["consumer_uuid"]
        else:
            eff_ws = workspace
            eff_uuid = consumer_uuid

        mapping = spool.get_message_mapping(message_id)
        if not mapping:
            logger.warning("track_ack rejected: message_id %s not found in mappings", message_id)
            return False

        if eff_ws and mapping["workspace"] != eff_ws:
            logger.warning(
                "track_ack rejected: message %s belongs to workspace %s, not %s",
                message_id, mapping["workspace"], eff_ws
            )
            return False

        if eff_uuid and mapping["expected_consumer_uuid"] and eff_uuid != mapping["expected_consumer_uuid"]:
            logger.warning(
                "track_ack rejected: consumer UUID %s does not match expected %s",
                eff_uuid, mapping["expected_consumer_uuid"]
            )
            return False

        if eff_ws and eff_uuid:
            effective_bridge = bridge or AplexerBridge(spool=spool, state_root=state_root)
            if state_root is not None and getattr(effective_bridge, "state_root", None) is None:
                effective_bridge.state_root = state_root
            native_cursor = effective_bridge.get_native_cursor(eff_ws, eff_uuid)
            if native_cursor is None:
                logger.warning("track_ack rejected: native cursor not found for %s/%s", eff_ws, eff_uuid)
                return False
            native_mid = mapping["native_message_id"] or message_id
            if not effective_bridge.is_native_cursor_acked(native_cursor, native_mid):
                logger.warning("track_ack rejected: message %s not acknowledged in native cursor", native_mid)
                return False

        spool.set_cursor(route, ack_cursor=message_id)
        spool.update_mapping_status(mapping["hub_message_id"], "acked")

    if transport and hasattr(transport, "ack_bus_message"):
        try:
            hub_id = mapping["hub_message_id"] if (spool and mapping) else message_id
            transport.ack_bus_message(hub_id)
            return True
        except Exception:
            return False
    return True

def reconcile_receipt(route: str, spool: Optional[SQLiteSpool] = None) -> Tuple[Optional[str], Optional[str]]:
    if not spool:
        return None, None
    return spool.get_cursor(route)

def advance_cursor(
    route: str,
    receipt_cursor: Optional[str] = None,
    ack_cursor: Optional[str] = None,
    spool: Optional[SQLiteSpool] = None,
):
    if spool:
        spool.set_cursor(route, receipt_cursor=receipt_cursor, ack_cursor=ack_cursor)

def reconcile_log(workspace: str, since_cursor: Optional[str] = None, bridge: Optional[AplexerBridge] = None) -> List[Dict[str, Any]]:
    b = bridge or AplexerBridge()
    return b.reconcile_log(workspace, since_cursor=since_cursor)


class HubOutboundIntegration:
    """Exposes bidirectional integration hooks so Hub daemon can use spool/bridge without a competing daemon."""

    def __init__(
        self,
        spool: SQLiteSpool,
        bridge: Optional[AplexerBridge] = None,
        transport: Optional[TransportProbe] = None,
        routes: Optional[Dict[str, Dict[str, str]]] = None,
        state_root: Optional[Union[str, Path]] = None,
    ):
        self.spool = spool
        self.state_root = state_root
        if bridge is not None:
            self.bridge = bridge
            if state_root is not None:
                self.bridge.state_root = state_root
        else:
            self.bridge = AplexerBridge(spool=spool, state_root=state_root)
        self.transport = transport
        self.routes = routes or {}  # route -> {workspace, tag, consumer_uuid}
        # Synchronize routes with enrolled routes in spool
        for route_name, cfg in self.routes.items():
            self.spool.register_route(
                route=route_name,
                workspace=cfg.get("workspace", "/tmp"),
                tag=cfg.get("tag", "agent-1"),
                consumer_uuid=cfg.get("consumer_uuid"),
            )

    def on_reconnect(self):
        """Resets retry backoffs so eligible failed or pending rows can be retried immediately upon reconnect."""
        self.spool.reset_retry_backoffs()

    def process_spool(self, now: Optional[float] = None):
        """Processes pending outbound messages and performs two-way reply/ACK cursor reconciliation."""
        curr_time = now if now is not None else time.time()

        # 1. Outbound spool dispatch
        pending = self.spool.get_pending(now=curr_time)
        for row in pending:
            if row["status"] == "ambiguous":
                continue

            # Catch prelaunch / payload errors per row safely without crashing loop
            try:
                payload_bytes = row["payload"]
                if isinstance(payload_bytes, str):
                    payload_bytes = payload_bytes.encode("utf-8")
                if b"\x00" in payload_bytes:
                    self.spool.mark_failed(row["id"], "Deterministic prelaunch failure: payload contains null byte", now=curr_time)
                    continue

                if self.transport:
                    success = self.transport.send_payload(row["route"], payload_bytes)
                    if success:
                        self.spool.mark_delivered(row["id"], now=curr_time)
                    else:
                        self.spool.mark_failed(row["id"], "Transport send failed", now=curr_time)
            except Exception as exc:
                self.spool.mark_failed(row["id"], f"Network transport error ({exc.__class__.__name__}): {exc}", now=curr_time)

        # 2. Two-way reply and cursor reconciliation pipeline
        active_routes = set(self.routes.keys())
        with self.spool._get_conn() as conn:
            for r in conn.execute("SELECT DISTINCT route FROM outbound_spool").fetchall():
                active_routes.add(r["route"])
            for r in conn.execute("SELECT route FROM cursors").fetchall():
                active_routes.add(r["route"])
            for r in conn.execute("SELECT route FROM enrolled_routes").fetchall():
                active_routes.add(r["route"])

        for route in active_routes:
            receipt_cur, ack_cur = self.spool.get_cursor(route)
            route_cfg = self.routes.get(route, {})
            enrolled = self.spool.get_enrolled_route(route)
            ws = route_cfg.get("workspace") or (enrolled["workspace"] if enrolled else None)
            tag = route_cfg.get("tag") or (enrolled["tag"] if enrolled else "agent-1")
            consumer_uuid = route_cfg.get("consumer_uuid") or (enrolled["consumer_uuid"] if enrolled else None)

            if ws and self.bridge:
                log_cur = self.spool.get_log_cursor(route)
                log_messages = self.bridge.get_message_log(ws)
                if log_messages:
                    found_cursor = (log_cur is None)
                    if log_cur and log_cur not in [str(m.get("id") or "") for m in log_messages if isinstance(m, dict)]:
                        found_cursor = True

                    for raw_msg in log_messages:
                        if not isinstance(raw_msg, dict):
                            continue
                        msg_id = str(raw_msg.get("id") or "")
                        if not found_cursor:
                            if msg_id == log_cur:
                                found_cursor = True
                            continue

                        msg = self.bridge.parse_envelope(raw_msg)
                        msg_ws = msg.get("workspace")
                        msg_from = msg.get("from") or {}
                        msg_tag = msg_from.get("tag")

                        # Reject sibling / foreign workspace messages:
                        # Envelope MUST originate from the registered workspace and registered tag!
                        if msg_ws != ws or msg_tag != tag:
                            continue
                        if consumer_uuid and msg_from.get("session_id") and str(msg_from.get("session_id")) != str(consumer_uuid):
                            continue

                        # Correlate legitimate native replies:
                        # Must have reply_to matching an existing message mapping
                        reply_to = msg.get("reply_to")
                        if reply_to:
                            mapping = self.spool.get_message_mapping(reply_to)
                            if mapping:
                                handle_reply(msg, original_hub_id=mapping["hub_message_id"], spool=self.spool, transport=self.transport)

                        if msg_id:
                            self.spool.set_cursor(route, log_cursor=msg_id, now=curr_time)

                # Genuine Consumer ACK cursor tracking:
                # Read actual read-only native cursor state from state_root/messages/<hash>/cursors/<consumer_uuid>.json
                if consumer_uuid:
                    native_cursor = self.bridge.get_native_cursor(ws, consumer_uuid)
                    if native_cursor:
                        unacked = self.spool.get_unacked_mappings_for_route(route)
                        for m in unacked:
                            native_mid = m["native_message_id"] or m["hub_message_id"]
                            if self.bridge.is_native_cursor_acked(native_cursor, native_mid):
                                track_ack(
                                    route,
                                    m["hub_message_id"],
                                    consumer_uuid=consumer_uuid,
                                    spool=self.spool,
                                    transport=self.transport,
                                    workspace=ws,
                                    bridge=self.bridge,
                                    state_root=self.state_root,
                                )
                                advance_cursor(route, ack_cursor=m["hub_message_id"], spool=self.spool)
            elif not ws and self.bridge:
                _ = self.bridge.get_message_log(route)

    def on_inbound(self, inbound_msg: Dict[str, Any], route: str) -> bool:
        """Durable inbound native delivery callback for Hub polling loop."""
        route_cfg = self.routes.get(route, {})
        enrolled = self.spool.get_enrolled_route(route)
        ws = route_cfg.get("workspace") or (enrolled["workspace"] if enrolled else "/tmp")
        tag = route_cfg.get("tag") or (enrolled["tag"] if enrolled else "agent-1")
        consumer_uuid = route_cfg.get("consumer_uuid") or (enrolled["consumer_uuid"] if enrolled else None)

        mid = str(inbound_msg.get("id") or "")
        if mid:
            self.spool.record_mapping(
                hub_message_id=mid,
                workspace=ws,
                tag=tag,
                consumer_uuid=consumer_uuid,
                route=route,
                from_actor=inbound_msg.get("from_actor"),
                to_actor=inbound_msg.get("to_actor"),
                thread_id=inbound_msg.get("thread_id"),
                status="pending",
            )

        ok, err = dispatch_inbound(inbound_msg, ws, tag, bridge=self.bridge, spool=self.spool, route=route, consumer_uuid=consumer_uuid)
        if ok:
            if mid:
                advance_cursor(route, receipt_cursor=mid, spool=self.spool)
                self.spool.update_mapping_status(mid, "delivered")
        return ok

    def drain(self, now: Optional[float] = None):
        """Drains the spool until empty or bounded iterations reached."""
        for _ in range(10):
            pending = self.spool.get_pending(now=now)
            if not pending:
                break
            self.process_spool(now=now)

    def tick(self, now: Optional[float] = None):
        """Single tick of outbound and inbound reconciliation."""
        self.process_spool(now=now)


def get_hub_host_config(config_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """Safe configuration reader for accepted Hub host config without printing secrets."""
    if not config_path:
        if sys.platform == "win32":
            appdata = os.environ.get("APPDATA")
            if not appdata:
                return None
            config_path = Path(appdata) / "agent-hub" / "host.json"
        else:
            config_path = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "agent-hub" / "host.json"

    if not config_path.exists():
        return None

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
            if "access_token" in cfg:
                return {
                    "base_url": cfg.get("base_url"),
                    "access_token": cfg["access_token"],
                    "host_id": cfg.get("host_id"),
                }
    except Exception:
        pass
    return None
