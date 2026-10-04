# Maintainer intake: Agent Bus decouple

Recorded 2026-10-04 from principal messages
`01a106c3-aea2-7d93-abbc-b244ffb7d848` and `01a106c4-fb31-7f22-8d30-f50a2cb9f33c`.

Human request: extract the message bus from aplexer into an independent
project. Aplexer becomes an adapter/UI client. Working name Agent Bus.

- Sibling path (explicit): `/home/alexey/git/agent-bus`
- Private GitHub: `PocketShell-io/agent-bus` (principal bootstraps docs only)
- Head/integration owner: `agent-coordination-head` `81e8010c-89e4-478b-be3a-4ee6991607f3`
- No fifth team, no duplicate head, do not move/delete `agent-coordination` history
- Bus identities/credentials/device/project/task independent of terminal sessions
- Never forge an aplexer sender
- MVP: local durable register/send/inbox/wait/reply/ACK, idempotency, crash-restart
- First dogfood: two plain headless processes, real task+artifact, one restart/redelivery
- NoRust/install/dirty-aplexer hold remains; stdlib implementation authorized

Current checkpoint lives in this repo (`coordination/bus.py`, `bus_cli.py`,
tests). Scoped copy into the sibling happens after that repo exists and
after an explicit extraction ACK. Package rename after checkpoint, not a
destructive move.
