# Agent Hub Outbound Host Adapter Kit

This kit implements the host-side outbound components for the `agent-hub` M3 cross-machine bus integration, directly serving the AC59 native two-host contest prerequisites.

## Goal: Outbound No-SSH Bus

The objective is to replace the previous inbound-SSH bus adapter with an outbound-only polling/WebSocket host daemon. The host machine connects to Cloudflare Agent Hub to claim messages and send replies without requiring inbound network access or an SSH server.

## Contract Pins & Qualification

- **Proposed C888 Wire Contract Pin**: `c888fd9c65d5a0aca26667e6eccb2c278b5334da`
- **Accepted Hub Main Pin**: `d86c76b35d41d63871a6282bdd7bfc2ff723a6fd` (M2 only; does not serve M3 bus)
- **Qualification**: Guarded under `CANDIDATE_CONTRACT_ONLY = True` and `UNAGREED_WIRE_PROTOCOL_VERSION = "v1-draft"`. No runtime advertising or device job execution occurs until final Hub acceptance and owner handoff.

## Architecture & Components

The implementation in `adapters/hub_outbound.py` consists of four primary components:

### 1. `SQLiteSpool`
- **Durable Storage & Atomic DB Transactions**: Uses WAL mode SQLite (`outbound_spool`, `spool_tombstones`, `delivery_intents`, `message_mappings`, `cursors`, `enrolled_routes`, `spool_metadata`). All mutating operations (`register_route`, `record_mapping`, `update_mapping_status`, `record_intent`, `update_intent_status`, `set_cursor`, `mark_delivered`, `mark_ambiguous`, `mark_failed`, `enqueue`) execute inside atomic `BEGIN IMMEDIATE` transactions with transactional rollback on capacity breach or errors.
- **Connection Lifecycle & Inherited PRAGMAs**: Every SQLite connection created via `_create_raw_conn()` / `_get_connection()` strictly enforces connection-level PRAGMAs:
  - `PRAGMA synchronous = NORMAL` (1)
  - `PRAGMA journal_size_limit = 65536`
  - `PRAGMA wal_autocheckpoint = 100`
  - `PRAGMA max_page_count = <max_pages>`
  Connections are guaranteed to be closed upon exiting context managers via explicit `try ... finally: conn.close()`.
- **Physical vs. Logical Bounded Storage Policy**:
  - **Logical Budgets**: Configurable `max_storage_bytes` (default 16 MiB) for cumulative payload size, and `max_payload_bytes` (default 1 MiB) per item.
  - **Physical Budgets & Minimum Reserve**: Bounded default `DEFAULT_MAX_PHYSICAL_BYTES = 16 MiB` and `DEFAULT_MAX_PAGES = 4096`. Validated upfront against minimum required SQLite schema footprint: `MIN_PHYSICAL_SCHEMA_BYTES = 114688` (28 pages @ 4096 bytes). Configurations with impossible budgets (< 114688 bytes, < 28 pages, negative values, or `max_payload_bytes > max_storage_bytes`) are rejected upfront with `ValueError`.
  - **Pre-Transaction Physical WAL Headroom Checking**: `_assert_capacity_available` evaluates physical storage against `max_physical_bytes` before executing mutations, anticipating WAL frame write growth (4120 bytes per page + B-tree/index overhead) to prevent transaction growth before physical budget is crossed, preserving queued work and zero budget breaches even under held-reader contention.
  - **Physical WAL Bounds & Non-Blocking Checkpointing**: `checkpoint_and_reclaim()` sets `PRAGMA busy_timeout = 100` before attempting `PRAGMA wal_checkpoint(TRUNCATE)` and gracefully falls back to `PRAGMA wal_checkpoint(PASSIVE)` if active readers hold snapshots, preventing writer stalls or 30-second delays.
  - **All-Table Record Caps**: Row caps enforced across all spool tables: `DEFAULT_MAX_TOMBSTONES = 10000`, `DEFAULT_MAX_MAPPINGS = 10000`, `DEFAULT_MAX_INTENTS = 10000`, and `DEFAULT_MAX_TOTAL_RECORDS = 50000`.
  - **Strict UTF-8 Metadata Input Bounds**: All metadata strings are validated pre-insertion (`validate_metadata_str`): route/tag/status <= 256 bytes, workspace path <= 4096 bytes, payload text/error text <= 65536 bytes, with zero tolerance for embedded NUL (`\x00`) bytes.
- **Persistent Anti-Replay Semantics Across All Ingress**:
  - **Versioned Age-Authenticated Key Policy**: Versioned keys formatted as `v1:<issuance_timestamp>:<token>`. `parse_versioned_key_issuance` strictly validates finite non-negative numbers and rejects future-invalid timestamps (> now + 60s). Nonfinite keys (`v1:nan:...`, `v1:inf:...`) are rejected upfront across all ingress (`enqueue`, `record_intent`, `record_mapping`, `validate_native_args`). Pruning tombstones by age updates the `oldest_tombstone_cutoff` watermark in `spool_metadata`. Any replay of a versioned key with issuance timestamp older than `oldest_tombstone_cutoff` is rejected across ALL ingress points (`enqueue` returns `False`, `record_mapping` and `record_intent` raise `IdempotencyConflictError`).
  - **Legacy Opaque Keys Safe Bounded Hold Policy**: Legacy unversioned opaque keys do not have timestamps and cannot be safely pruned by age without risking replay. Under safe bounded hold, opaque keys in `spool_tombstones` are never evicted by age alone. When tombstone table cap is reached, excess opaque keys are recorded in the `evicted_opaque_keys` ledger in `spool_metadata`. Subsequent replays of cap-evicted legacy keys return `True` (stable idempotent outcome) without inserting into `outbound_spool` -> guaranteeing ZERO duplicate transport sends.
- **Terminal-Only Metadata Pruning**:
  - Only terminal delivery intents (`status = 'sent'`) and terminal message mappings (`status IN ('acked', 'replied')`) are eligible for age-based pruning.
  - Pending, ambiguous, or in-flight intents and mappings are strictly preserved.
- **Fail-Closed Capacity Preservation**:
  - If capacity limits (payload bytes, physical bytes, page count, or record count) are breached, mutating methods raise `SpoolStorageLimitReached` and roll back atomically.
  - Existing pending/ambiguous work, cursors, and original retry keys are preserved intact; no wholesale table wipes or database resets ever occur.
- **Collision Detection & Idempotency**:
  - Re-enqueuing with identical key, route, and payload returns `True` (idempotent replay, including against active rows, tombstones, and evicted opaque keys).
  - Re-enqueuing with identical key but conflicting route or conflicting payload returns `False` (atomic collision rejection).
- **Injectable Clock & Reconnect Retry**: `get_pending()` supports clock injection (`now: Optional[float]`) and backoff. `reset_retry_backoffs()` allows immediate retry upon explicit reconnect triggers.

### 2. `AplexerBridge` & Genuine Sender Discovery
- **Genuine Sender Discovery Contract (`--workspace`)**:
  - Per Rust specification (`cloudflare-aplexer-protocol/src/bin/aplexer/message_routing.rs`), cross-workspace delivery using `--workspace` strictly FORBIDS `--from` and discovers genuine session identity via `current_session_sender`.
  - `AplexerBridge.send_message` strictly executes `["message", "send", "--workspace", ..., "--to", ..., "--json", "--data", <JSON>, "--", <TEXT>]` without `--from`.
  - If sender context is unbound/unknown, delivery fails closed truthfully without `--from`/env impersonation.
  - Discovered genuine sender context is verified end-to-end via an executable Rust-shaped CLI fixture.
- **Strict Argv Execution with Literal `--` Separator**: Executes `aplexer` commands strictly via `subprocess.run` with list arguments (no shell interpolation). All positional `<TEXT>` arguments are preceded by the literal `--` delimiter, ensuring hostile texts starting with `--pane`, `--all`, or other flags are strictly parsed as positional text rather than CLI flags.
- **Pre-Effect Input & NUL Byte Validation**: `validate_native_args` deterministically validates all arguments (`workspace`, `tag`, `text`, `idempotency_key`, `data` keys/values) against embedded NUL bytes (`\x00` or `\u0000`), string types, nonfinite timestamps, and length bounds *before* invoking `subprocess.run` and *before* writing to intent persistence.
- **Deterministic vs Ambiguous Failure Handling**: Prelaunch errors (such as `ValueError` or `OSError` from embedded NUL bytes) are safely caught and return deterministic exit code 2, failing the row safely without crashing the dispatch loop or poisoning subsequent rows.
- **Reserved Provenance Keys Protection**: Untrusted user-supplied `data` dictionary keys cannot overwrite trusted provenance keys (`bridge_id`, `idempotency_key`, `workspace`, `tag`, `session_id`, `machine_id`, `origin`, `recipient`, `provenance`).
- **Exact Native Log Reconciliation**: Delivery intent is persisted in `delivery_intents` before process execution. If process execution encounters an ambiguous failure (e.g., IPC disconnect or timeout), `send_message` inspects `get_message_log()`. Only positive same-key evidence validating exact workspace, recipient tag, target session UUID, discovered sender context, body text, and a valid native message ID reconciles the intent to `sent`. Mismatches (differing body, recipient, workspace) or multiple matches remain held as ambiguous with detailed diagnostics and zero blind resends.
- **Safe Wake Guard**: Native wake is attempted only if the target session is positively verified idle and empty. If unsupported or unverified, wake is explicitly deferred durably, retaining the message in the mailbox inbox without raw PTY keystroke injection.

### 3. `C888BusClient`
- **Proposed Wire Endpoints**: Implements `/api/bus/send`, `/api/bus/reply`, `/api/bus/inbox`, `/api/bus/messages/{id}` (show), `/api/bus/messages/{id}/ack`, `/api/bus/messages/{id}/accept`, `/api/bus/messages/{id}/complete`, and `/api/bus/claims`.
- **Default-Closed C888 Runtime Gate**: Proposed wire contract client defaults to closed (`allow_loopback_http=False`, `fixture_opt_in=False`). Connecting requires HTTPS, and HTTP execution requires an explicit candidate/fixture opt-in (`fixture_opt_in=True` or `allow_loopback_http=True`) or accepted Hub owner handoff before executing network operations.
- **Per-Client Deny-Redirect Opener**: Built with `DenyRedirectHandler` refusing HTTP redirects (301, 302, 303, 307, 308) fail-closed, preventing cross-origin or redirect credential forwarding (Authorization header leakage).
- **Bounded HTTP Response Reads**: All response reads on success (200), token refresh (401 retry), and error paths are strictly bounded via `_read_bounded_response` before allocation, preventing memory exhaustion from unbounded servers.
- **Payload Bounds & Incoming Schema Validation**: Enforces the 16 KiB UTF-8 body cap (`MAX_BUS_BODY_BYTES = 16384`) on outgoing and incoming messages, validates schema fields, and rejects embedded NUL bytes and nonfinite timestamps.
- **Authentication**: Injects `Authorization: Bearer <token>` via injected token provider without logging credentials, and performs bounded retry upon HTTP 401.

### 4. `HubOutboundIntegration` & State Provenance
- **Route Enrollment & Pre-Effect Mapping**: Maintains `enrolled_routes` and `message_mappings` tables. Pre-dispatch mappings record `hub_message_id`, expected `workspace`, `expected_tag`, `expected_consumer_uuid`, and `thread_id` before effects occur.
- **Sibling & Foreign Workspace Forgery Protection (F1 / Check 3)**:
  - `handle_reply` verifies that incoming native replies originate from the exact enrolled workspace, match the expected recipient tag, match the session UUID, and correspond to mapped Hub thread/message IDs. Sibling or foreign workspace replies, unmapped IDs, or mismatched tags/UUIDs are rejected fail-closed (returns `None`), preventing outbox staging or cursor mutation.
  - Sibling workspaces posting chat messages with fake `kind: "ack"` or spoofed payload IDs are ignored.
- **Native Consumer Cursor Provenance & Layout**: `track_ack` verifies consumer receipts directly against the read-only native state tree adhering to the Rust producer specification (`cloudflare-aplexer-protocol`):
  - **State Root Resolution Precedence**: Configured `state_root` -> `APLEXER_STATE_DIR` (absolute or cwd-resolved) -> `XDG_STATE_HOME/aplexer` (must be absolute) -> `~/.local/state/aplexer`. State root is completely distinct from the runtime directory (`/tmp/aplexer-{uid}` or `XDG_RUNTIME_DIR`), with zero guessing or `.aplexer/` directory fallbacks.
  - **Workspace Canonicalization & 128-bit Key**: Exact raw Unix filesystem bytes hashed with SHA-256 (first 16 bytes / 128 bits hex) to yield `${state_root}/messages/<hash>`.
  - **`workspace.json` Reverse Mapping**: Strictly verified before reading cursors, confirming the directory maps back to the expected canonical workspace to prevent collision or aliasing.
  - **Consumer Cursor Path**: `${state_root}/messages/<hash>/cursors/<consumer_uuid>.json`.
  - **Bounded Read-Only Safety**: Opened non-blocking with `O_NOFOLLOW` refusing symlinks, verifying regular file type and enforcing the 64 KiB cap (`MAX_MAILBOX_STATE_BYTES`). Zero directory creation, zero writes, zero file locks from the Python reader probe. Atomic-rename compatible.
  - **Cursor Schema & Semantics**: Sparse `exceptions` list of exact acknowledged message IDs, plus legacy `acked_through` high-water mark scoped strictly to matching route mappings (no cross-workspace or cross-consumer inheritance).
  - **Fail-Closed Validation**: Missing files, mismatched reverse maps, path traversal attempts, non-canonical/malformed UUIDs, symlinks, non-regular files, or oversize files cleanly return `None` without crashing. Arbitrary API callers or sibling workspaces cannot forge ACKs for other agents.
- **Bidirectional Pipeline**: `process_spool()` handles pending outbound queue dispatch with per-row exception isolation (network errors mark the row failed without crashing the loop).
- **Two-Way Reply & ACK Tracking**: Actively calls `get_cursor()` and `get_message_log()`, correlates native replies matching `reply_to`, forwards consumer ACKs to Hub transport, and safely advances route cursors atomically via `set_cursor()`.
- **Exported Contract Functions**: Exposes `receive_message`, `dispatch_inbound`, `handle_reply`, `track_ack`, `reconcile_log`, `reconcile_receipt`, `advance_cursor`, and `parse_envelope`.

## Source Dependencies

- **Agent Hub (`~/git/agent-hub`)**: Provides core configuration (`host.json`), device login logic, and client interfaces.
- **Python 3.9+**: Standard library only (`sqlite3`, `json`, `subprocess`, `urllib.request`, `hashlib`).
- **Aplexer**: Rust native CLI for session listing and message mailboxes.

## Testing Status

> [!IMPORTANT]
> **Testing Scope & Physical Windows Execution: NOT_RUN**
> Real Windows execution of the Task Scheduler script (`windows-hub-host-task.ps1`) and daemon on physical Windows hardware (Win35/Laptop) has **NOT_RUN**. Testing is conducted via comprehensive Linux-based fixtures.

### Linux Windows-shaped Tests
We test the `hub_outbound.py` adapter natively using `unittest` and `pytest`:
- SQLite spool storage bounds: upfront validation rejecting impossible budgets (< 114,688 bytes or < 28 pages), physical size / page count / record count enforcement.
- Repeated delivery-retention cycles: bounded tombstones, terminal-only intent and mapping pruning, WAL journal truncation, and metadata watermarking.
- Capacity failure preservation: fail-closed admission rejecting overflow without wiping database or dropping unacked/ambiguous pending work.
- Idempotency & replay guarantees: same-key replays across restart/pruning, collision rejection on payload/route changes, zero duplicate effects on expired keys.
- Atomic concurrency & recovery: atomic `BEGIN IMMEDIATE` admission across concurrent connections, and reconnect/lost HTTP receipt stability.
- Reconnect backoff, clock injection, and loop resilience against transport exceptions.
- Strict argv construction, native intent persistence, and ambiguous IPC failure log reconciliation.
- Proposed C888 wire contract client loopback HTTP server fixture, 16KB body enforcement, HTTPS fail-closed, and 401 token refresh.
- End-to-end two-way reply correlation and cursor advancement.
- R8 defect verification suite (`TestR8VerificationDefectsAndContractHardening`): exact log reconciliation (mismatches held ambiguous; exact match sent), per-client deny-redirect opener (preventing credential leakage), bounded HTTP response reads across all branches, default-closed C888 runtime gate, body/schema validation (16KB cap), nonfinite/future versioned key rejection, and held-reader pre-transaction capacity check.

## Local Preview & Install Instructions

**1. Device Login**
Before running the daemon, the host logs into the Hub:
```bash
python -m agent_hub_host.cli login --base-url <url>
```
This browser login populates `%APPDATA%\agent-hub\host.json`.

**2. Task Scheduler Preview**
To preview what the Task Scheduler will configure without making any system changes:
```powershell
.\scripts\windows-hub-host-task.ps1
```

**3. Task Scheduler Install**
To install the logon task for the current interactive non-admin user:
```powershell
.\scripts\windows-hub-host-task.ps1 -Install
```
To remove the task cleanly:
```powershell
.\scripts\windows-hub-host-task.ps1 -Remove -ConfirmAction
```

## Remaining Hub M3 & Physical Evidence Handoff

The `HubOutboundIntegration` class is designed to be injected into the existing Agent Hub host daemon loop.
1. **Hub M3 Integration**: `agent-hub-head` needs to integrate the `HubOutboundIntegration` hooks into `host/agent_hub_host/agent.py` once the C888 wire contract is accepted.
2. **Physical Device Validation**: The Windows host task and Aplexer bridge must be genuinely run on physical Win35/Laptop hardware. Device-side ACK must only be accepted with authentic recipient device/consumer provenance.
