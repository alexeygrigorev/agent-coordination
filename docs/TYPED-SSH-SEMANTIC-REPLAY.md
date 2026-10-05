# Typed SSH Stdin RPC and Semantic Replay Verification Report

- **Document**: `docs/TYPED-SSH-SEMANTIC-REPLAY.md`
- **Component**: `agent-coordination`
- **Author**: Typed SSH & Semantic Replay Verification Worker (for `agent-coordination-head`)
- **Git Pin Baseline**: `a412cea` / `bb8dcad`
- **Verification Date**: 2026-10-05
- **Status**: Verified via unit test suite (31/31 passed); Two-computer live execution nominated in `docs/desktop-integration-test.md`.

---

## Executive Summary

This report documents the verification of the **Typed SSH Stdin RPC mechanism**, **fail-closed receipt validation**, **semantic replay protection**, and **separated receipt/ACK/outcome states** implemented in `agent-coordination`.

The implementation addresses critical multi-computer operational hazards identified when bridging Windows workstations with Linux server nodes running native `aplexer`:
1. **Windows Shell Corruption Bypassed**: Standard CLI argument passing on Windows (`cmd.exe` or PowerShell) suffers from quote stripping, escape character mangling, and command length limitations. Streaming typed JSON-RPC over SSH `stdin` eliminates command-line interpretation entirely.
2. **Fail-Closed Receipt Policy**: Transport commands fail closed immediately if the remote transport does not return a confirmed durable `message_id`.
3. **No Forged Windows Aplexer Origin**: Because Windows has no native `aplexer` binary or daemon, `originating_agent` enforces `session_id = None`. Any attempt to forge an invented session UUID fails immediately with `IdentitySpoofError`.
4. **Semantic Replay Protection**: Idempotency keys bound to payload SHA-256 digests ensure retries produce identical receipts without duplicating messages or allowing payload divergence.
5. **Separated State Transitions**: Send receipts, recipient read ACKs, semantic agreements, and action completions are tracked as strictly separated lifecycle stages.
6. **Acceptance Boundary Clarified**: Local pytest passes (31/31) verify protocol invariants and state machines, but are explicitly **not** two-computer cross-host acceptance proof. Live two-computer execution is specified in `docs/desktop-integration-test.md` and awaits physical desktop triggering.

---

## 1. Typed SSH Stdin RPC Protocol

### 1.1 Hazard & Motivation

When executing remote commands across Windows workstations into remote Linux execution hosts:
- `cmd.exe` and PowerShell handle double quotes, nested JSON brackets, carets (`^`), percent signs (`%`), and newlines inconsistently.
- Argument length limits (e.g. 8,191 characters in `cmd.exe`, 32,768 in `CreateProcess`) truncate large structured task payloads.
- Passing structured JSON payloads via `--data '{"key": "value"}'` creates injection risks and escape failures.

### 1.2 Protocol Design (`adapters/windows_client.py`)

The Typed SSH Stdin RPC streams structured JSON-RPC requests directly over SSH `stdin`, invoking a lightweight remote dispatcher without passing user payload data in command-line arguments.

#### Invocation Command
```bash
ssh -o BatchMode=yes -o StrictHostKeyChecking=yes <alias> -- python3 -c "<dispatcher_script>"
```

#### Request Wire Schema (`TypedRpcRequest`)
```json
{
  "method": "send",
  "params": {
    "workspace": "/home/alexey/git/agent-coordination",
    "to": "agent-coordination-head",
    "body": "Task status report",
    "token": "TOK-20261005-001",
    "idempotency_key": "ac-550e8400-e29b-41d4-a716-446655440000",
    "originating_agent": {
      "device_id": "windows-desktop",
      "kind": "ssh-client-host",
      "native_aplexer": false,
      "workspace": "work/agent-coordination",
      "tag": "windows-codex"
    },
    "bridge_device_id": "hetzner-rmthz",
    "aplexer_bin": "/home/alexey/.local/bin/aplexer"
  },
  "request_id": "5698b631-6e84-4ca8-a6d1-447a1924558e"
}
```

#### Supported RPC Methods

| Method | Parameters | Behavior |
| --- | --- | --- |
| `send` | `workspace`, `to`, `body`, `token`, `idempotency_key`, `originating_agent`, `bridge_device_id`, `aplexer_bin` | Invokes native `aplexer message send` on target host; returns durable message receipt. |
| `poll` | `workspace` (opt), `tag` (opt), `aplexer_bin` | Invokes `aplexer message inbox --json`; returns unread message list. |
| `reply` | `message_id`, `body`, `token`, `idempotency_key`, `originating_agent`, `bridge_device_id` | Invokes `aplexer message reply`; returns reply receipt. |
| `ack` | `message_ids`, `all` (bool), `tag` (opt) | Acknowledges messages to clear from active unread inbox. |
| `status` | None | Returns host health and aplexer presence. |

#### Response Wire Schema (`TypedRpcResponse`)
On success:
```json
{
  "request_id": "5698b631-6e84-4ca8-a6d1-447a1924558e",
  "success": true,
  "result": {
    "id": "0199ac389a01720ea3be8bcfb5c0c99a",
    "delivery": "inbox",
    "created_at": 1791116400
  },
  "error": null
}
```

On failure:
```json
{
  "request_id": "5698b631-6e84-4ca8-a6d1-447a1924558e",
  "success": false,
  "result": null,
  "error": {
    "code": "aplexer_exit",
    "message": "error: recipient tag not found"
  }
}
```

---

## 2. Failure-Closed Receipt Validation

A primary architectural requirement is that the transport layer must never assume delivery succeeded simply because a network socket exited with return code 0.

### 2.1 Validation Rules

1. **Non-Zero SSH Return Code**:
   `ssh_run()` catches `subprocess.TimeoutExpired` and `OSError`, wrapping them in `TransportUnavailable(f"ssh_error:{...}")`. If `proc.returncode != 0`, it raises `TransportUnavailable(f"ssh_exit:{proc.returncode}:{err}")`.
2. **Malformed JSON Payload**:
   If the remote endpoint outputs invalid JSON, `send_message()` raises `ReceiptMissingError(f"Remote host returned invalid JSON receipt: ...")`.
3. **Missing Durable Message ID**:
   ```python
   message_id = raw_receipt.get("id") or raw_receipt.get("message_id")
   if not message_id:
       raise ReceiptMissingError(
           f"Fail-closed: remote response missing durable message ID. Payload: {raw_receipt}"
       )
   ```
   Even if the remote returns `{"status": "ok"}`, if `id` (or `message_id`) is omitted or empty, execution fails closed.
4. **RPC Failure Propagation**:
   In `send_message(use_stdin_rpc=True)`:
   ```python
   if not rpc_resp.success:
       err_msg = rpc_resp.error.get("message", "unknown_error") if rpc_resp.error else "failed"
       raise ReceiptMissingError(f"RPC send failed: {err_msg}")
   ```

---

## 3. Origin Authentication & Anti-Spoofing Rules

### 3.1 Strict Separation of Identities

| Entity | Role | Identity Invariants |
| --- | --- | --- |
| `originating_agent` | The actual author on the workstation | `device_id="windows-desktop"`, `native_aplexer=False`, `session_id=None`. **Never invent an aplexer session ID**. |
| `bridge_device_id` | The allowlisted execution host | `device_id="hetzner-rmthz"`. The SSH process runs under the authenticated SSH user's Unix session. |

### 3.2 Enforcement Invariant: `session_id = None`

In `adapters/windows_client.py`:
```python
@dataclass
class OriginatingAgent:
    device_id: str = "windows-desktop"
    kind: str = "ssh-client-host"
    native_aplexer: bool = False
    workspace: str = "work/agent-coordination"
    tag: str = "windows-codex"
    session_id: str | None = None  # MUST STAY NONE: No invented Windows aplexer session

    def validate(self) -> None:
        if self.session_id is not None:
            raise IdentitySpoofError(
                f"Invented Windows aplexer session ID forbidden: '{self.session_id}'. "
                "Windows has no local aplexer binary."
            )
```
- Calling `origin.to_dict()` invokes `self.validate()`, which strips `session_id` from the output dictionary and forbids any non-`None` value.
- In `adapters/aplexer_ssh.py`, `validate_no_from_spoof` prevents callers from passing `--from <tag>` to forge another session's tag across the SSH bridge.

---

## 4. Semantic Replay Protection & Idempotency Keys

### 4.1 Payload Canonical Digest (`coordination/cursors.py`)

Deduplication requires verifying not only the key, but also that the content has not mutated under the same key:
```python
def payload_digest(body: str, data: dict[str, Any] | None) -> str:
    blob = json.dumps({"body": body, "data": data or {}}, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()
```

### 4.2 Idempotency Lookup and Conflict Detection

In `CursorStore`:
1. `lookup_send(key, sender, recipient, digest)`:
   - If `key` is absent in `idempotency.json`: returns `None` (proceed with send).
   - If `key` exists and `sender`, `recipient`, and `digest` match identically: returns the cached `message_id` (idempotent short-circuit; suppresses duplicate remote command).
   - If `key` exists but `sender`, `recipient`, or `digest` differ: raises `IdempotencyConflict(key)` (fails closed against payload mutation).
2. `remember_send(key, sender, recipient, digest, message_id)`:
   - Writes the record atomically using `.tmp` file replacement to prevent corrupt reads during concurrent operations.

### 4.3 Outbox Queueing for Disconnected / Client Nodes

When a sender transmits a message to a node that cannot accept inbound SSH (such as `windows-desktop`, where `can_run_aplexer() == False`):
- `SshRelay.send()` records the message into `outbox.jsonl` with `queued_for_client_poll: True`.
- `SendReceipt` is issued with `delivery="queued_client_poll"`.
- The Windows client later retrieves the message during its periodic `poll` cycle.

---

## 5. Cursor Tracking & Separated State Transitions

### 5.1 Architectural Invariant

> **"A send receipt is not a recipient read ACK. A read ACK is not semantic agreement. Semantic agreement is not action completion."**

`coordination/envelope.py` defines explicit, non-interchangeable states:

```
+---------------+
|   RECORDED    | (Queued in outbox / pending client polling)
+-------+-------+
        |
        v
+---------------+
| SEND_RECEIPT  | (Transport delivered into mailbox; durable message_id issued)
+-------+-------+
        |
        v
+---------------+
| READ_ACK      | (Recipient read message; acknowledged via aplexer message ack)
+-------+-------+
        |
        v
+---------------+
|SEMANTIC_AGREED| (Recipient parsed content and agreed to proposal/plan)
+-------+-------+
        |
        v
+---------------+
|ACTION_COMPLETE| (Recipient completed work and verified evidence paths)
+---------------+
```

### 5.2 Dataclass Hierarchy

1. `SendReceipt`: Issued upon transport confirmation. Contains `message_id`, `idempotency_key`, `sender`, `recipient`, `delivery`, `catalog_resolved_session_id`, `bridge_device_id`, `originating_agent`, `payload_sha256`, `state=TransportState.SEND_RECEIPT`.
2. `ReadAck`: Issued when the recipient session consumes and acknowledges the message. Contains `message_id`, `acked_by`, `acked_at`, `state=TransportState.RECIPIENT_READ_ACK`.
3. `ActionOutcome`: Issued when the downstream action concludes. Contains `message_id`, `correlation_token`, `reply_message_id`, `agreed: bool`, `completed: bool`, `evidence_paths: list[str]`.
   - `completed=True` -> `TransportState.ACTION_COMPLETED`
   - `agreed=True` -> `TransportState.SEMANTIC_AGREED`
   - `agreed=False` -> `TransportState.SEND_RECEIPT` (no semantic progress).

### 5.3 Mailbox Cursor Watermarking

`CursorStore.cursor(mailbox: str) -> str | None` and `CursorStore.advance(mailbox: str, message_id: str) -> None`:
- Stores high-watermark message IDs per mailbox in `cursors.json`.
- Protects consumers from re-processing already-handled messages after client reconnection.

---

## 6. Test Suite Execution & Local Limitations

### 6.1 Pytest Execution Results

Execution command:
```bash
python3 -m pytest tests/ adapters/ -v
```

Output:
```text
============================= test session starts ==============================
platform linux -- Python 3.12.3, pytest-9.1.1, pluggy-1.6.0
rootdir: /home/alexey/git/agent-coordination
configfile: pyproject.toml
plugins: anyio-4.12.1, opik-2.2.54
collected 31 items

tests/test_adapter_cli.py .                                              [  3%]
tests/test_bus.py .....                                                  [ 19%]
tests/test_bus_dogfood.py .                                              [ 22%]
tests/test_cursors.py ...                                                [ 32%]
tests/test_device_registry.py ...                                        [ 41%]
tests/test_envelope.py ..                                                [ 48%]
tests/test_guards.py ...                                                 [ 58%]
tests/test_ssh_relay.py ......                                           [ 77%]
adapters/test_adapters.py .......                                        [100%]

============================== 31 passed in 1.08s ==============================
```

All 31 unit tests pass cleanly:
- 24 tests in `tests/` covering device admission, catalog resolution, offline queueing, idempotency replay, and guards.
- 7 tests in `adapters/test_adapters.py` covering device listing, anti-spoofing, pane-injection rejection, Windows originating agent validation (`session_id=None`), fail-closed missing receipt, valid send receipt formatting, and RPC line dispatch.

### 6.2 Local Test Limitations vs Two-Computer Acceptance Proof

As explicitly codified in `tests/test_ssh_relay.py` (`test_localhost_fake_is_not_cross_computer_proof`):
- Local tests use `FakeTransport`, monkeypatching, and in-memory test doubles.
- Local pytest execution validates protocol correctness, parsing logic, and negative guards, but **does not constitute proof of cross-computer delivery**.
- Cross-computer acceptance requires live execution across the real network boundary between the Windows workstation and the Hetzner remote server (`hetzner-rmthz`).

---

## 7. Status of Two-Computer Readiness

| Readiness Criterion | Status | Evidence / Location |
| --- | --- | --- |
| **Typed SSH Stdin RPC** | **Ready** | Implemented in `adapters/windows_client.py` (`execute_stdin_rpc`, `handle_rpc_line`); unit-tested in `adapters/test_adapters.py`. |
| **Fail-Closed Receipts** | **Ready** | Enforced in `send_message()`, `reply_message()`; verified by `test_windows_client_fail_closed_missing_receipt`. |
| **Anti-Spoofing & Identity Separation** | **Ready** | `OriginatingAgent.validate()` rejects non-null `session_id`; `validate_no_from_spoof()` prevents remote `--from` injection. |
| **Semantic Replay & Idempotency** | **Ready** | Canonical payload hashing + `CursorStore.lookup_send()` tested in `test_idempotent_retry_does_not_double_send`. |
| **State Separation** | **Ready** | `TransportState` hierarchy (`SEND_RECEIPT`, `READ_ACK`, `SEMANTIC_AGREED`, `ACTION_COMPLETED`) defined in `coordination/envelope.py`. |
| **Physical Two-Host Test** | **Nominated** | Fully specified in `docs/desktop-integration-test.md`; awaiting trigger at physical workstation boundary. |

---

## Conclusion & Next Actions

1. The typed SSH stdin RPC implementation in `adapters/windows_client.py` is sound, robust against shell quoting issues, strictly separates originating vs bridge identity, and fails closed when native receipts are absent.
2. The semantic replay protection in `coordination/cursors.py` and `coordination/ssh_relay.py` guarantees idempotent retransmissions while detecting payload conflicts.
3. The codebase remains cleanly pinned at `a412cea` / `bb8dcad`.
4. The nomination contract in `docs/desktop-integration-test.md` is complete and ready for execution by the desktop orchestrator or user when two-computer testing is initiated.
