# Conversation platform plan

Small shippable milestones on Agent Hub. Survey evidence:
[STATUS.md](STATUS.md). Tracker:
[agent-hub#13](https://github.com/alexeygrigorev/agent-hub/issues/13).

This repository publishes the plan. Implementation happens in isolated
fresh-`origin/main` Agent Hub worktrees. Routing session owns
machine/model/task routing (`~/git/agent-hub/docs/ROUTING.md`, main
`213fcf6`). Conversation work calls that API. It does not add a second
dispatcher or a second bus transport.

## Constraints

- Reuse device/human auth, idempotency, and `hub bridge`. Keep `/api/bus/*`
  for 1:1 machine/role traffic. Conversation rows live in dedicated tables
  with atomic `seq` (no dual-write into `messages`).
- No new Durable Object, no Quorum, no SSH relay revival, no contest Worker
  changes, no aplexer-watch auto-Enter, no busy-composer input.
- UI uses dakit (`~/git/dakit`). File missing components as dakit needs.
- `[skip ci]` focused commits, fast-forward to hub main after independent
  review. No PRs, no force-push. No secrets, no public channel posts, no
  cloud or credential changes from conversation workers.
- Physical delivery requires host evidence. Tests are source evidence only.
- Existing host timers stay up until a replacement check is observed working.
- Platform already prepared hub worktrees `agent-hub-wt-platform-{api,cli,ui}`
  (Agent Branches tasks 0389 / 0390 / 0391; not accepted). Do not duplicate
  those writers. Shared `src/hub.ts` dispatch needs an ACK from the current
  hub owner before overlapping edits.

## Milestone map

| ID | Outcome | Depends on | Suggested worker (already allocated by platform) |
|---|---|---|---|
| M1 | Conversation API | Existing bus + auth | Antigravity `platform-api` |
| M2 | dakit conversation UI | M1 contract | OpenCode glm-5.3-flash `platform-ui` |
| M3 | CLI + inbox bridge | M1 contract; native `a message` | Codex `platform-cli` |
| M4 | Task/review/outcome links | M1 + routing (do not modify routing policy) | After M1; coordinate with `routing` |
| M5 | Safe pings + physical acceptance | M1–M4 source + host enrollment | After Argon post-milestone review |

Argon (deep tier) reviews this plan before M1 merge, and again after the
first integrated milestones. Prepared review worktree:
`~/git/agent-coordination-wt-platform-plan-review`.

## M1 — Conversation API

**Goal.** Authenticated humans and agents join named conversations, send
durable ordered messages, retry safely, and record inbox receipts.
Point-to-point `/api/bus/send` remains for machine/role addresses.

**Shape (dedicated store; no unsafe bus dual-write).**

- Dedicated tables: `conversations`, `conversation_members`,
  `conversation_messages` with a per-conversation monotonic `seq`. Optional
  `bridge_ref` records a native aplexer envelope id. Do **not** insert the
  same row into legacy `messages`. Bus `thread_id` is not the conversation
  store.
- Align with the API-worktree candidate
  `~/git/agent-hub-wt-platform-api/docs/CONVERSATIONS.md` after review:
  `/api/conversations`, membership, sequence pagination, verified self
  identity. Implementation files named by platform were not on disk when
  inspected. Dispatch wiring in `src/hub.ts` waits for hub-zai ACK. Draft
  is not accepted.
- Identity: human from verified session subject (`human:<sub>`); agent from
  verified device-flow actor. Refuse host/job/routing-client/`role:root`.
  No JSON/header sender override.
- Authorization: only current members read or write; non-members 403. An
  admin session is not blanket membership.
- Send: idempotency key per `(conversation_id, actor, key)` returns the
  original message and seq. Conflicting payload 409. Body size stays at the
  current bus limit (16 KiB).
- Receipts: per-member read cursor / unread count. Bus accept/complete stay
  optional later task stages, not “read”.
- List: ordered by `seq` with `after`/`before`; no long-poll in the Durable
  Object. Direct = exactly two members; group bounded.
- Cross-project same-tag isolation tests before implementation review.

**Acceptance.**

- Source tests: create/direct/group; member isolation; order; retry same key;
  conflicting key 409; unknown conversation 404; revoked token 401; human and
  agent senders; receipt does not mark accept/complete.
- Negative tests live next to `test/m3-http.test.ts` style HTTP cases.
- No change to routing tables or model policy.
- Independent review of the **same candidate SHA** by a distinct identity and
  model. Do not require a different commit.
- Docs: short contract in `~/git/agent-hub/docs/` (conversation section), not
  a new abstraction manifesto. Candidate `docs/CONVERSATIONS.md` in the API
  worktree is the starting contract.

**Out of scope.** UI, CLI verbs beyond a thin API client used by tests, host
bridge fan-out, wake-up, DNS, enrollment.

## M2 — dakit conversation UI

**Goal.** A signed-in human can list conversations, read ordered history, send
a message, and see unread state.

**Shape.**

- New authenticated page using dakit shell + `.dk-split` list–detail
  (`~/git/dakit/docs/shell.md`, `docs/list-detail.md`). Agent Hub is already
  named as an operator app in the family spec.
- Do not restyle `public/fleet.html` into a chat. Keep fleet as fleet.
  `public/index.html` “under construction” can link to fleet and
  conversations after both exist.
- Missing kit pieces (composer, receipt ticks, member chips) go to dakit as
  needs, then consume them. No one-off color/radius/type.

**Acceptance.**

- Rendered browser verification of list, empty, detail, send, unread, 403
  state, desktop and a narrow viewport. Screenshots are evidence of the
  session that drove the UI, not of production.
- Keyboard focus ring and no accent-border regressions (dakit family rules).
- Uses M1 API only; mock or wrangler-dev hub, not a fake second backend.

**Depends.** M1 routes frozen enough for the UI contract. Can start against
the M1 branch/worktree after the API schema is written, merge after M1.

## M3 — CLI and native inbox bridge

**Goal.** `hub` can create/list/send/read/ack conversations. Host bridge
copies conversation messages into existing aplexer inboxes for member agents
on that host.

**Shape.**

- CLI subcommands next to current `hub send/inbox/reply/ack` in
  `host/agent_hub_host/cli.py`. Same credential files, no new secret format.
- Bridge: extend `host/agent_hub_host/bridge.py`. Inbox-only by default
  (`a message send` without pane). Dedup on conversation message id and
  `bridge_ref`. Never `--pane` / Enter on busy, menu, draft, or unknown
  composers.
- Reconnect: unread conversation receipts catch up when the host agent runs
  `hub bridge --once`.
- Do not impersonate native session identity (`--from` remains forbidden).

**Acceptance.**

- Host tests with fake `a` binary (existing bridge test style): fan-out to
  two local tags, duplicate hub id applied once, busy target queued not
  typed into, native reply maps back to the same conversation.
- `hub conversation send` retry with the same key is a no-op.
- No global install; project-local venv only.

**Depends.** M1. Can proceed in `agent-hub-wt-platform-cli` against the M1
contract. Codex quota-gate wrapper already required by platform.

## M4 — Task, review, outcome linkage

**Goal.** A conversation can point at a routing job, and a job/review/outcome
can point at a conversation, without copying routing logic.

**Shape.**

- Optional `conversation_id` on `routing_jobs` **or** a small join table
  `conversation_links(conversation_id, kind, ref)` where `kind` is
  `routing_job` | `fleet_launch` | `review` | `outcome`. Prefer the join
  table so routing policy code stays untouched.
- Posting a link does not submit a task. Submitting a task does not create a
  conversation unless the client passes an existing id.
- Review/outcome: record launcher/hub terminal states already used
  (`done`/`failed`/`completed-awaiting-review`). Do not invent a new review
  engine. Repo `review_gate.py` stays at the git boundary.

**Acceptance.**

- Tests: member can attach/list links; non-member 403; unknown job 404;
  routing submit without a conversation still works (routing regression).
- Routing session ACK that policy, tiers, and placement files were not
  semantically changed (schema addition only, if any).
- Docs: one paragraph in ROUTING.md or the conversation contract, not a
  parallel task tracker.

**Depends.** M1 landed. Coordinate schema with `routing` before editing
`src/routing.ts` / `src/schema.ts` shared pieces.

## M5 — Safe pings, continuation, physical acceptance

**Goal.** Conversations are usable on a real enrolled host, with a safe
follow-up ping, without claiming unattended recovery that issue 102 still
owns.

**Shape.**

- Reuse scheduled checks (`src/checks.ts`) for `inbox_backlog` on a
  conversation actor. Optional `routine` check that sends one hub
  conversation message. No new scheduler.
- Wake: only `hub bridge` + existing aplexer `message deliver` at a verified
  idle empty prompt. Principal-wake from SPEC M5 stays a later recovery
  item; this milestone does not close contest issue 102.
- Physical acceptance on already-authorized machines: Hetzner host (already
  enrolled per prior reports) plus at least one human session. Win35/laptop
  host enrollment remains a hub operations task, not a conversation feature
  fake.

**Acceptance.**

- Source: check fires once per interval, duplicates suppressed, no pane
  write in tests.
- Physical: named host, named conversation, two members (human + agent),
  ordered messages after reconnect, inbox receipt recorded. Write the
  evidence path privately; public STATUS gets sanitized SHA/time only.
- Domain `hub.dtcdev.click` and missing host tokens are **dependencies**,
  not M5 work. If the workers.dev origin is what is actually enrolled, say
  so; do not pretend the custom domain exists.

**Depends.** M1–M3. M4 links optional for the physical conversation demo.

## Dependency checks before each merge

1. `git fetch` and rebase on current `origin/main`; re-run the milestone
   tests.
2. No overlap with hub-zai owned files without ACK (`src/hub.ts` dispatch,
   `src/env.ts`, live deploy).
3. No overlap with routing policy/placement without ACK.
4. dakit uniformity session: no new raw palette in hub CSS.
5. Resource: worker ≤1500M, scratch under the worktree `.local/tmp`, no
   `/tmp`, no shared-checkout edits, no worktree deletion of peers.
6. Independent reviewer inspects the same candidate SHA with a distinct
   identity and model.

## Unfinished planned work: milestone or disposition

The brief asked to integrate unfinished competition/hub plans. Items that
are not conversation features get an explicit owner and stay off M1–M5.

| Leftover plan | Disposition |
|---|---|
| Claims in launch admission | **Hold, hub fleet.** `/api/bus/claims` stays; wiring into `fleet.ts`/`routing.ts` is hub-zai/fleet work, not a conversation milestone. |
| Generic role failover | **Hold, compatibility.** `coordination/role_failover.py` remains source. Hub keeps root lease epochs only. Not M1–M5. |
| Writer-run / head-recovery | **Hold, hub SPEC M5 / operations.** Conversation M5 does not schedule the daily writer or recover heads. |
| Principal-wake / issue 102 | **Partial overlap with conversation M5.** Safe inbox ping and idle-empty `message deliver` are in M5. Unattended death recovery stays contest issue 102. |
| Accounting producers → `/api/metrics` | **Hold, dashboard compatibility.** Agent Dashboard collectors stay host-side until a separate hub metrics milestone. |
| Request-to-outcome / ask-ledger / turn-end obligations | **Hold host-side.** M4 links conversations to routing jobs and existing review/outcome states. It does not port `ask-ledger.py` or `tasks_guard.py`. |
| Custom domain / host token / launcher account labels | **Dependencies, not conversation features.** Platform/head DNS probe: `hub.dtcdev.click` unresolved and health unavailable (current). Historical 15-Oct bus tests remain separate evidence. |
| Quorum | **Drop** (hub Durable Object is the authority). Already in STATUS. |
| Screen auto-Enter | **Drop** (hub never types into terminals). |

## What this plan will not do

- Duplicate FileBus, SSH relay, ChannelDO, or Agent Relay.
- Move contest Agent Branches into the hub.
- Archive predecessor repos (GitHub notices already exist; local checkouts
  lag).
- Deploy, change DNS, rotate tokens, or stop systemd timers.
- Claim physical multi-host delivery from unit tests.

## Next actions

1. Argon reviews STATUS + this PLAN. Survey repairs findings in
   `docs/platform/` only.
2. Platform keeps API/UI/CLI workers in their existing hub worktrees;
   survey does not start agents.
3. After Argon ACK of the plan, M1 lands first with tests and a pinned
   review, `[skip ci]`, fast-forward hub main.
4. M2 and M3 merge behind M1. M4 after routing ACK. M5 after a real
   conversation on an enrolled host.
5. Update this STATUS incrementally as each SHA lands. Do not push
   coordination docs until Argon review and head approval.
