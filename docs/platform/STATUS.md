# Conversation platform status

As of 2026-10-17. Survey owner: `platform-survey` (Grok) in isolated worktree
`~/git/agent-coordination-wt-platform-survey` from `origin/main` `98857ca`.
Implementation target is Agent Hub (`~/git/agent-hub`, GitHub main `213fcf6`).
This repository is deprecated for standalone orchestration (`762c349`) and owns
the cross-project survey and plan. Product code belongs in Agent Hub
([issue 13](https://github.com/alexeygrigorev/agent-hub/issues/13)).

Evidence classes used below:

- **source**: committed files and tests at a named revision.
- **runtime**: a prior measured host/Worker observation recorded in a named
  report. This survey did not re-probe production, timers, DNS, or dashboards,
  and did not read credential, config, or log files.
- **partial**: source exists, runtime acceptance is missing or incomplete.
- **planned**: documented intent without matching source on current main.

Unit tests are not physical delivery. Passing vitest/unittest counts are source
evidence only.

## 1. Product map

| Product | Checkout | GitHub main observed | Role in a conversation platform |
|---|---|---|---|
| Agent Hub | `~/git/agent-hub` at `213fcf6` | `213fcf6` | Control plane: auth, bus, registry, checks, fleet, routing, dashboard |
| Agent Coordination | `~/git/agent-coordination` at `98857ca` | `98857ca` | Deprecated SSH/role-failover source; this survey/plan |
| Agent Bus | `~/git/agent-bus` local `bf351f4` | `a9156b9` (deprecation notice) | FileBus predecessor; do not duplicate |
| Agent Dashboard | `~/git/agent-dashboard` local `6863b99` | `3f126df` (deprecation notice) | Accounting views; hub fleet page replaced operator UI |
| Agent Quota Launcher | `~/git/agent-quota-launcher` local `53c7b2e` | `5145d0d` (orchestration deprecation) | Remains the headless executor |
| Agent Relay | `~/git/agent-relay` at `0a2895b` | `0a2895b` | Unrelated FastAPI task starter; leave untouched |
| Cloudflare contest | `~/git/cloudflare-agent-git` local dirty/behind | `0a95aa1` | Contest entry, process, recovery, timers |
| Agent Branches | `~/git/agent-branches` detached `a35c4bd` | `82e310f` | Separate Git-coordination product |
| aplexer | `~/git/aplexer` (dirty shared tree; do not edit) | — | Native same-host sessions and inbox |
| aplexer-watch | `~/git/aplexer-watch` `837edff` | `837edff` | Auto-Enter helper; hub must not type into terminals |
| dakit | `~/git/dakit` `103912d` | `103912d` | UI kit for conversation UI |

Routing session `agent-coordination:routing` owns machine/model/task routing.
Conversation work reuses that contract. It does not replace it.

## 2. Contradictions in the starting reports

Verified against current source, GitHub, and git history. Starting files:
`~/tmp/agent-reports/hub-feature-inventory.md`, `agent-hub-generic.md`,
`agent-hub-status.md`, `hub-routing.md`, plus `agent-messaging-status.md`.

1. **Hub HEAD.** Generic hub report pins main at `f571f43` (15 Oct, CI added).
   Current GitHub and local main are `213fcf6` (16 Oct routing + fair queue).
   Between them: `f5efc43` (default liveness alerts to `grok-bot` when
   `HUB_ALERT_TO` is unset), `14f7e22`, `1544862`, `bc1ae5c`, `213fcf6`.
2. **hub-zai uncommitted patch.** `agent-hub-status.md` (16 Oct morning) says
   the grok-bot alert default is uncommitted on `f571f43`. That change is
   already on main as `f5efc43`. Shared `~/git/agent-hub` is clean at
   `213fcf6`.
3. **Deprecation notices.** Generic report claimed README deprecation commits
   on dashboard `3f126df`, bus `a9156b9`, launcher `5145d0d`, private launcher
   `f7e920a`, coordination `762c349`. GitHub has those commits. Local
   dashboard/bus/launcher checkouts do not contain them: their working READMEs
   still describe standalone products. Coordination local and GitHub both have
   `762c349`. Local trees are stale or divergent, not proof the notices were
   never pushed.
4. **SPEC tracker vs source.** Agent Hub issue 1 still has M0–M7 unchecked.
   Source on `213fcf6` includes M0–M4 tests (`test/m1-*`, `m2-registry.test.ts`,
   `m3-bus.test.ts`, `m3-http.test.ts`, `m4-*.test.ts`), fleet/liveness/checks,
   quota snapshots, and routing. Issue 13 already tracks this conversation
   platform. Issues 5–12 remain OPEN even where source exists.
5. **Bus path name.** SPEC §2 said replace Agent Bus with `/api/messages`.
   Implemented routes are `/api/bus/send|inbox|reply|messages|claims`
   (`~/git/agent-hub/src/hub.ts`). Coordination AC59 kit documents the same
   `/api/bus/*` contract (`docs/ac59-hub-bridge.md`).
6. **Deploy assumption.** SPEC (11 Oct) assumed Workers Free, local-only until
   M7, and “no custom domain needed”. `docs/DEPLOY.md` records a deployed
   Worker on the workers.dev origin, crons `*/30` (root slot, scheduling off)
   and `*/5` (checks). Intended `hub.dtcdev.click` is still a DNS/TLS/access
   gap (routing report and DEPLOY.md agree). This survey did not resolve DNS.
7. **Product count.** Contest `AGENTS.md` still frames four products.
   `_docs/02-projects.md` lists five, adding Agent Bus. Hub generic report
   treats bus/dashboard/coordination as superseded predecessors.
8. **Worktrees.** `_docs/team/05-implementer.md` forbids git worktrees. Latest
   user brief for this task authorizes isolated fresh-origin/main worktrees and
   aplexer workers. That brief wins.
9. **“Merged and deployed” vs live routing.** Feature inventory marks checks,
   liveness, dashboard, and bus as merged and deployed. Routing report
   (`hub-routing.md`) is explicit that **live task routing is not deployed**:
   custom domain unresolved, host access token missing, launcher account
   labels missing. Those two reports describe different layers. This survey
   does not claim a current production probe.
10. **Test counts.** Messaging report: 251 Worker + 555 host tests at
    `f571f43`. Routing report: 276 Worker + 561 host at `213fcf6`. Current
    tree has 29 Worker test files under `~/git/agent-hub/test/` and 23 host
    test modules under `~/git/agent-hub/host/tests/`. Counts were not re-run
    here.
11. **Claims vs launch.** Inventory correctly says `/api/bus/claims` rejects
    overlapping scopes and is not wired to launch admission. Confirmed: no
    `claims` references in `src/fleet.ts` or `src/routing.ts`.
12. **Dirty role-failover worktree.** Generic report left
    `~/git/agent-coordination-role-failover` untouched. It is still dirty on
    `codex/role-failover-20261006` at `30df32a`. Do not edit it.
13. **Contest HEAD.** Local `~/git/cloudflare-agent-git` is dirty, one commit
    ahead and 68 behind `origin/main`. GitHub main is `0a95aa1`. Local is not
    the contest source of truth.

## 3. Agent Hub — shipped source versus runtime versus gaps

Revision: `213fcf6` “Keep unmatched tasks from starving ready queue work
[skip ci]”. Docs: `docs/SPEC.md`, `GENERIC-HUB.md`, `DEPLOY.md`, `ROUTING.md`,
`QUOTA.md`, `ROOT-DISPATCH.md`.

### 3.1 Auth, registry, host client (SPEC M0–M2)

**Source.** DTC OIDC + admin-token sign-in, CSRF, device-flow pairing, hashed
credentials, machine registry, heartbeats (`src/auth/`, `src/schema.ts`,
`src/registry.ts`, `host/agent_hub_host/`). Issues 2–4 are CLOSED.

**Runtime (prior reports).** Dashboard and APIs require sign-in. Hetzner
enrolled as a host with a one-minute fleet-host timer. Win35 used as a paired
**agent** for messaging tests, not enrolled as a host. Laptop and Grok Bot box
not enrolled. Not re-verified this session.

**Partial.** Interactive `start-session` needs per-machine `admission_argv`.
Headless launches wait for launcher plans that report account labels
(`docs/GENERIC-HUB.md`). Routing report: Hetzner host config has a base URL
without an access token and without headless launcher/model/admission routes.

### 3.2 Point-to-point bus (SPEC M3)

**Source.** `src/bus.ts` + `/api/bus/*` in `src/hub.ts`: send, inbox, show,
reply, ack, accept, complete, claims, actor list. Durable rows with
`thread_id`, `idempotency_key`, 30-day expiry, ULID ids. CLI:
`hub send|inbox|show|ack|accept|complete|reply|claim|release|claims|bridge`
(`host/agent_hub_host/cli.py`). Bridge:
`host/agent_hub_host/bridge.py` maps hub messages into native `a message`
mailboxes, preserves busy/draft rules, normalizes `sync_reply`. Tests:
`test/m3-bus.test.ts`, `test/m3-http.test.ts`, `host/tests/test_bus.py`,
`test_bridge.py`.

**Runtime (prior reports, 15 Oct).** Hub production Hetzner↔Hetzner and
Win35↔Hetzner request/reply and burst tests succeeded; idempotency and
foreign-sender 403 recorded. Native same-host `a message` 60/60. Old SSH
typing path delivered anonymously and broke native replies. Recipient
registration bug fixed in `c062b9d`.

**Not a conversation on main.** Messages are 1:1 actor addressing (`tag`,
`project:tag`, `role:…`, `machine:…`). There is no members set, no human+agent
group, no unread cursor per member, no conversation-scoped ACL. `thread_id`
is a reply-chain grouping, not a first-class conversation. Dashboard has no
bus/conversation page (`public/fleet.html` sections: alerts, liveness, checks,
registry, start work, machines, hub agents, sessions, registered agents).
`public/index.html` still says “under construction”. `public/fleet.css` is
ad-hoc system-ui CSS, not dakit.

**API candidate (not accepted).** Platform Antigravity worktree
`~/git/agent-hub-wt-platform-api` has untracked `docs/CONVERSATIONS.md`.
That draft uses dedicated `conversation_messages` plus atomic `seq` and
optional `bridge_ref`, with no dual-write into `messages`. Named
`src/conversations.ts` and `test/conversations.test.ts` were **not** present
when inspected. Shared hub dispatch remains unwired pending hub-zai ACK.
Agent Branches task 0389.

### 3.3 Scheduler, leases, checks, liveness (SPEC M4–M6 partial)

**Source.** Root jobs/leases/offers (`src/jobs.ts`, `src/root_scheduling.ts`);
root scheduling flag default documented as enabled in README and switched
**off** in DEPLOY.md for the live Worker. Scheduled checks (`src/checks.ts`):
liveness, quota, http, inbox_backlog, routine; actions alert, hub message, or
launch. Liveness and alerts (`src/liveness.ts`). Fleet accounts, routes,
subscriptions, sessions, launches (`src/fleet.ts`). Sanitized quota snapshots
(`src/quota.ts`, `docs/QUOTA.md`). Oversight ledger exists in host tests
(`host/tests/test_oversight.py`); inventory says it has no poller.

**Runtime (prior reports).** Five-minute checks cron deployed; Hetzner
heartbeats reported. Alerts show on the dashboard. Inbox/webhook delivery
needs `HUB_ALERT_TO` / `HUB_ALERT_WEBHOOK` (now defaulting to `grok-bot` in
source when unset). Host-side principal-ping, headless-root, and supervisor
timers were still running; migration is one-at-a-time and not claimed done.

**Partial / planned.** SPEC M5 writer-run, head-recovery, principal-wake: not
accepted as runtime. Generic role failover for arbitrary roles: not built
(only root lease epoch fencing). Claims not in launch admission. Daily writer
not switched onto hub checks.

### 3.4 Task routing (owned by session `routing`)

**Source, reviewed, on main `213fcf6`.** `src/routing.ts`,
`src/model-routing.ts`, `config/model-routing.json`, `docs/ROUTING.md`,
`host/agent_hub_host/routing.py`. Capability ads, tiers deep/daily/quick,
queued placement, batches, idempotency, client tokens scoped to
`routing:submit`, sanitized PNG artifacts, fair queue so unmatched needs
cannot starve ready work. Independent Gemini reviews recorded in
`hub-routing.md` at `1544862`, `bc1ae5c`, `213fcf6`.

**Runtime.** Live routed-task acceptance is **not** claimed. Domain, host
token, and launcher account-attribution remain rollout blockers. Conversation
milestones must call this API rather than invent a second dispatcher.

### 3.5 Historical hub worktrees

`git worktree list` on Agent Hub shows many leftover
`.local/delivery-6e96/worktrees/*` branches from SPEC M3/M4/M6 delivery.
Platform conversation worktrees `agent-hub-wt-platform-{api,cli,ui}` exist at
`213fcf6`, clean vs `origin/main` when inspected. They are candidates, not
accepted milestones. Do not edit shared `~/git/agent-hub`.

## 4. Predecessor repositories

### Agent Coordination (`98857ca`)

Deprecated README points at Agent Hub. Remaining source is still useful as
compatibility:

- SSH relay / catalog / guards: `coordination/ssh_relay.py`, `catalog.py`,
  `guards.py`, `adapters/aplexer_ssh.py`
- Role failover (source, reviewed, not autonomous runtime):
  `coordination/role_failover.py`, `failover_bridge.py`,
  `ql_consumer_fencing.py`, `docs/ROLE-FAILOVER-RUNTIME.md`
- Quorum prototype (inventory decision: drop; hub DO is the authority):
  `coordination/quorum_authority.py`,
  `research/coordination/ROLE-FAILOVER-QUORUM-PROTOTYPE.md`
- AC59 HTTP FileBus adapter and hub-shaped `/api/bus/*` loopback:
  `ac59_service/`, `docs/ac59-hub-bridge.md` (claims return 501)
- Outbound host kit: `docs/hub-outbound-host.md`, `adapters/hub_outbound.py`
- Independent reviews under `reviews/`
- `coordination/TASKS.json` local tracker (do not publish contents)

Open GitHub issues include cross-host messages (#59), supervisor continuation
(#61), and a cluster of role-failover issues (#42–#46). Messaging #59 is
partially superseded by hub bus runtime reports; physical three-host
enrollment is still open.

Dirty worktree `~/git/agent-coordination-role-failover` at `30df32a` must stay
untouched.

### Agent Bus (GitHub `a9156b9`, local `bf351f4`)

FileBus plus sessionless headless consumer (`coordination/bus.py`,
`worker_bus.py`, `headless_worker.py`, `model_bus_consumer.py`). Intake
(`docs/maintainer-intake-20261004.md`) asked for two-process then two-host
acceptance. README on GitHub is deprecated in favor of the hub bus. Local
checkout is behind GitHub and dirty. Do not start a second transport.

### Agent Dashboard (GitHub `3f126df`, local `6863b99`)

Python hourly utilization, accounting, feature tracking, localhost preview.
GitHub README deprecated. Local is ahead of its `origin/main` and behind
GitHub. Hub fleet page absorbed operator views; accounting collectors remain
compatibility producers until a metrics post is accepted (SPEC M6).

### Agent Quota Launcher (GitHub `5145d0d` deprecation of **orchestration
entry points**, local `53c7b2e`)

Still the maintained executor: `submit` / `plan` / `run`, quse admission,
systemd task units, lifecycle through review. Hub placement must keep using
it. Outstanding: account-attributed plan fields required by the fleet guard
(GENERIC-HUB.md). Local checkout does not track `origin/main` (remote is
`github`).

### Agent Relay (`0a2895b`, 14 Sep 2026)

SQLite FastAPI register/task/result starter. Generic report correctly left it
unmarked. Not part of the conversation platform.

## 5. Competition, Agent Branches, contest artifacts

### Cloudflare agent git (GitHub `0a95aa1`)

Portfolio docs, process, recovery, timers, contest prototype:

- Process: `_docs/03-way-of-working.md`, `_docs/04-communication.md`,
  `_docs/team/*`, founder journal through 2026-10-15
- Recovery: `_docs/05-recovery.md`, issue
  [102](https://github.com/alexeygrigorev/cloudflare-agent-git/issues/102)
  still OPEN (`scripts/recover-agent` was absent on 7 Oct inspection in that
  doc). Unattended failover is not accepted.
- Supervision / ping / root: `scripts/supervision/`, `scripts/ping/`,
  `scripts/root/` — host-side runtime per generic report; hub checks can
  replace them after observed dual-run. Issue 104 still OPEN on making
  `scripts/supervision/service.py` executable or stopping docs that name it
  as installed.
- Request-to-outcome / review gates: `scripts/delivery/`,
  `scripts/guards/review_gate.py`, `scripts/guards/claims_check.py` — repo
  boundary, not hub conversations.
- Turn-end wake: `scripts/ping/ask-ledger.py` — host-side; inventory said
  keep, not port.
- Prototype Worker/DO/Artifacts: `prototype/` — contest runtime; hub must
  not touch the contest Worker.
- Submission: `docs-submission/SUBMISSION.md`, `VIDEO.md`, `COST.md`,
  `DEMO-SCRIPT.md`. Founder journal 2026-10-15 records that the contest
  entry was submitted (Loom recording; receipt screenshot privately). That
  is submission receipt, not a judging result.
- Post-demo follow-through: GitHub
  [issue 114](https://github.com/alexeygrigorev/cloudflare-agent-git/issues/114)
  OPEN; `_docs/demo-feedback-2026-10-15.md` exists on GitHub (`32caeac5734b`)
  and is missing from the stale local checkout.

Local `~/git/cloudflare-agent-git-wt-root-stuckdraft` is a docs worktree for
stuck-draft rules. Do not use it for hub work.

### Agent Branches product (`~/git/agent-branches`)

Standalone CLI/SDK/radar/coordinator backup, pinned provenance in
`docs/SOURCE-PROVENANCE.md`. Inventory decision stands: integrate later if
needed, do not absorb into the hub. GitHub main `82e310f` is a docs commit;
local detached `a35c4bd`.

### Contest worktrees (`~/git/agent-branches-contest-*`)

Leftover implementation lanes from the contest (actors, checks, runtime,
demo, runbook, submission, reviews). Example HEADs when listed: seed
`e009ff8`, demo `da272a3`, live-runner `4504468`, submission `a8a7ef2`.
`agent-branches-contest-e2e-*` directories are not git worktrees. These are
historical; they are not conversation-platform sources. Do not merge them
into Agent Hub.

Live/l6 Agent Branches worktrees (`agent-branches-live-*`, `agent-branches-l6-*`)
are product spikes, also out of hub conversation scope.

### aplexer native inbox (M3 dependency)

Installed `a message` verbs: send, reply, deliver, inbox, wait, log, show,
ack, gc, plus `a work join|leave` and `a context`. Same-host durable inbox
already exists. Hub bridge copies hub→native and native→hub. Conversation
CLI should reuse this, never busy-composer injection (`--pane` only at idle
empty prompt when a wake is explicitly in scope; M3 default is inbox-only).

`aplexer-watch` v0 (`837edff`) is a similarity auto-Enter tool. Hub policy:
never type into terminals.

## 6. Continuation, recovery, tracker, review, failover, quota, scheduling

| Theme | Where it lives | State |
|---|---|---|
| Continuation / unattended recovery | contest issue 102, `_docs/05-recovery.md`, hub SPEC M5 principal-wake | Planned / source-only. No accepted unattended cycle. |
| Supervisor continuation in standalone workspaces | coordination issue 61 | Open. |
| Tracker | GitHub issues per product; contest `TASKS.json` / delivery guards; hub `routing_jobs` and `fleet_launches` | Split. No conversation↔task link. |
| Independent review | contest `scripts/guards/review_gate.py`; hub routing used different-model reviews; launcher lifecycle `completed-awaiting-review` | Repo/launcher gate. Conversations do not record review verdicts. |
| Role failover | `coordination/role_failover.py` source; hub root lease epoch only | Semantics partially merged; generic roles not built. Dirty failover worktree preserved. |
| Quorum | `coordination/quorum_authority.py` | Prototype; inventory decision drop. |
| Quota | quse + launcher admission; hub `src/quota.ts` snapshots; routing reuses ranking heuristics | Source on hub; live placement blocked on account labels / host token. |
| Scheduling | hub checks cron; root scheduling flag off in DEPLOY.md; contest systemd timers still running per reports | Dual-run risk until timers move one-by-one. |
| Ownership claims | hub `/api/bus/claims`; aplexer `a work`; contest git hooks | Three layers. Launch admission does not consult hub claims. |
| Agent Branches provenance | `~/git/agent-branches/docs/SOURCE-PROVENANCE.md`; hub not using AB for this survey worktree | Separate product. |
| Deprecations | GitHub READMEs on hub predecessors; contest repo deliberately not deprecated | Local checkouts lag GitHub. |

## 7. Conversation platform gap

What a human/agent conversation needs, versus what exists:

| Need | Exists | Gap |
|---|---|---|
| Authenticated human identity | DTC session / admin token | No conversation membership for humans |
| Authenticated agent identity | Device-flow agent tokens, bus actors | Actors are not conversation members |
| Direct and group threads | 1:1 `to_actor` + optional `thread_id` | No `conversations` / members / ACL |
| Durable ordered history | ULID bus messages, 30-day retention | Need dedicated `conversation_messages.seq`; do not dual-write `messages` |
| Retries | `idempotency_key` | Reuse; do not replace |
| Inbox receipts | ack/accept/complete stages | Per-message, not per-member unread |
| Human UI | fleet.html operator page | No conversation UI; not dakit |
| CLI | `hub send/inbox/reply/ack` | No conversation commands |
| Native bridge | `hub bridge` | Point-to-point; no conversation fan-in; must stay inbox-only |
| Task/review/outcome | routing jobs, fleet launches, launcher review states | No `conversation_id` linkage |
| Safe pings / continuation | checks + planned principal-wake | Wake must stay idle-empty-prompt; no physical acceptance yet |

dakit (`103912d`) already has shell, split list–detail, inbox nav pattern,
device-login, and family recipes (`docs/shell.md`, `docs/list-detail.md`,
`docs/family.md`). Agent Hub is named as an operator app in the family spec
and does not use `.dk-*` classes today. File missing pieces as dakit needs;
do not one-off styles.

## 8. Reports consulted

Primary (starting set, then verified):

- `~/tmp/agent-reports/hub-platform-brief.md`
- `~/tmp/agent-reports/hub-feature-inventory.md`
- `~/tmp/agent-reports/agent-hub-generic.md`
- `~/tmp/agent-reports/agent-hub-status.md`
- `~/tmp/agent-reports/hub-routing.md`
- `~/tmp/agent-reports/agent-messaging-status.md`
- `~/tmp/agent-reports/hub-platform.md` (orchestration log; workers already
  started as candidates)

Related, not re-opened as source of truth: `aplexer-send-ack.md`,
`aplexer-watch.md`, `aplexer-enter-delay.md`, `aplexer-blocked-report.md`,
`remote-aplexer-guide.md`, `stall-coordinator.md`, `mcp-hub.md`. dakit
rollout briefs under `~/tmp/agent-reports/dakit-*.md` inform M2 kit usage.
Contest follow-through lives in GitHub issue 114 and the 15 Oct founder
journal, not in those dakit/ais* reports.

Private routing receipts under `~/tmp/agent-reports/hub-routing-private/`
were not read (may contain operational detail). Credential/config/log files
were not read.

## 9. Honest gaps in this survey

- This survey did not itself probe production HTTP, DNS, or timers. Platform
  reports a **current** independent check: `hub.dtcdev.click` unresolved and
  health unavailable. Historical 15-Oct bus tests remain separate evidence.
  Runtime feature claims stay attributed to 15–16 Oct reports except that
  DNS/health line.
- Worker test suite not executed in this session (docs-only task).
- Platform API worktree is still at `213fcf6` plus untracked
  `docs/CONVERSATIONS.md`. CLI/UI trees were not re-listed after the first
  clean inspection. This survey did not edit those trees.
- Local dashboard/bus/launcher divergence from GitHub was not reconciled
  (out of edit scope).
- Quota/host token/domain rollout remains owned by hub-zai / deploy access,
  not this survey.
- Argon has a prepared worktree `~/git/agent-coordination-wt-platform-plan-review`
  at `98857ca`; it has not reviewed this document yet.

## 10. Leftover planned work (mapped)

See PLAN.md “Unfinished planned work”. Summary: claims-in-launch, generic
role failover, writer-run, head-recovery, accounting producers, and
ask-ledger/request-to-outcome remain open in executable M2b/M6–M11; only
safe inbox ping / idle-empty deliver overlaps conversation M5. Unattended
recovery remains contest issue 102. Quorum and auto-Enter stay dropped.

## 11. Next actions

1. Independent Argon review of this STATUS and of `PLAN.md` (existing
   `platform-plan-review` worktree). Repair findings here.
2. Keep routing as the only machine/model/task dispatcher.
3. M1 conversation API on Agent Hub main, isolated worktree, after any
   shared-dispatch ACK with hub-zai (platform already prepared
   `agent-hub-wt-platform-api`).
4. M2 dakit UI and M3 CLI/bridge in their prepared worktrees, gated on M1
   contract.
5. M4 link conversations to routing jobs and review/outcome records.
6. M5 safe pings plus physical host/conversation acceptance. No dual-run of
   old timers and new checks without observed replacement.
7. Do not push these docs until Argon review and head approval.

## Platform integration checkpoint

The first survey draft is `c90cdf8`; survey repair `e854a8d` aligned the
conversation store and attributed the head's current DNS failure. Argon is
reviewing pinned drafts; no final verdict or docs main push is claimed here.
The head has retained reusable unfinished work as M2b/M6–M11 in PLAN rather
than treating named holds as completion.

The agent CLI candidate `0a06f5e` is committed and registered in actual Agent
Branches task `task-0390`. Its author reports 45 focused tests passing;
independent Argon code review and API integration remain open. API/UI task
forks `task-0389`/`task-0391` are allocated, not accepted. Native participation
is being implemented separately in `task-0392`; a genuine nonce-only native
self-send/reply probe succeeded on the execution host, which is not physical
cross-host or authenticated conversation acceptance. No conversation product
commit is on hub main at this checkpoint.

### Independent review checkpoint

Argon reviewed `c90cdf8` and `e854a8d` as REVISE, then accepted `cf91b0d`
with implementation gates for identity/CSRF, dakit, genuine native
participation, conversation-aware notifications and honest provenance.
The code worktrees still require separate exact-version reviews. This
follow-up corrects stale hold wording and makes the supported self-bound
native client and inbox-only notification defaults explicit.

Argon separately accepted CLI `0a06f5e` against the frozen API draft, with
45 focused tests verified. Its full host run retained one real-HTTP fixture
environment error; a dependency-enabled rerun remains required before
integration. Native bridge candidate `17424c6` is in its actual task fork
and independent Grok review has started. The M6 claims worker started only
after routing explicitly acknowledged scope and admission semantics.
