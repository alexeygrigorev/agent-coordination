# Independent Peer Review Report: REV-COORD-QL-CONSUMER-FENCING-C2905

## 1. Reviewer Identity & Date
- **Reviewer Role:** Distinct Independent Reviewer for Product 4 (Cross-computer Agent Coordination) under the project head
- **Target Task:** `coord-ql-consumer-fencing` (Directive C2905)
- **Launcher Task ID:** `t-coord-ql-consumer-fencing-c2905`
- **Review Task ID:** `t-coord-ql-consumer-fencing-review-c2905`
- **Review Date:** 2026-10-06 19:27:00 CEST (Europe/Berlin)
- **Workspace:** `/home/alexey/git/agent-coordination`

---

## 2. Evaluated Files & Implementation Architecture

### Target Implementation Files
1. `coordination/ql_consumer_fencing.py` (207 lines)
   - Implements `QLConsumerFencing`, `Fenced`, and `reject_head_cred_inheritance`.
   - Bridges task enqueue and role replacement workflows onto `RoleAuthority` fenced epochs and guarded effects.
2. `tests/test_ql_consumer_fencing.py` (440 lines)
   - Comprehensive test suite covering epoch fencing, credential leakage rejection, guarded effect idempotency/deduplication, and gated replacement startup.

### Architectural Alignment with Directive C2905
- **Task Admission & Epoch Fencing (`QLConsumerFencing.admit_and_enqueue_task`)**:
  - Verifies current leaseholder status via `authority.authorize(project, role, actor, generation, epoch)`.
  - Fails closed immediately with `Fenced` if the leaseholder or epoch is stale or superseded.
- **Credential Isolation (`reject_head_cred_inheritance`)**:
  - Inspects payload dictionaries recursively for sensitive head tokens and credentials (`head.cred`, `head_cred`, `head_token`, `head.token`, `cred`, or string tokens containing `"head"`).
  - When `reject=True` (default in admission & replacement flows), raises `ValueError` to block credential leakage.
  - When `reject=False`, sanitizes payload by recursively stripping all matching credential keys.
- **Deduplication via Control-Plane Guarded Effects**:
  - Admission uses idempotency key `f"ql-task:{project}:{role}:{epoch}:{task_id}"`.
  - Retried submissions with identical task ID under the same epoch are deduplicated and return `{"state": "already_enqueued"}` without duplicate launcher invocation.
- **Epoch Validation (`validate_consumer_epoch`)**:
  - Validates `epoch`, `holder`, and `generation` against `authority.role_state(project, role)`.
  - Confirms active authorization via `authority.authorize(project, role, actor, generation, expected_epoch)`.
  - Fails closed (`False`) on expired leases, suspect states, actor mismatches, or unconfigured roles.
- **Gated Role Replacement Startup (`gated_replacement_startup`)**:
  - Requires caller to be authorized for the specified epoch.
  - Verifies caller activation receipt via `authority.activation(...)`, failing closed (`Fenced`) if `role_ack` or `first_action` is missing or if the state is `pending_role_ack_and_first_action`.
  - Sanitizes the replacement payload against head credential leakage.
  - Executes single-instance launch using guarded effect key `f"ql-replace:{project}:{role}:{caller_epoch}"`, preventing duplicate replacement instances per epoch.

---

## 3. Verification of Negative & Concurrency Cases

| Case | Scenario | Expected Behavior | Observed Result | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Valid Enqueue** | Active leaseholder with matching epoch and clean payload submits task | Admitted; launcher executed once; returns queued status | Passed (`test_valid_enqueue_under_current_epoch`) | **VERIFIED** |
| **Stale Epoch / Deposed Principal** | Former holder attempts enqueue after failover election promotes successor | Fails closed with `Fenced`; launcher is not called | Passed (`test_stale_principal_fenced_after_takeover`) | **VERIFIED** |
| **Epoch Spoofing** | Deposed holder attempts to use newly elected epoch | Fails closed with `Fenced`; holder mismatch rejected | Passed (`test_stale_principal_fenced_after_takeover`) | **VERIFIED** |
| **Launch Deduplication** | Same task ID submitted multiple times in same epoch | First succeeds; subsequent return `{"state": "already_enqueued"}`; launcher called exactly once | Passed (`test_deduplicate_launch_intents`) | **VERIFIED** |
| **Credential Rejection** | Payloads contain `head.cred`, `head_cred`, `head_token`, or nested head credentials | Rejected with `ValueError`/`Fenced`; launcher never called | Passed (`test_reject_head_cred_inheritance`) | **VERIFIED** |
| **Credential Sanitization** | `reject_head_cred_inheritance` called with `reject=False` | Head credentials stripped, non-credential fields preserved | Passed (`test_reject_head_cred_inheritance`) | **VERIFIED** |
| **Gated Replacement (Unactivated)** | Caller has not completed `role_ack` and `first_action` | Fails closed with `Fenced`; replacement launch rejected | Passed (`test_gated_replacement_startup_single_instance`) | **VERIFIED** |
| **Gated Replacement (Single Instance)** | Multiple replacement requests in same epoch | Exactly one launch executed under key `ql-replace:...`; duplicates return `already_enqueued` | Passed (`test_gated_replacement_startup_single_instance`) | **VERIFIED** |
| **Epoch Validation (Mismatch/Expired)** | Validation with wrong epoch, actor, generation, or expired lease | Returns `False` (fails closed) | Passed (`test_validate_consumer_epoch`) | **VERIFIED** |

---

## 4. Test Execution Results & Command Output

### Target Unit Tests: `tests/test_ql_consumer_fencing.py`
Command:
```bash
python3 -m pytest tests/test_ql_consumer_fencing.py -vv
```
Output:
```
============================= test session starts ==============================
platform linux -- Python 3.12.3, pytest-9.1.1, pluggy-1.6.0 -- /usr/bin/python3
cachedir: .pytest_cache
rootdir: /home/alexey/git/agent-coordination
configfile: pyproject.toml
plugins: anyio-4.12.1, opik-2.2.54
collecting ... collected 6 items

tests/test_ql_consumer_fencing.py::test_valid_enqueue_under_current_epoch PASSED [ 16%]
tests/test_ql_consumer_fencing.py::test_stale_principal_fenced_after_takeover PASSED [ 33%]
tests/test_ql_consumer_fencing.py::test_deduplicate_launch_intents PASSED [ 50%]
tests/test_ql_consumer_fencing.py::test_reject_head_cred_inheritance PASSED [ 66%]
tests/test_ql_consumer_fencing.py::test_gated_replacement_startup_single_instance PASSED [ 83%]
tests/test_ql_consumer_fencing.py::test_validate_consumer_epoch PASSED   [100%]

============================== 6 passed in 2.52s ===============================
```

### Full Repository Regression Test Suite
Command:
```bash
python3 -m pytest tests/ -v
```
Output:
```
============================= test session starts ==============================
platform linux -- Python 3.12.3, pytest-9.1.1, pluggy-1.6.0
rootdir: /home/alexey/git/agent-coordination
configfile: pyproject.toml
plugins: anyio-4.12.1, opik-2.2.54
collecting ... collected 77 items

tests/test_adapter_cli.py .                                              [  1%]
tests/test_bus.py .....                                                  [  7%]
tests/test_bus_cli_host_addressing.py ......                             [ 15%]
tests/test_bus_dogfood.py .                                              [ 16%]
tests/test_cursors.py ...                                                [ 20%]
tests/test_device_registry.py .....                                      [ 27%]
tests/test_envelope.py ..                                                [ 29%]
tests/test_failover_bridge.py ......                                     [ 37%]
tests/test_guards.py ...                                                 [ 41%]
tests/test_host_interface.py .....                                       [ 48%]
tests/test_offline_network.py .                                          [ 49%]
tests/test_ql_consumer_fencing.py ......                                 [ 57%]
tests/test_quorum_authority.py .....                                     [ 63%]
tests/test_role_failover.py ..............                               [ 81%]
tests/test_sessionless_worker_bus.py .......                             [ 90%]
tests/test_ssh_relay.py ......                                           [ 98%]
tests/test_worker_bus_cli.py .                                           [100%]

============================= 77 passed in 15.66s ==============================
```

---

## 5. Confirmation of Preserved Dirty Uncommitted Files

Git status check in `/home/alexey/git/agent-coordination` confirmed that all 5 preserved dirty uncommitted files remain 100% untouched, with zero diffs introduced and zero resets:
- `adapters/windows_client.py` (Untouched, preserved)
- `coordination/TASKS.json` (Untouched, preserved)
- `coordination/ssh_relay.py` (Untouched, preserved)
- `tests/test_offline_network.py` (Untouched, preserved)
- `tests/test_ssh_relay.py` (Untouched, preserved)

Git status porcelain:
```
 M adapters/windows_client.py
 M coordination/TASKS.json
 M coordination/ssh_relay.py
 M tests/test_offline_network.py
 M tests/test_ssh_relay.py
?? coordination/ql_consumer_fencing.py
?? reviews/REV-COORD-QL-CONSUMER-FENCING-C2905.md
?? tests/test_ql_consumer_fencing.py
```

---

## 6. Independent Review Verdict

**Verdict:** **`ACCEPT`**

The implementation in `coordination/ql_consumer_fencing.py` cleanly satisfies all safety, fencing, idempotency, and credential isolation invariants of Directive C2905. The accompanying test suite in `tests/test_ql_consumer_fencing.py` provides thorough coverage of valid, negative, concurrent, and fail-closed edge cases. The entire test suite of 77 tests passes with zero regressions, and all uncommitted working files have been preserved intact.
