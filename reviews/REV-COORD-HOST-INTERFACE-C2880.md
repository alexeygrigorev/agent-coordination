# REV-COORD-HOST-INTERFACE-C2880 — Independent Code Review

Verdict: **ACCEPT**

- **Reviewer**: Distinct Independent Peer Reviewer for Product 4 (Cross-computer Agent Coordination)
- **Review Role**: Independent Peer Reviewer for task `coord-dashboard-launcher-hosts` (launcher task `t-coord-dashboard-launcher-hosts-c2880` / review task `t-coord-dashboard-launcher-hosts-review-c2880`)
- **Caller / Parent**: `764358a8-1b4e-49c6-845a-9b79bf3ba536`
- **Project**: Cross-computer Agent Coordination (`agent-coordination`)
- **Target Workspace**: `/home/alexey/git/agent-coordination`
- **Git Commit Baseline**: `30df32ae2bbcc47558556e03701e28bae4a10022`
- **Review Date**: 2026-10-06 (Europe/Berlin / CEST)

---

## 1. Evaluated Files & Scope of Changes

This independent review evaluated the implementation of host interface admission and event logging across two target files in `/home/alexey/git/agent-coordination`:

1. **`coordination/host_interface.py`** (381 lines)
   - SHA-256: `4382a6640b77ad5293cb0171745f1a8d8bece881bf44c22dd8aa1565d242a254`
   - **DeviceRegistry Allowlist Validation**: Integrates with `DeviceRegistry` to validate host/device IDs upon admission request (`_admit_host_task_impl` / `admit_host_task`). Fails closed by raising `UnknownDevice` if the target device is not present in the allowlist.
   - **Outbound SSH Client Routing & Security (`windows-desktop`)**:
     - Detects `device.outbound_ssh_only`.
     - Strictly enforces `session_id=None`, neutralizing synthetic session invention.
     - Strips or rejects credential inheritance via `reject_head_cred_inheritance`.
     - Routes execution to `hetzner-rmthz` (`execution_target = "hetzner-rmthz"`).
     - Dispatches via `delivery = "sessionless_worker_bus"`.
   - **Aplexer Host Resource Enforcement (`hetzner-rmthz`)**:
     - Detects `device.kind == DeviceKind.APLEXER_HOST`.
     - Validates memory limit against `MAX_MEMORY_MB = 1500`. Caps memory to `<= 1500M` (`min(parsed_mem, MAX_MEMORY_MB)`) and raises `GuardRejected` when `enforce_memory_limit=True` and memory exceeds 1500MB.
     - Dispatches via `delivery = "local_task_unit"` targeting local machine `hetzner-rmthz`.
   - **Atomic JSONL Host Event Logging**:
     - Implements `emit_host_event` writing to `host_events.jsonl` under advisory exclusive file lock (`fcntl.flock(f.fileno(), fcntl.LOCK_EX)`).
     - Appends structured records containing `event_id` (UUID4), `event_type`, `device_id`, `task_id`, `details`, `timestamp` (UTC ISO), and `recorded_at`.
   - **Structured Event Querying**:
     - Implements `query_host_events` with shared lock (`fcntl.flock(f.fileno(), fcntl.LOCK_SH)`), supporting field-level filtering on `event_type`, `device_id`, and `task_id`.

2. **`tests/test_host_interface.py`** (213 lines)
   - SHA-256: `aa87469ba6d5522526fd8459c34b819d852c02cac4bf12d9ba4ee940bcf55b17`
   - Comprehensive test suite covering positive, negative, security, and concurrency paths:
     - `test_admit_hetzner_host`: Memory capping (integer, string parsing e.g. "2G", low memory preservation, default), execution target verification, delivery mode verification.
     - `test_admit_windows_host`: Target routing to `hetzner-rmthz`, sessionless worker bus delivery, strict `session_id=None` enforcement.
     - `test_unknown_host_fails_closed`: Fail-closed gate throwing `UnknownDevice` on unregistered device IDs for both class and module-level methods.
     - `test_reject_head_cred_inheritance`: Stripping of `head.cred`, `head_cred`, `cred`, and nested credentials; rejection with `GuardRejected` when `reject_on_cred=True`.
     - `test_emit_and_query_host_events`: Atomic JSONL emission, UTC ISO timestamps, query filtering, and concurrent thread pool execution (5 concurrent threads emitting 25 events simultaneously under file locking).

---

## 2. Verification of Negative & Safety Cases

### 2.1. Unknown Host Fails Closed (`UnknownDevice`)
- **Requirement**: Any unregistered device ID must immediately fail closed with `UnknownDevice` and code `unknown_device`.
- **Implementation**:
  ```python
  device = self.registry.get(device_id)
  ```
  `DeviceRegistry.get(device_id)` queries internal allowlist index and raises `UnknownDevice(device_id)` on unknown keys.
- **Verification**:
  Calling `adm.admit_host_task("unregistered-laptop", "t1")` raises:
  ```
  UnknownDevice: unknown_device:unregistered-laptop (code="unknown_device", device_id="unregistered-laptop")
  ```

### 2.2. Outbound SSH Host Sessionless Enforcement (`session_id=None`)
- **Requirement**: Outbound SSH-only clients (e.g. `windows-desktop`) must never be assigned an aplexer session ID, even if supplied by the caller.
- **Implementation**:
  ```python
  if is_outbound:
      session_id = None
      if "session_id" in sanitized_payload:
          sanitized_payload["session_id"] = None
      execution_target = "hetzner-rmthz"
      delivery = "sessionless_worker_bus"
  ```
- **Verification**:
  Supplying `payload={"session_id": "invented-windows-session", "command": "test"}` yields `decision["session_id"] is None` and `decision["payload"]["session_id"] is None`.

### 2.3. Head Credential Rejection and Stripping (`GuardRejected`)
- **Requirement**: Prevent inheritance of head credentials into admitted worker payloads; strip credentials by default and reject when requested.
- **Implementation**:
  ```python
  def reject_head_cred_inheritance(payload: dict[str, Any], *, reject: bool = False) -> dict[str, Any]:
      has_head_cred = (
          "head.cred" in payload
          or "head_cred" in payload
          or "cred" in payload
          or (isinstance(payload.get("head"), dict) and "cred" in payload["head"])
      )
      if has_head_cred and reject:
          raise GuardRejected("head_cred_inheritance_rejected: forbidden credential inheritance")
      ...
  ```
- **Verification**:
  - With `reject_on_cred=False` (default sanitization): admitted payload strips `head.cred`, `head_cred`, and `cred` while retaining legitimate task fields (`job_name`, `agent_tag`).
  - With `reject_on_cred=True`: raises `GuardRejected("guard_rejected:head_cred_inheritance_rejected: forbidden credential inheritance")`.

### 2.4. Aplexer Host Memory Capping & Bounds (`<= 1500M`)
- **Requirement**: Enforce memory bound `<= 1500M` on aplexer hosts (`hetzner-rmthz`).
- **Implementation**:
  ```python
  parsed_mem = parse_memory_mb(requested_mem, default=MAX_MEMORY_MB)
  if enforce_memory_limit and parsed_mem > MAX_MEMORY_MB:
      raise GuardRejected(f"memory_limit_exceeded: {parsed_mem}MB exceeds {MAX_MEMORY_MB}MB")
  memory_mb = min(parsed_mem, MAX_MEMORY_MB)
  ```
- **Verification**:
  - Requested `4096` MB or `"2G"`: clamped to `1500` MB.
  - Requested `512` MB: preserved at `512` MB.
  - With `enforce_memory_limit=True` and `2000` MB: raises `GuardRejected("guard_rejected:memory_limit_exceeded: 2000MB exceeds 1500MB")`.

### 2.5. Atomic Concurrency on Event Emission
- **Requirement**: Multiple processes or threads emitting events must not interleave lines or corrupt `host_events.jsonl`.
- **Implementation**:
  `emit_host_event` locks the file descriptor with `fcntl.flock(f.fileno(), fcntl.LOCK_EX)` before writing and flushing.
- **Verification**:
  5 concurrent threads emitting 25 events via `ThreadPoolExecutor` produced exactly 25 properly formatted JSON records with zero line interleaving or truncation.

---

## 3. Test Execution Results & Command Output

### 3.1. Target Test Suite: `tests/test_host_interface.py`
Command:
```bash
python3 -c "import os, pytest, sys; os.chdir('/home/alexey/git/agent-coordination'); sys.exit(pytest.main(['tests/test_host_interface.py', '-v']))"
```
Output:
```
============================= test session starts ==============================
platform linux -- Python 3.12.3, pytest-9.1.1, pluggy-1.6.0
rootdir: /home/alexey/git/agent-coordination
configfile: pyproject.toml
plugins: anyio-4.12.1, opik-2.2.54
collecting ... collected 5 items

tests/test_host_interface.py .....                                       [100%]

============================== 5 passed in 0.06s ===============================
```

### 3.2. Full Test Suite: `tests/`
Command:
```bash
python3 -c "import os, pytest, sys; os.chdir('/home/alexey/git/agent-coordination'); sys.exit(pytest.main(['tests/', '-v']))"
```
Output:
```
============================= test session starts ==============================
platform linux -- Python 3.12.3, pytest-9.1.1, pluggy-1.6.0
rootdir: /home/alexey/git/agent-coordination
configfile: pyproject.toml
plugins: anyio-4.12.1, opik-2.2.54
collecting ... collected 71 items

tests/test_adapter_cli.py .                                              [  1%]
tests/test_bus.py .....                                                  [  8%]
tests/test_bus_cli_host_addressing.py ......                             [ 16%]
tests/test_bus_dogfood.py .                                              [ 18%]
tests/test_cursors.py ...                                                [ 22%]
tests/test_device_registry.py .....                                      [ 29%]
tests/test_envelope.py ..                                                [ 32%]
tests/test_failover_bridge.py ......                                     [ 40%]
tests/test_guards.py ...                                                 [ 45%]
tests/test_host_interface.py .....                                       [ 52%]
tests/test_offline_network.py .                                          [ 53%]
tests/test_quorum_authority.py .....                                     [ 60%]
tests/test_role_failover.py ..............                               [ 80%]
tests/test_sessionless_worker_bus.py .......                             [ 90%]
tests/test_ssh_relay.py ......                                           [ 98%]
tests/test_worker_bus_cli.py .                                           [100%]

============================= 71 passed in 18.62s ==============================
```

---

## 4. Confirmation of Preserved Dirty Files

The 5 dirty uncommitted files in `/home/alexey/git/agent-coordination` were continuously monitored and verified to remain 100% untouched. No modifications, staged changes, or resets were introduced:

1. `adapters/windows_client.py` — Untouched (0 diffs introduced)
2. `coordination/TASKS.json` — Untouched (0 diffs introduced)
3. `coordination/ssh_relay.py` — Untouched (0 diffs introduced)
4. `tests/test_offline_network.py` — Untouched (0 diffs introduced)
5. `tests/test_ssh_relay.py` — Untouched (0 diffs introduced)

---

## 5. Independent Verdict

**ACCEPT**

The implementation in `coordination/host_interface.py` and test coverage in `tests/test_host_interface.py` strictly satisfy all specifications:
1. `MultiHostAdmission` validates device IDs against `DeviceRegistry` and fails closed with `UnknownDevice`.
2. For outbound SSH-only devices (`windows-desktop`), it enforces `session_id=None`, sanitizes/rejects `head.cred`, and routes execution to `hetzner-rmthz` via `sessionless_worker_bus`.
3. For aplexer-host devices (`hetzner-rmthz`), it enforces/caps memory limits to `<= 1500M` and sets delivery to `local_task_unit`.
4. `emit_host_event` atomically records structured JSON lines into `host_events.jsonl` using advisory file locking (`fcntl.flock`).
5. `query_host_events` accurately filters events by `event_type`, `device_id`, and `task_id` under shared lock.
6. The entire 71-test suite passes with 0 regressions.
7. All 5 dirty pre-existing peer files remain 100% untouched.
