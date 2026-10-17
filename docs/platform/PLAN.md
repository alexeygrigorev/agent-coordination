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
  those writers. Shared-checkout `src/hub.ts` edits need the current owner’s ACK.
  Isolated worktrees use native context to verify disjoint physical paths;
  matching relative filenames across worktrees do not create an ownership hold.

## Current execution checkpoint

Hub main `6cf0c18` contains reviewed M1/F7/M2/M2b/M3/P3/pairing, portable
host storage and M5 bounded follow-up retirement. Canonical Agent Branches and
private remote restore match all 207 reviewed source hashes; both CLI help
checks and integration typecheck pass. Post-main Argon source review of
`16d66d6` is published in `10c65ff` after factual correction `a5685ed`.
Its two Low host workflow findings are assigned to task0425 for bounded local
binding repair and a truthful migration runbook; enrollment stays unchanged. M5 exact source
`212560b` received Grok SCOPED ACCEPT `34ee3d0`: the five original defects and
R2 retirement gap are repaired. Target read cursors remain unchanged and system
follow-ups remain eligible for native delivery. Physical M5 is still open.
M4 repaired candidate `7b6f7ff` in task0422 received Argon acceptance `fc5bd30`
after four findings in `ab3b953`. Codex is composing its shared retention code
with M5 main; the resolved source needs a new independent review. M7 `abd48b8`
was rejected for a same-date cross-project duplicate intent after lease expiry.
Repaired `275c84a` is in task0423 with 30 role and two identity passes; distinct
Grok review is active. M9 task0424 has a Grok worker implementing a bounded authenticated
receiver, host sanitizer and dakit views against read-only Dashboard reports;
early receiver `738f45e` is in the actual fork/WIP, with adapter, UI and tests
still in progress. Producer ownership/adoption remain pending.
M4/M5/M7/M8a/M8b/M9/M10/M11 remain
in scope. New intake milestone M12 below is also required; it does not replace
the existing milestones.

## Milestone map

| ID | Outcome | Current source / next owner |
|---|---|---|
| M1 | Authenticated conversation API and F7 registry | Integrated on Hub `7929a1b`; post-main Argon gate recorded in `10c65ff` |
| M2 | dakit conversation UI | Integrated on `7929a1b`; physical adoption remains separate |
| M3a / M3b | Public CLI and genuine native inbox participation | POSIX and portable Windows source integrated on `16d66d6` after corrective audit; own-session POSIX round trips verified, physical Windows unproven |
| M2b | Fleet, sign-in and device views use dakit | Integrated on `7929a1b`, official kit lock preserved |
| M4 | Canonical task/review/outcome links in both directions | Task0422 candidate `7b6f7ff` accepted by Argon `fc5bd30`; composition with M5 needs review; routing ACK pending |
| M5 | Safe scheduled follow-ups and physical acceptance | Source `212560b` accepted in `34ee3d0`, integrated/restored as `6cf0c18`; physical acceptance remains |
| M6 | Ownership-aware launch admission | Already integrated before the conversation bundle; regression compatibility preserved |
| M7 | Configured roles and epoch-fenced job effects | Task0423 repaired `275c84a` under Grok review after `9574242` REVISE; actual backend remains M8b |
| M12 | Capture intake, assign tasks and preserve orchestrator handoff context through CLI/API; backfill existing work | New requirement; phased source work and Argon review required, actual routing/session linkage and backfill remain acceptance gates |

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
- Windows participation requires portable transitive imports, private NTFS
  journals, verified Win32 handle/ACL/no-follow behavior, bounded locks with
  process-death release, and atomic recovery that preserves P3 uncertainty and
  cursor rules. Linux contract tests and a skipped real-Windows check establish
  source evidence only. After distinct source review, a genuine Windows owner
  must prove public login, enrolled native identity, bidirectional messages,
  offline/reconnect dedup, reply and gap reconciliation on the physical host.
  Keep Windows root stood down and preserve rollback until that handoff; this
  physical gate also belongs to M11.
- Check journal-parent privacy before host adoption. The composed POSIX backend
  holds on a group/world-accessible journal parent; the isolated composition
  fixture required changing its own `.local` from `0775` to `0700`. Any existing
  workspace needs its owner's acknowledged metadata change; do not relax the
  backend, recursively chmod contents, move/reset journals, or silently alter
  a shared production workspace to make acceptance pass.

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
- Notification defaults to a durable native inbox only, without PTY or
  composer writes. Extend existing checks to query conversation read
  watermarks; the current 1:1 bus backlog query cannot detect conversation
  unread state. Any future opt-in terminal wake needs its own reviewed
  stable-idle/empty-draft and single-attempt uncertainty guards. Fenced
  principal-wake belongs to M8b; M5 does not close contest issue 102.
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

Retention gaps are part of native bridge acceptance. The bridge must preserve its
fail-closed default when history is incomplete and provide an explicitly
authorized catch-up path or durable gap notice before advancing its local cursor.
Test pruned prefixes and interior gaps against the real API metadata, preserve
retained unread messages, and never silently label skipped history delivered.

The early post-M6 Argon direction acceptance does not close the required working
conversation review. Keep `GATE-CONV-REVIEW` open until accepted M1/F7/UI/CLI/native
source is integrated and the real composed Worker, browser, CLI and own native
inbox round trip is verified. Then run an independent Argon review against that
exact integrated source before declaring the conversation path accepted.

1. `git fetch` and rebase on current `origin/main`; re-run the milestone
   tests.
2. Preserve hub-zai’s shared-checkout files and live ops (`src/hub.ts`,
   `src/env.ts`, deploy/enrollment); an actual physical overlap needs ACK.
   Isolated worktrees with native `a context` showing zero overlap may implement
   and integrate already authorized source. Do not infer peer agreement or
   modify the shared checkout to make it follow remote main.
3. No overlap with routing policy/placement without ACK.
4. dakit uniformity session: no new raw palette in hub CSS.
5. Resource: worker ≤1500M, scratch under the worktree `.local/tmp`, no
   `/tmp`, no shared-checkout edits, no worktree deletion of peers.
6. Independent reviewer inspects the same candidate SHA with a distinct
   identity and model.

## Remaining integration milestones

M1–M5 are the first conversation release, not the whole backlog. The reusable
unfinished plans below remain in this platform roadmap. A dependency hold is
not a delivered integration. Each milestone needs a scoped implementer, a
different-model pinned review, tests, and a normal main push. File ownership
must be agreed through the bus before implementation; this roadmap grants none.

| ID | Shippable result and acceptance | Dependencies |
|---|---|---|
| M2b | Adopt the existing dakit package in fleet, sign-in and device-pairing views. Preserve routes and auth behavior; render authenticated/expired/error states on desktop/mobile in both themes. Kit lock and semantic color/border checks pass. Coordinate with the separate dakit uniformity session; missing shared components become dakit needs. | M2; shared `hub.ts`/fleet scope agreement. No dakit source fork. |
| M6 | Enforce existing ownership claims before editable task placement/launch. Associate configured workspace/project and requested edit scopes with the authenticated holder, and consult the existing claim authority in the admission transaction. Test overlapping/ancestor scopes, expiry, claim/offer races, missing edit scope, foreign holders, and unchanged read-only routing. A failed check creates neither launch nor capacity reservation. Record that admission declarations do not sandbox later filesystem writes. | M1/M4 references; routing/fleet owner agreement. |
| M7 | Generalize existing epoch-fenced leases to configured automation roles, reusing root lease semantics and the reviewed coordination reference. Effect authorization and epoch check share a transaction; a partitioned former holder cannot renew or act. Test takeover, reconnect, expired holder, stale epoch and repeated completion. Keep Win35 root stood down; no new quorum authority or silent conversation-membership takeover. | M6; explicit role configuration and independent fencing review. |
| M8a | Qualify maintained host execution: launcher plan/receipt proves the actual account, profile, provider, model and effort selected, with fresh quota and resource evidence. Unknown attribution holds instead of guessing. Test shared-account capacity across hosts, profile mismatch, expired observations and uncertain effects. Coordinate necessary launcher changes with its owner; preserve ordinary Git restore. | Existing routing contracts; launcher owner scope agreement. |
| M8b | Add supported writer-run, principal-wake and head-recovery job profiles to the existing host dispatcher and checks. Jobs carry approved actions and fenced role custody, preserve drafts, reconcile uncertain starts, and continue through independent outcome review. Prove two useful controlled cycles plus worker/reviewer/host interruption before claiming unattended recovery; issue 102 stays open until its actual gates pass. | M7/M8a; existing custody and runtime gates. |
| M9 | Connect existing Dashboard accounting producers to authenticated bounded hub metrics ingestion and dakit views. Preserve 24 hourly UTC buckets, source coverage, accepted outcomes and known/unknown token fields; quota percentages never become token counts or money. Reject foreign-host writes and oversized/private payloads. Keep raw transcripts and metrics evidence host-local. | M2b; producer owner agreement; existing sanitized quota contract. |
| M10 | Make follow-through visible in conversations: reference canonical GitHub/routing tasks, owner acceptance, first-action evidence, due obligation, pinned independent review, accepted outcome and human delivery as distinct facts. Adapt existing ask-ledger/supervision records and existing checks instead of a second tracker or scheduler. Test duplicate/late replies, crash between state and notification, missing reviewer/owner, revoked membership, restart and an overdue obligation producing one safe inbox follow-up. | M4/M5/M8b; tracker and host-adapter contracts. |
| M11 | Verify supported host adoption and migration using the reviewed source. Complete an actual human/agent exchange with reconnect, native replies, routed task/outcome link and due follow-up on genuinely enrolled machines. Test a second physical host when available; retain partial acceptance labels otherwise. Move each old timer/service only after replacement proof and an acknowledged operations handoff, with rollback and an independent restore check. | M1–M10 as applicable; deployment/enrollment custody and explicit operations authorization. |

The first post-milestone Argon review checks both the working conversation
path and this remaining roadmap. It cannot turn allocated tasks, local unit
tests, or named owners into runtime delivery. Later milestones may ship in
smaller independently reviewed parts; their acceptance requirements stay open.

| Survey item | Integration/disposition |
|---|---|
| Claims in launch admission | M6; current claims endpoint remains the authority. |
| Generic role failover | M7; use coordination source as reference, keep root stand-down and epoch fencing. |
| Launcher account/profile labels | M8a; required for genuine existing fleet execution, not an assumed host capability. |
| Writer-run / head-recovery / principal-wake | M8b; no old service retired from source-only evidence. |
| Accounting producers → hub metrics | M9; compatibility collectors remain until ingestion/coverage acceptance. |
| Request-to-outcome / ask-ledger / turn-end obligations | M10; host adapters and canonical task references, not a parallel tracker. |
| Domain, host enrollment, token absence, migration | M11 operations dependencies; do all code/review/restore preparation before requesting a concrete final operations approval. Historical bus results remain historical. |
| Agent Branches provenance | Use real task forks/WIP during development and synchronize accepted main with independently recoverable Git. Keep Branches a separate product. |
| Contest-specific Git adapter, artifacts backend, recordings/publication | Keep as contest/product evidence and link where useful; do not turn the conversation hub into a second Git hosting or publishing system. No contest submission or social posting from this plan. |
| Quorum | Drop: the hub Durable Object is the existing authority; duplicating it would conflict with the deployment architecture. |
| Screen auto-Enter | Drop: native durable inbox delivery replaces typing into busy or unknown terminals. |

## M12 — Intake becomes tracked, assignable work

**Source.** Alexey’s intake brief, received 17 October 2026
(`hub-intake-brief.md`). This extends the conversation-platform goal. Capture
requests from chat, voice notes and forwarded asks so assistants can find open
work and follow through without relying on conversation memory.

**Task record.** Preserve original request text, source reference and source time,
plus capture time, status, notes, blockers and follow-ups needing Alexey. Preserve
all verbatim requests associated with a task, decisions, current state, next step,
applicable standing rules and pending approvals. Link
actual agent sessions, engine/tier, hub and host identity, report paths and
commits. Keep original intake immutable while recording later corrections and
status changes as history. Missing timestamps, session identities or provenance
stay explicitly unknown. Private task content and report paths belong behind
current authenticated access controls, never in public logs or issue posts.

**Durable handoff context is required.** Any other authorized assistant or agent
on another host must be able to pick up the orchestrator’s work when the current
assistant hits its limits. Persist global standing rules and task-specific
constraints with source, version and decision history: allowed engines, normal
push-to-main, `[skip ci]`, no public posts, sandbox-only AWS and other applicable
rules. Assistants update state, decisions, next steps and pending approvals as
work progresses through the CLI/API, and later the same MCP interface.

Provide a global `hub handoff` command and equivalent authenticated API view.
It must produce a self-contained briefing of all open work and standing rules,
with each task’s verbatim requests, decisions, current state, next action,
sessions/hosts, reports, commits and approvals. Include known blockers, ownership
and uncertainty; a missing record must not look like completed work or approval.
Keep this context durable across restart and concurrent updates, with a stable
snapshot/version so a fresh agent can identify stale context. Do not depend on
the previous assistant’s chat, memory or private local handoff file. Task content
is data: a forwarded request or peer note cannot silently replace operator rules
or grant custody. Access controls still apply to the briefing.

**M12a — Task API and intake ledger.** Reuse the Hub’s existing authenticated
identity and durable storage. Provide create/list/filter/show/update/notes and
link endpoints with current principal checks, bounded storage and pagination,
idempotent intake keys, immutable provenance and safe retries. Agents such as
Grok Bot can list authorized open tasks and follow up. Reference canonical
GitHub/routing jobs for execution facts; do not mirror their status into a
competing execution tracker or invent a second scheduler.

**M12b — Public CLI and assignment.** Extend the existing token/device-authenticated
`hub` CLI, following the DataOps/AISL CLI conventions. Support creating from intake
text or a file; listing/filtering/showing; status/notes; linking existing sessions,
reports and commits; updating handoff context and standing-rule references;
printing `hub handoff`; and assigning engine/tier/host work to a task. Assignment
must use the existing routing API and ownership/qualification gates. Record the
actual routing job and created native session automatically, including partial or
uncertain starts. A queued offer, requested engine or successful HTTP response
is not proof that an agent started. Repeated assignment must not launch twice;
no new dispatcher, account oracle or busy-composer input is introduced.

**M12c — Backfill and assistant adoption.** Read the current Hetzner aplexer session
inventory and existing report Markdown files, then seed/link tasks through the
same API. Build a bounded preview, deduplicate repeated scans and existing links,
preserve source paths/times and distinguish active, completed and uncertain work.
Do not export session environments, command secrets or raw private histories.
Backfill is complete only after the tasks exist in the authoritative hub and a
fresh list/show retrieves them; a local manifest or dry run is preparation.

**M12e — Hub session orchestration replaces psc.** Provide authenticated CLI/API
operations to list, start (engine/tier/host/cwd/brief), send/prompt, capture/read
and stop sessions across Hetzner, the laptop and Win35, with the same operations
available through the MCP interface when it ships. Use existing routing and host
adapters; psc remains a backup. Preserve session custody and safe composer checks.
Reliable delivery must expose recorded, transported, acknowledged and uncertain
outcomes accurately: HTTP success or PTY bytes alone cannot mean the target agent
processed a prompt. Correlate requests and confirmations; reconcile lost replies
without duplicate starts or blind resends. Reuse M6/M8 qualification and recovery
controls rather than adding another launcher or weakening an unresolved gate.

**M12d — MCP follow-up.** Keep the API suitable for the later MCP hub at
`mcp.dtcdev.click`. Track MCP exposure separately; do not claim that shipping the
HTTP API has installed or deployed an MCP integration.

**Acceptance.** Use focused real-HTTP/SQLite and CLI tests for access controls,
provenance, filtering, deduplication, pagination, updates and linked evidence.
Verify actual existing routing creates one genuine session and attaches it to the
task; test lost responses, restart/reconciliation and rejected assignments.
Prove assistants can retrieve open tasks, persist a follow-up and update handoff
context as they work. Test a fresh agent given only normal authenticated hub
access and `hub handoff`: it must recover the full open-work briefing and
applicable rules, identify the next action and continue an authorized task
without the old chat or local STATE file. Test concurrent context updates,
stale snapshots, revoked access and pending approvals without duplicate work.
Run a real
bounded session/report backfill and reconcile counts against the source inventory.
Demonstrate an assistant on the Grok Bot box performing the full hub CLI/API
start -> send -> confirm-delivered -> capture -> stop loop against a real
throwaway session on Hetzner. Verify the actual prompt and captured response,
then verify the intended session stopped. Cover unavailable hosts, lost replies,
revoked access and uncertain delivery without silent drops or unsafe retries.
Track laptop/Win35 adapter qualification separately; the Hetzner demonstration
does not prove those hosts work. MCP acceptance follows its separately delivered
interface. This session-control scope is required alongside task assignment and
handoff, not satisfied by a task CRUD API.
Obtain Argon review on the exact implementation and act on its findings before
normal main integration. Token/device auth, workspace ownership, private recovery
and the physical/runtime gates remain in force.

**Dependencies and sequence.** Task CRUD, CLI and fixture-based backfill work can
proceed independently. Real assignment depends on routing-owner compatibility and
M6/M8a/M8b as applicable; adoption/backfill depends on the accepted API being
available. M10 consumes these task records for follow-through rather than adding
another intake ledger. Keep each phase independently owned and reviewed, while
retaining assignment, actual backfill, assistant adoption, demonstrated
orchestrator handoff and cross-host session orchestration in M12’s full scope.

## What this plan will not do

- Duplicate FileBus, SSH relay, ChannelDO, or Agent Relay.
- Move contest Agent Branches into the hub.
- Archive predecessor repos (GitHub notices already exist; local checkouts
  lag).
- Deploy, change DNS, rotate tokens, or stop systemd timers.
- Claim physical multi-host delivery from unit tests.

## Next actions

1. Portable Windows source is published as `16d66d6` after corrective audit
   `e5133fc`; canonical/private restore against all 203 hashes passed. Preserve
   original reports and native journals. Physical Windows owner tests, enrollment
   and adoption remain M3b/M11 gates; source acceptance does not close them.
2. Preserve the published post-main Argon review and factual correction in
   `10c65ff`; address the two verified Low host workflow findings in a bounded
   follow-up. Its source verdict does not close deployment or multi-host gates.
3. M5 source is accepted, integrated and privately restored as `6cf0c18`.
   Preserve its current-slot fences, unresolved intents and fair bounded cleanup.
   Physical scheduled follow-up/native delivery remains an acceptance obligation.
4. Complete M4/M5 composition and independent review after M4 source acceptance
   `fc5bd30`; preserve both retention lifecycles and verify shared budgets and
   rollback. Annotate the report's one historical table error before publication.
   Coordinate routing compatibility ACK; silence is not an ACK. Finish distinct
   M7 review of `275c84a`, preserving task0423 ancestry and unresolved effects.
5. Compose accepted M4/M7 changes with M5 main, resolve shared conversation/
   retention/auth conflicts and independently verify any semantic merge changes.
   Continue M8a qualified execution, M8b recovery profiles, M9 accounting, M10
   follow-through and M11 physical migration with existing ownership gates.
   M9 task0424 is active on isolated Hub source; obtain the producer contract
   owner, review the sanitized adapter and receiver, and prove ingestion before
   claiming producer adoption.
6. Implement M12 intake/task API and CLI in scoped phases, coordinate the
   existing routing assignment contract, obtain Argon review and prove real
   session/report backfill. Keep actual assignment and assistant follow-up as
   acceptance gates; do not stop at a CRUD-only ledger.
7. Keep STATUS, the head report and private recovery checkpoints current after
   accepted milestones. Source and release commits carry `[skip ci]` and actual
   agent/model provenance; push normally to main without PRs or force-push.
   Preserve journals, peer checkouts, global tools and rollback evidence.
