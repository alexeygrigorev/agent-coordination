# REV-COORD-CLI-SOURCE-C2880 — Independent Code Review

Verdict: **ACCEPT**

- **Reviewer**: Distinct Independent Peer Reviewer for Product 4 (Cross-computer Agent Coordination)
- **Review Role**: Independent Peer Reviewer for task `coord-native-cli-source` (launcher task `t-coord-cli-source-c2880` / review task `t-coord-cli-review-c2880`)
- **Caller / Parent**: `764358a8-1b4e-49c6-845a-9b79bf3ba536`
- **Project**: Cross-computer Agent Coordination (`agent-coordination`)
- **Target Workspace**: `/home/alexey/git/agent-coordination`
- **Parent Baseline Commit**: `c391a739b09ca8d1fff0fc970450cc8bc9be0fe9`
- **Pinned Implementation Commit**: `30df32ae2bbcc47558556e03701e28bae4a10022`
- **Tree Hash**: `379fc3e58735b5b535930231175bf4f5d7ceddea`
- **Diff SHA-256**: `f5c5920ce4193c00135f9a479534f2c63246568b08c5b49655573a5d02b07b97` (against parent `c391a739b09ca8d1fff0fc970450cc8bc9be0fe9`)
- **Review Date**: 2026-10-06 (Europe/Berlin / CEST)

---

## 1. Explicit Attestation & Scope of Changes

### 1.1. Reviewer Attestation
The independent reviewer explicitly attests that the pinned commit `30df32ae2bbcc47558556e03701e28bae4a10022` (tree `379fc3e58735b5b535930231175bf4f5d7ceddea`, diff SHA-256 `f5c5920ce4193c00135f9a479534f2c63246568b08c5b49655573a5d02b07b97` against parent commit `c391a739b09ca8d1fff0fc970450cc8bc9be0fe9`) is the exact output independently evaluated, executed, verified, and accepted for task `coord-native-cli-source`.

### 1.2. Evaluated Files & Normalized Diff Counts
The changes comprise the following implementation and test additions:

1. **`coordination/bus_cli.py`**:
   - **Normalized Diff**: **273 insertions(+)**, **24 deletions(-)** (total **297 lines touched/modified**).
   - **Cross-command Addressing Support**: Added `--device`, `--target-device`, and `--registry` arguments across bus CLI subcommands (`register`, `send`, `inbox`, `wait`, `worker-register`, `worker-send`, `worker-receive`), and made `--registry` and `--json` available uniformly via common parent parser.
   - **DeviceRegistry Validation**: Implemented `_load_registry(args)` supporting explicit `--registry <path>`, environment variable `AGENT_DEVICE_REGISTRY`, and fallback to `examples/devices.example.json`.
   - **Fail-Closed Unknown Device Gate**: Validates targets against `DeviceRegistry.get(target_device)`, failing closed by raising `UnknownDevice(target_device)` (with error code `unknown_device`).
   - **Fail-Closed Device Mismatch Gate**: Validates that recipient identities registered on one device cannot be erroneously targeted at a different device without raising `CoordinationError("Target device mismatch: ...")`.
   - **Strict Sessionless Identity Formatting**: Enforces `session_id=None` when creating `NamespacedId` for remote host destinations and originating agents, completely avoiding synthetic aplexer session invention.
   - **Consistent JSON Error Formatting**: Top-level exception handling catches `UnknownDevice`, `CoordinationError`, and general exceptions, printing valid parseable JSON to stdout when `--json` is supplied, and clean error messages to stderr otherwise.

2. **`tests/test_bus_cli_host_addressing.py`**:
   - **Normalized Diff**: **392 insertions(+)**, **0 deletions(-)** (total **392 lines**, 6 comprehensive tests).
   - `test_registration_with_device_identity`: Tests `--device`, `--target-device`, and `worker-register` device identity persistence.
   - `test_sending_message_with_explicit_remote_host_device_target`: Tests sending with remote target, destination envelope verification, and recipient inbox query/filtering.
   - `test_unknown_device_fails_closed_with_clear_error`: Verifies fail-closed behavior on unregistered host targets with and without `--json`.
   - `test_target_device_mismatch_fails_closed`: Verifies fail-closed behavior when target device does not match enrolled recipient device.
   - `test_worker_bus_explicit_device_targeting`: Tests end-to-end `worker-send`, `worker-receive`, and `worker-ack` across distinct device IDs.
   - `test_custom_registry_path_validation`: Tests `--registry` pointing to an isolated custom registry file.

---

## 2. Verification of Negative & Safety Cases

### 2.1. Unknown Device Allowlist Validation (`unknown_device`)
- **Requirement**: Unregistered hostnames or devices must be rejected fail-closed with code `unknown_device`.
- **Implementation**:
  In `cmd_send`, `cmd_inbox`, `cmd_wait`, `cmd_worker_send`, and `cmd_worker_receive`:
  ```python
  reg = _load_registry(args)
  if target_device:
      if reg is not None:
          reg.get(target_device)
      else:
          raise UnknownDevice(target_device)
  ```
  `DeviceRegistry.get(device_id)` raises `UnknownDevice(device_id)` when the device ID is not allowlisted.
- **Verification**:
  Executing `python3 coordination/bus_cli.py ... send --target-device unknown-rogue --json` returns exit code `1` and emits:
  ```json
  {"error": "UnknownDevice", "code": "unknown_device", "message": "unknown_device:unknown-rogue", "device_id": "unknown-rogue"}
  ```
  Without `--json`, it exits with code `1` and outputs `Error: unknown_device:unknown-rogue` to stderr.

### 2.2. Target Device Mismatch Fail-Closed
- **Requirement**: Prevent cross-device identity spoofing or sending to an enrolled recipient under an erroneous target device.
- **Implementation**:
  ```python
  if recipient_id in identities:
      recip_ident = identities[recipient_id]
      if target_device and recip_ident.get("device_id") and recip_ident.get("device_id") != target_device:
          raise CoordinationError(
              f"Target device mismatch: recipient {recipient_id} is enrolled on {recip_ident.get('device_id')}, expected {target_device}"
          )
  ```
- **Verification**:
  Executing a send command targeting a recipient registered on `hetzner-rmthz` while specifying `--target-device windows-desktop` raises `CoordinationError` and outputs:
  ```json
  {"error": "CoordinationError", "code": "coordination_error", "message": "Target device mismatch: recipient <id> is enrolled on hetzner-rmthz, expected windows-desktop"}
  ```
  Exits cleanly with return code `1` without uncaught exceptions or tracebacks.

### 2.3. No Synthetic Session Invention (`session_id=None`)
- **Requirement**: Destination envelopes for remote hosts must never fabricate synthetic aplexer session IDs.
- **Implementation**:
  ```python
  dest_namespaced = NamespacedId(
      device_id=target_device,
      workspace=cred.get("project_id", "agent-coordination"),
      agent_tag=args.to,
      task_id=cred.get("task_id") or "default",
      session_id=None,  # MUST STAY NONE: No invented synthetic session
  )
  ```
- **Verification**:
  Inspected envelope payload structure in sent message:
  - `data["destination_namespaced"]["session_id"]` is `None` (`null` in JSON).
  - `data["destination"]` renders as `windows-desktop/agent-coordination/<recipient>/-/default` (using the standard `-` placeholder for sessionless).
  - Originating agent identity also preserves `session_id=None`.

### 2.4. Valid JSON on Success and Errors
- **Requirement**: `--json` flag must ensure valid JSON output across all execution paths.
- **Implementation & Verification**:
  All command success paths format their output via `json.dumps(..., indent=2)`.
  Top-level error handling in `main()` wraps `args.func(args)` in `try...except`:
  - `UnknownDevice`: serializes error name, code, message, and device_id.
  - `CoordinationError`: serializes error class name, error code, and message.
  - General `Exception`: serializes error class name and message.
  All error paths under `--json` output parseable JSON to stdout and return code `1`.

---

## 3. Test Execution Results

All unit and integration tests were executed in the target repository `/home/alexey/git/agent-coordination`.

### 3.1. Host Addressing Test Suite
```bash
python3 -m pytest tests/test_bus_cli_host_addressing.py -vv
```
**Output**:
```text
============================= test session starts ==============================
platform linux -- Python 3.12.3, pytest-9.1.1, pluggy-1.6.0 -- /usr/bin/python3
cachedir: .pytest_cache
rootdir: /home/alexey/git/agent-coordination
configfile: pyproject.toml
plugins: anyio-4.12.1, opik-2.2.54
collecting ... collected 6 items

tests/test_bus_cli_host_addressing.py::test_registration_with_device_identity PASSED [ 16%]
tests/test_bus_cli_host_addressing.py::test_sending_message_with_explicit_remote_host_device_target PASSED [ 33%]
tests/test_bus_cli_host_addressing.py::test_unknown_device_fails_closed_with_clear_error PASSED [ 50%]
tests/test_bus_cli_host_addressing.py::test_target_device_mismatch_fails_closed PASSED [ 66%]
tests/test_bus_cli_host_addressing.py::test_worker_bus_explicit_device_targeting PASSED [ 83%]
tests/test_bus_cli_host_addressing.py::test_custom_registry_path_validation PASSED [100%]

============================== 6 passed in 0.64s ===============================
```

### 3.2. Full Repository Test Suite
```bash
python3 -m pytest tests/ -v
```
**Output**:
```text
============================= test session starts ==============================
platform linux -- Python 3.12.3, pytest-9.1.1, pluggy-1.6.0
rootdir: /home/alexey/git/agent-coordination
configfile: pyproject.toml
plugins: anyio-4.12.1, opik-2.2.54
collecting ... collected 66 items

tests/test_adapter_cli.py .                                              [  1%]
tests/test_bus.py .....                                                  [  9%]
tests/test_bus_cli_host_addressing.py ......                             [ 18%]
tests/test_bus_dogfood.py .                                              [ 19%]
tests/test_cursors.py ...                                                [ 24%]
tests/test_device_registry.py .....                                      [ 31%]
tests/test_envelope.py ..                                                [ 34%]
tests/test_failover_bridge.py ......                                     [ 43%]
tests/test_guards.py ...                                                 [ 48%]
tests/test_offline_network.py .                                          [ 50%]
tests/test_quorum_authority.py .....                                     [ 57%]
tests/test_role_failover.py ..............                               [ 78%]
tests/test_sessionless_worker_bus.py .......                             [ 89%]
tests/test_ssh_relay.py ......                                           [ 98%]
tests/test_worker_bus_cli.py .                                           [100%]

============================= 66 passed in 14.92s ==============================
```

---

## 4. Confirmation of 5 Dirty Files Untouched

Per the reviewer constraints, the pre-existing uncommitted modifications in `/home/alexey/git/agent-coordination` were checked and verified to be 100% untouched (zero modifications introduced, zero resets):

1. `adapters/windows_client.py`: Untouched pre-existing state.
2. `coordination/TASKS.json`: Untouched pre-existing state.
3. `coordination/ssh_relay.py`: Untouched pre-existing state.
4. `tests/test_offline_network.py`: Untouched pre-existing state.
5. `tests/test_ssh_relay.py`: Untouched pre-existing state.

`git status` confirms that no unintended files were modified or staged.

---

## 5. Independent Verdict

**ACCEPT**

The independent reviewer confirms that pinned commit `30df32ae2bbcc47558556e03701e28bae4a10022` (tree `379fc3e58735b5b535930231175bf4f5d7ceddea`, diff SHA-256 `f5c5920ce4193c00135f9a479534f2c63246568b08c5b49655573a5d02b07b97` against parent `c391a739b09ca8d1fff0fc970450cc8bc9be0fe9`) fully satisfies the cross-computer host addressing requirements:
1. Explicit attestation confirms the reviewed commit and tree match the exact evaluated output.
2. Normalized diff counts (`coordination/bus_cli.py` +273/-24 lines touched: 297; `tests/test_bus_cli_host_addressing.py` +392 lines) are verified accurate.
3. Native CLI commands support `--device`, `--target-device`, and `--registry`.
4. Allowlist validation fails closed with code `unknown_device` when invalid devices are supplied.
5. Target device mismatches fail closed cleanly without crashing.
6. Remote host destinations maintain `session_id=None` without synthetic session fabrication.
7. All `--json` outputs produce parseable JSON on both success and error.
8. The entire 66-test suite passes with zero regressions.
9. All 5 dirty pre-existing peer files remain 100% untouched.
