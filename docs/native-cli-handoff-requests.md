# Native CLI Handoff Requests for Ant 46fdb644

- **Recipient**: Antigravity Head `46fdb644-9b58-4e2f-aab3-9be5e1e33337` (owner of `cloudflare-aplexer-protocol`)
- **Originator**: `ac-adapter-exec` (`cd07e46a-b698-4e3c-a98c-9d91b913594b`), CLI adapters executor for `agent-coordination`
- **Date**: 2026-10-04
- **Repository constraint**: `cloudflare-aplexer-protocol` remains strictly read-only by this product until explicit handoff ACK. No native source edits or Rust builds were performed.

---

## Item 1: Native `--idempotency-key` on `aplexer message send` & `reply`

### Issue Description
When executing `aplexer message send --idempotency-key <KEY> "body"` against the installed production binary (`/home/alexey/.local/bin/aplexer` version 0.1.9), the command fails with:
```text
error: unexpected argument '--idempotency-key' found
  tip: to pass '--idempotency-key' as a value, use '-- --idempotency-key'
Usage: aplexer message send [OPTIONS] <TEXT>
```

### Analysis of Native Source
In `cloudflare-aplexer-protocol`, the flag has already been added to Rust source definitions:
- `src/bin/aplexer/cli_message_args.rs:146`: `pub(crate) idempotency_key: Option<String>` in `MessageSendArgs`
- `src/bin/aplexer/cli_message_args.rs:172`: `pub(crate) idempotency_key: Option<String>` in `MessageReplyArgs`
- `src/bin/aplexer/message_routing.rs:208, 365`: mapped into envelope

However, because Rust build/install is under strict hold ("No Rust build/install under hold"), the installed binary in PATH remains 0.1.9 without this flag.

### Adapter Interim Workaround
In `adapters/aplexer_ssh.py` and `coordination/ssh_relay.py`:
1. The adapter probes `--help` on the target binary to detect flag presence.
2. If absent, the adapter omits `--idempotency-key` from the native CLI arguments to avoid exit code 2.
3. The idempotency key is embedded into the `--data` JSON payload (`data["idempotency_key"]`), and deduplication is enforced by the adapter's `CursorStore`.

### Requested Action
When the Rust build/install hold is formally reviewed and lifted, Ant `46fdb644` should rebuild and promote the updated `aplexer` binary with the native `--idempotency-key` CLI argument enabled.

---

## Item 2: Origin Authentication & Sender Verification for `--from`

### Issue Description
In native `aplexer message send [OPTIONS] <TEXT>`, the flag `--from <TAG>` acts as an unvalidated sender identity override. When messages cross machine boundaries (such as Windows desktop -> Hetzner server), an arbitrary `--from` flag allows unverified identity spoofing.

### Adapter Interim Workaround
In `adapters/aplexer_ssh.py`:
1. `validate_no_from_spoof` rejects any `--from` argument that does not match the authenticated caller identity.
2. Across SSH, the remote process runs under the SSH user's session (`bridge_device_id`). The authentic client author is recorded in structured metadata (`originating_agent`), with `session_id: null` (no fake Windows session).

### Requested Action
Ant `46fdb644` to review native identity binding in `aplexer message`:
- Consider namespace validation or signed sender tokens so sessions cannot forge sibling tags without authentication.

---

## Item 3: Stdin JSON-RPC / Streaming Mode for Windows Cross-Host Calls

### Issue Description
Windows shells (`cmd.exe` and PowerShell) frequently mangle complex JSON escaping on command-line arguments (e.g. `--data "{\"key\":\"val\"}"`), or hit command length limits.

### Adapter Interim Workaround
`adapters/windows_client.py` implements a typed SSH stdin RPC runner (`execute_stdin_rpc`) that streams JSON-RPC payloads over standard input directly to the remote Python handler.

### Requested Action
Consider adding native support in `aplexer message`:
- `aplexer message send --stdin-json` or `aplexer message rpc` to accept JSON message envelopes directly from stdin.
