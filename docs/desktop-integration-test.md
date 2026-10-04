# Desktop Integration Action Contract (Nomination)

> [!IMPORTANT]
> **Status: Test Contract Nomination Only**
> This document specifies the exact contract, test matrix, and evidence criteria for real two-computer integration. It is a **nomination** and specification of the test; **it does not claim the test has been executed**.
> Execution of Windows commands will occur when the desktop orchestrator or user executes them at the physical two-computer boundary.

- **Contract Owner**: `agent-coordination-head` (`81e8010c-89e4-478b-be3a-4ee6991607f3`)
- **Adapter Owner**: `ac-adapter-exec` (`cd07e46a-b698-4e3c-a98c-9d91b913594b`)
- **Desktop Environment**: Windows desktop (`.local/desktop-environment.json`), outbound `ssh.exe` available, allowlisted alias `hetzner`, Python 3.11+, allowed workspace `work/agent-coordination`.
- **Inbound Access**: NONE (no inbound SSH server, no local aplexer installation).

## Separation of Identities

1. `originating_agent`: The Windows agent author (`device_id: windows-desktop`, `workspace: work/agent-coordination`, `tag: windows-codex`, `native_aplexer: false`).
   - **Crucial Rule**: `session_id` MUST be `null` / omitted. Never invent a Windows `aplexer` session UUID.
2. `bridge_device_id`: The execution host (`hetzner-rmthz`) where the remote SSH command is spawned.
   - **Crucial Rule**: The client must never pass `--from` to impersonate a Hetzner session.

## Test Verification Matrix (When Executed on Desktop)

| Step | Action | Direction | Verification Evidence |
| --- | --- | --- | --- |
| 1. Typed Send | Windows Codex sends typed ping to Hetzner `agent-coordination-head` via `adapters/windows_client.py send` | Windows -> Hetzner | Returns valid JSON `SendReceipt` with durable `message_id`. Fail-closed if receipt is missing. |
| 2. Remote Receipt | Hetzner head inspects inbox (`aplexer message inbox --json`) | Hetzner local | Inbox shows durable message containing `originating_agent` data, correlation token, and no forged Windows session ID. |
| 3. Remote Reply | Hetzner head replies via `aplexer message reply <id> "ACK AC-WIN-HETZ-001"` | Hetzner -> Queue | Produces durable reply message in mailbox. |
| 4. Outbound Poll | Windows Codex polls inbox via `adapters/windows_client.py poll` | Windows -> Hetzner | Windows client displays typed `PollMessage` with matching `correlation_token` and `reply_to`. |
| 5. Separate Read ACK | Windows Codex acks the reply via `adapters/windows_client.py ack <reply_id>` | Windows -> Hetzner | Subsequent poll returns empty list (message removed from active inbox). |
| 6. Flaky Retry | Replay Step 1 with identical `--idempotency-key` | Windows -> Hetzner | Returns identical `message_id` receipt without creating a duplicate message. |
| 7. Negative Guard: Fake Session | Invoke Windows client with forged `session_id` | Client local | Fails immediately with `IdentitySpoofError`. |
| 8. Negative Guard: Pane Injection | Attempt to pass `--pane` to remote command | Transport | Fails closed with safety guard rejection (inbox-only delivery). |

## Exact Desktop Command Invocations

From the Windows workstation command prompt (`cmd.exe` or PowerShell), using existing `ssh.exe` and the `hetzner` SSH alias:

### Step 1: Send Ping from Windows
```cmd
python adapters\windows_client.py --alias hetzner send ^
  --workspace /home/alexey/git/agent-coordination ^
  --to agent-coordination-head ^
  --token AC-WIN-HETZ-001 ^
  --idempotency-key AC-WIN-HETZ-001 ^
  --origin-device windows-desktop ^
  --origin-tag windows-codex ^
  --body "AC-WIN-HETZ-001 desktop to Hetzner ping"
```
*(Alternatively, use `--stdin-rpc` to stream structured JSON over SSH stdin, eliminating shell quoting issues).*

### Step 2: Poll Inbox from Windows
```cmd
python adapters\windows_client.py --alias hetzner poll
```

### Step 3: Acknowledge Message from Windows
```cmd
python adapters\windows_client.py --alias hetzner ack <RECEIVED_MESSAGE_ID>
```

### Step 4: Typed Reply from Windows
```cmd
python adapters\windows_client.py --alias hetzner reply <RECEIVED_MESSAGE_ID> ^
  --token AC-WIN-HETZ-001-R ^
  --idempotency-key AC-WIN-HETZ-001-R ^
  --body "Semantic outcome confirmed from Windows"
```

## Evidence and Completion Standards

The test will be considered **Proven** only when:
1. Windows desktop terminal log or screenshot displays command invocations and formatted JSON receipts.
2. Hetzner-side mailbox transcript records the matching message ID with authentic metadata.
3. No secrets or SSH private keys were pasted or exposed during execution.
4. Pytest unit tests in `tests/` are explicitly recognized as protocol unit tests, not two-computer execution proof.
