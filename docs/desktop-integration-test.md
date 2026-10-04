# Desktop integration action contract

Owner: `agent-coordination-head` (`81e8010c-89e4-478b-be3a-4ee6991607f3`).
Executor of the actual Windows commands: desktop-orchestrator / user, at
the real two-computer boundary. This document nominates the test; it does
not claim the test has run.

Environment (private `.local/desktop-environment.json`): Windows, no local
aplexer, `ssh.exe` present, bundled Python/Node present, allowed workspace
`work/agent-coordination`. No inbound Windows SSH. No new credentials.

## What would count as proof

1. Windows Codex -> Hetzner `agent-coordination-head`: ssh.exe typed send
   using `adapters/windows_client.py send`, native Hetzner catalog resolved
   at send time, durable message ID returned, originating agent recorded as
   Windows ssh-client (not a forged Hetzner session).
2. Hetzner -> Windows Codex: Hetzner queues or writes a mailbox item;
   Windows polls via ssh.exe; client displays exact message ID; read ACK
   is a separate Windows-confirmed step; semantic reply is a third step.
3. Offline retry: kill SSH after send, replay the same `--idempotency-key`,
   observe one durable ID (no duplicate body).
4. Cursor reconciliation: poll twice, process each ID once.
5. Negatives: unknown device, busy/working pane (no `--pane`), missing
   native Windows aplexer (do not invent a session), unregistered alias.

## Exact commands (narrow, reviewed, desktop-run)

From Windows, using existing `ssh.exe` and the hetzner alias already in
the user's SSH config. Do not paste secrets.

```text
python adapters/windows_client.py --alias hetzner send ^
  --workspace /home/alexey/git/agent-coordination ^
  --to agent-coordination-head ^
  --token AC-WIN-HETZ-001 ^
  --idempotency-key AC-WIN-HETZ-001 ^
  --origin-device windows-desktop ^
  --origin-tag windows-codex ^
  --body "AC-WIN-HETZ-001 desktop to Hetzner ping"

python adapters/windows_client.py --alias hetzner poll
```

Hetzner side expected evidence: `aplexer message inbox --json` as
`agent-coordination-head` showing that durable ID; reply with the same
token; `message ack ID`. Receipt != ACK != semantic reply.

## What is out of scope for this nomination

- Root running a busy composer injection
- Creating an inbound Windows SSH server
- Copying `~/.ssh` keys into the repo
- Marking localhost pytest as this test

Ask desktop through the native principal/desktop mailbox when ready.
Independent Hetzner work continues meanwhile.
