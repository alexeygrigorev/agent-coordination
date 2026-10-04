# Cross-computer Agent Coordination

Fourth standalone product. Native cross-host coordination MVP under
implementation; old SSH mailbox wrappers are a baseline, not acceptance.

Head: `agent-coordination-head` (`81e8010c-89e4-478b-be3a-4ee6991607f3`).
Principal monitor: `codex-principal` (`93cf28f2-2872-411c-a5da-179e1b83b59f`).

## What this is

A stdlib Python SSH relay that talks to the **current installed aplexer**
on allowlisted computers. It resolves native catalogs at send time, keeps
durable message IDs with idempotency, and separates send receipt, recipient
read ACK, and semantic/action outcome.

Windows currently has no local aplexer. Both directions use Windows-initiated
`ssh.exe`. The SSH bridge identity is not the originating agent.

## Layout

- `coordination/` stdlib relay, registry, catalog, guards, cursors
- `adapters/` CLI and Windows client
- `tests/` unit tests with fake transport (not two-computer proof)
- `docs/` topology, Cloudflare comparison, admission contract, desktop test
- `reviews/` independent reviewer verdicts
- `scripts/backup.py` private GitHub main mirror + remote restore

## Constraints

No new SSH keys, no secret copy, no Cloudflare spend, no Rust build/install
while the hold stands, no edits to dirty `~/git/aplexer` or the isolated
`cloudflare-aplexer-protocol` checkout until Antigravity-head ACKs a source
handoff.

Sibling Agent Bus (`/home/alexey/git/agent-bus`) is the aplexer-independent
message bus. This repo keeps SSH/device coordination and a checkpoint of
the stdlib bus core until a scoped extraction ACK. Histories are not moved.
