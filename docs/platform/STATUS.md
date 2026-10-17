# Conversation platform status

As of 2026-10-17. Survey owner: `platform-survey` (Grok) in isolated worktree
`~/git/agent-coordination-wt-platform-survey` from `origin/main` `98857ca`.
Implementation target is Agent Hub (`~/git/agent-hub`, GitHub main `5dcdf71`).
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
| Agent Hub | `~/git/agent-hub` at `5dcdf71` | `5dcdf71` | Control plane: auth, bus, registry, checks, fleet, routing, dashboard |
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

### Reviewed plan publication and implementation repair

- Published this survey and PLAN at coordination main `096bdd9`; published
  the exact sanitized independent Argon report at `6cb7a77`. Argon accepted
  final input `096bdd9` after rejecting the first two drafts. Both public
  main synchronization and an independent private GitHub restore were
  verified; restored `6cb7a77` passed `git fsck`. Completed owned survey and
  documentation worktrees were removed after preserving private evidence
  and the original review history.
- Agent Hub main remains `213fcf6`. CLI candidate `0a06f5e` has scoped Argon
  acceptance; its 45 focused tests and the repaired 30-test existing HTTP
  fixture passed. That fixture does not prove the new conversation round trip.
- Native bridge `17424c6` has scoped independent Grok acceptance. Genuine
  native identity, nonce probes and durable delivery/reply mapping were
  reviewed. Installed native send still lacks an atomic idempotency primitive;
  uncertain effects hold and reconcile rather than resend blindly.
- API `ee6d679` was rejected by independent Codex review. Nine findings
  cover identity namespaces, removal/retry authorization, current credential
  checks across awaited bodies, exact human subjects, last-owner transitions,
  aggregate growth, real registry constraints, re-add cursors and a
  clock-sensitive integration assertion. Independent tests completed 13/14;
  separate probes reproduced the security failures. Antigravity repair is
  active. The real registry's global tag constraint remains an explicit
  integration criterion, not a passing replacement-schema fixture.
- OpenCode's dakit UI is a candidate. Its guessed adapter/browser fixtures
  must match the real API contract before review and rendered acceptance.
  The existing route/body/sequence mismatch was identified before integration.
- Grok is implementing M6 claims admission after routing acknowledged the
  source boundary and atomic offer/reservation semantics. Claims remain the
  existing authority; free-text prompts do not grant edit authority.
- Measured process-limit failures in two owned verification workers were
  corrected to the policy's 256-task cap, retaining 1500 MiB memory caps.
  Runtime failures and later completed test results remain distinct evidence.

Next: repair and independently re-review M1; align and render the UI against
that contract; verify actual Worker/CLI/native/browser flow; then integrate
reviewed product commits and obtain the required post-milestone Argon review.
Task/outcome, notification and M2b/M6–M11 acceptance remains open. Production
adoption, physical cross-host delivery, domain readiness and timer migration
are unverified by this checkpoint.

### Worker recovery checkpoint (2026-10-16T23:18:54.875182+00:00)

- The first OpenCode UI run still used the guessed contract and its browser
  run failed 8 of 10 checks. The head stopped that owned workload, verified
  its scope inactive, and preserved source as `f298644` in task `0391`.
  A fresh OpenCode `glm-5.3-flash` continuation in task `0395` now has the
  exact protocol, strict fixture requirements, and a checkpoint before
  browser rendering. The rejected UI snapshot is not product acceptance.
- The first M6 Grok execution stopped without a completed handoff or tests.
  Its native handle was missing and its owned scope was inactive. The head
  preserved the partial implementation as `0fda8bc` in task `0393`; a fresh
  Codex continuation in task `0396` owns completion and verification.
- Antigravity's M1 repair is active in task `0394`. The real registry's
  same-tag limitation needs a compatible storage/registration migration;
  the required shared source lease has been requested from its current
  owner. That criterion remains open while the other eight repairs proceed.
  No reserved Hub source was changed without agreement.
- All replacement model workers use independent 1500 MiB / 256-task
  containment and fresh quota admission. Original code, task-fork history
  and private evidence were retained. Current Agent Hub main is still
  `213fcf6`; combined runtime acceptance and the remaining roadmap stay open.

### Independent repair reviews (2026-10-17)

- M1 repair `033d710` is preserved in actual Agent Branches task `0394`.
  Its author reports typecheck and 23 focused tests passing. Independent
  Codex rereview also passed those tests and 15 private composed-Worker
  probes. The original identity, retry, credential and owner counterexamples
  are resisted, but the reviewer reproduced additional retention defects:
  polling pruned history can fail to advance, retained-message retries can
  depend on a deleted parent, membership removal can fail at the storage cap,
  and cleanup can exceed its batch bound. The pinned report is pending;
  M1 remains unaccepted.
- The real registry still returns 201 then 409 for the same tag in different
  projects. Task `0399` prepares an executable migration patch and tests in
  private source copies, without editing the reserved Hub source. Initial
  audit found additional pairing, inbox-alias and legacy credential-binding
  consumers that must be covered. A storage-only patch is insufficient.
- OpenCode Flash UI repair `6de5b4e`, preserved in task `0395`, reports
  12 strict-contract browser checks, 6 asset tests, typecheck and official
  dakit checks passing. Twelve local render artifacts cover desktop/mobile,
  light/dark and interaction states. The owned worker has exited and its
  quota reservation was released. Independent Grok review is running.
  These fixtures do not establish a real browser-to-Worker conversation.
- Independent Argon review rejected M6 candidate `fe7a8c1` after 144 Worker
  tests, 42 host/CLI tests and 5 adversarial probes. Findings: invalidated
  unstarted offers can permanently retain capacity; conflicting edits bypass
  enqueue admission; policy changes can be bypassed by old legacy offers;
  and the required routed-edit credential cannot be provisioned through the
  current HTTP paths. Task `0400` owns repair, including real device-pairing
  acceptance and preserving started/uncertain capacity until confirmed exit.
- Hub main is still `213fcf6`; no product candidate was merged or deployed.
  The accepted plan, scoped CLI/native reviews, required combined integration,
  post-milestone Argon review, and M2b/M4–M11 roadmap remain in force.

### Pinned candidates and second review cycle (2026-10-17)

- M1 review report `95bb542` rejects `033d710`. Six original findings are
  resolved in the tested paths; retention/accounting and re-add semantics
  remain partial, and the real registry dependency stays open. New findings
  F10–F16 include a high-severity default tombstone cap that prevents an owner
  from removing a current reader. Independent verification passed 23 candidate
  tests and 20 composed Worker probes, including eight assertions that confirm
  counterexamples. Argon task `0401` owns repair; passing counterexample probes
  are not requirement acceptance.
- F7 registry proposal `7d8cd28` is preserved in actual task `0399`. The
  patch is applied only in private copies. Its exact-artifact typecheck,
  34 Worker/M1 tests and 193 inherited regressions passed. The proposal covers
  atomic project/tag uniqueness, immutable credential project binding,
  pairing/refresh, bus aliases and historical message isolation. All 110
  actual core/config hashes stayed unchanged. Independent Argon review is
  running; source application still requires the reserved owners' handoff.
- M6 repair `71349b4`, preserved in actual task `0400`, reports 163 Worker
  tests, five adapted Argon probes, 42 host/CLI tests and typecheck passing.
  It repairs invalid unstarted-offer retirement, enqueue conflicts, current
  policy checks and real HTTP-paired agent submission for routed edits.
  Independent Argon rereview is running. Started or uncertain effects still
  retain capacity until confirmed exit; intent declarations are not an OS
  filesystem sandbox.
- Independent Grok UI report `f66536d` rejects `6de5b4e`. Browser probes
  reproduced cross-human failed-draft leakage, stacked mobile panes, an
  oversized chevron caused by the wrong dakit class, changing create retry
  keys and an enabled composer after denial. Static/official dakit checks,
  typecheck and six asset tests pass. Codex task `0403` owns the five repairs,
  targeted regressions and clean rendered evidence. The missing shared
  message-thread/composer vocabulary was sent privately to the dakit owner.
- M8a host safeguard/proposal `1f6d191` is preserved in task `0402` and is
  under independent Grok review. The actual maintained launcher exposes
  provider/model planning and plain-text submission, with no qualifying
  account/native-profile/effort/request/native-identity receipt. The host
  candidate holds unsupported task execution before claim/submission; it does
  not implement the missing launcher contract. Its reported 202 host tests,
  34 restore tests and 42 server regressions do not prove actual credential
  attribution. Launcher owner agreement and companion implementation remain
  required; full M8a is open.

Hub main remains `213fcf6`; no candidate above is product acceptance or a
production deployment. Required combined Worker/browser/CLI/native evidence,
post-land Argon direction review and the rest of the roadmap remain open.

### First accepted product milestone landed: M6 (2026-10-17)

- Agent Hub main is now `5dcdf7164b28bd0e3a1d717ac9090c054eca3f24`.
  It contains exact M6 source `71349b42` and the sanitized independent Argon
  acceptance report in `docs/reviews/CLAIM-ADMISSION.md`. All four prior
  findings were resolved. The head rebased onto fresh main, verified the code
  matched the accepted source, and passed typecheck, 163 Worker tests and
  42 host/CLI tests before the normal main push. No Actions run was created
  for the `[skip ci]` push.
- Shared main and the real Agent Branches canonical were fast-forwarded to
  the same SHA. An expired scoped development token was renewed privately;
  the peer's original token file was preserved. The separate private GitHub
  recovery clone restored the same SHA, passed `git fsck`, matched nine
  relevant source/report blobs, and ran the restored CLI help command.
- This is source acceptance of typed claims admission, not filesystem
  sandboxing, provider execution qualification or deployment. The future
  F7 registry integration must use its immutable credential actor binding
  in `claim_admission.ts`; that adapter remains an explicit merge-time gate.
- API repair checkpoint `a7452d8`, preserved in task `0401`, reports 29
  conversation tests and typecheck passing. Additional integration/probe/docs
  work and independent rereview remain. UI repair `7179868`, preserved in
  task `0403`, reports 29 browser checks and 12 adapted reviewer probes;
  independent Grok rereview is running. Combined conversation acceptance
  remains open.
- A fresh launcher audit found GitHub main `5145d0d` has substantial
  provider-admission/root-profile/task-unit code absent from the shared
  installed checkout `53c7b2e`. Its task-unit quota cohort gate deliberately
  holds. Task `0404` prepares executable launcher/Hub companion patches in
  private copies of current source, reusing these guards. Actual reserved
  source remains unchanged and full M8a remains open.

Next: post-land Argon direction review of this foundation and the remaining
critical path; finish M1/F7 security and ownership gates; then verify the real
Worker/browser/CLI/native conversation flow. The full M2b/M4–M11 roadmap and
later review of the working conversation path remain required. No deployment,
cloud resources, domain, production/provider credentials, services or timers were
changed. Only an expired scoped Agent Branches development token was renewed
privately while preserving the peer’s original token file.

## Registry rejection and final API review — 17 October

Independent Argon review `eae7fdc0519f60681ff5e885061682471bb53193`
rejected F7 proposal `7d8cd282d292a45b0ec297ec1a8e86ff327fc332`.
Its 227 inherited/focused checks passed, while nine independent probes
reproduced five defects: projectless registration can be locked out by a later
qualified registration; reserved names can acquire human/system/host identity;
invalid credentials can become valid after registration changes and survive
deletion; immutable registry bindings conflict with the landed M6 raw credential
comparison; and root reply aliases plus conversation denial status are inconsistent.
The first two are HIGH blockers. No registry patch has been applied to source.

Codex repair task `0405` (`platform-registry-r2`, genuine session `302edfb8`)
is running in private source copies. It owns only the two proposal artifacts.
Its inputs are accepted Hub main `5dcdf7164b28bd0e3a1d717ac9090c054eca3f24`
and the six final API files at `da38cb2a00c092423d0b67419b0ea45d6a09dfa9`.
The repair must address all five findings, preserve final retention fixes and
M6 admission, and pass independent review before acknowledged source handoff.

The Argon API owner released final `da38cb2` with 31 public tests, 20 adapted
observational probes and typecheck reported passing. Those six files were
imported byte-identically onto accepted M6 main as
`f872fd1047b28f9e2d57820a7c0c7dc626870346`, preserved in actual Agent Branches
task `0406` with fork push and WIP registration. Independent Codex review
`983c8d74` is running against that exact combined base. Required F7 remains open;
a scoped API acceptance alone cannot complete M1.

Grok independently accepted UI `7179868ae9f1723d9070a37f107a3b4f635c5cb6`
in report `35fa7cd8599cd782a9a8d5ccf5d3f9196a77028b`: all five prior blockers
resolved. Review covered static/dakit checks, typecheck, six asset tests and
browser probes (24 passed with one harness timeout after a successful creation;
seven follow-up probes passed). It inspected 12 rendered images. This is scoped
fixture UI acceptance; real combined Worker/browser/CLI/native transport remains
required before the conversation platform can be called working. UI is held for
safe backend integration.

Post-land Argon direction review `787001e2` is running against Hub `5dcdf71`,
coordination `20dabd3` and the full accepted roadmap. It is an early M6 foundation
review; later working-conversation review remains required. M2b and M4–M11,
physical execution qualification, real adoption and operational handoffs remain
open. Private GitHub restore and fsck independently verified coordination
`20dabd3` and Hub `5dcdf71`.

## Retention review and real transport work — 17 October

Independent Codex report `626dac6d540a5342bb87db57a74e5d41fbaa3fa6` gives
**REVISE** on exact API input `f872fd1047b28f9e2d57820a7c0c7dc626870346`.
It independently ran typecheck, 31 public tests, 47 observational probes and
120 M6/lifecycle compatibility tests. Most F1–F16 repairs hold. Two required
repairs remain beyond F7: F11 unread counts include interior-pruned messages and
gap metadata is incomplete; F14 mixed bus messages, claims and conversation
cleanup can delete three rows at limit 1 or 101 at limit 100. A LOW finding also
requires rejecting malformed or unsupported accounting-migration versions.
Observational probes confirm failures; their passing assertions are not API
acceptance. Real local Worker dispatch, RPC, both cron paths, alarm, concurrent
sends/retries and accepted M6 compatibility passed under private composition.

Grok repair task `0409` (`a4b49718`, `platform-api-r3`) is running against the
frozen input. It owns conversation retention/accounting and the narrowly
required `src/bus.ts` shared-budget repair, with regression tests. It must preserve
all earlier identity/replay/revocation fixes. F7 task `0405` remains separate and
uses its pinned inputs; the head will combine independently reviewed repairs.

Actual Agent Branches task `0408` preserves combined input
`cee47dff8b423d82eb15e1f9b39cc39ff9ede59f`: accepted M6 main plus 43 unchanged
files from final API, reviewed UI and reviewed CLI/native bridge. Codex worker
`874796d5` owns the minimal Worker composition hook and dedicated transport
harness/docs. It has selected the conversation subclass under the existing
public Hub identity. Its target is real local workerd/SQLite, browser, Python CLI
and its own genuine native inbox exchange; fixture API responses cannot satisfy
that criterion. Pending F7/API defects cannot be credited as fixed by this work.

The original M8a Grok review session `2ddf3991` disappeared from fresh live/all
session listings without producing a report. Its worktree and private probes
were preserved. Recovered reviewer `ff4d61d2` is running against
`b05384c19afb5ac8d3b1594669e63c6b79bb6bb6`, the same frozen host safeguard
files on accepted M6 main, preserved in actual task `0407` fork/WIP. It must
inspect fresh launcher source `5145d0d`, distinguish it from the old installed
source, and give a scoped verdict. Full physical execution qualification remains
open. Genuine first-action evidence was checked for tasks `0407`–`0409`.

Hub main remains `5dcdf71`; no rejected API/registry source has been pushed or
deployed. The full accepted roadmap and required working-conversation Argon
review remain open.

## Early Argon direction findings acted on — 17 October

Argon direction review accepts the M6 foundation and the complete roadmap as an
early checkpoint. It leaves `GATE-CONV-REVIEW` explicitly open: a later review
must inspect the integrated, verified conversation path. P1 registry identity
repair and P2 API retention repair remain required; their independent review
verdicts cannot be replaced by this direction acceptance. P4 keeps physical
execution qualification open beyond host safeguards or a single attested route.
P5's credential summary has been corrected to distinguish a renewed scoped
development token from production/provider credentials.

P3 adds a concrete bridge requirement: pruned prefix or interior history can stop
the native bridge's contiguous-sequence check permanently. PLAN now requires a
fail-closed default plus explicit authorized catch-up or a durable gap notice;
no skipped history can be silently reported delivered. Task `0408` reproduced an
interior gap through the real API/CLI and keeps it unresolved while task `0409`
repairs the server metadata.

The transport worker reports a real local browser/Worker/SQLite/Python CLI and
own genuine native-inbox round trip, reconnect/reload without duplicates,
restart reconciliation, loop suppression and immediate removal denial. This is
author evidence pending frozen-source independent review, not physical
second-host acceptance. The rendered browser evidence was inspected by the head.

Launcher companion artifact `18dd854322ace65f1773c5d4115866b137e6d907` is
preserved in actual task `0404` fork/WIP. Independent Argon reviewer `ff24f690`
is running on the three byte-identical artifacts imported onto main as
`82ab318` in an isolated worktree. The review must inspect fresh launcher
`5145d0d`, private test-state isolation, and compatibility with landed M6. The
251 author fixture checks do not establish live account identity, configured
profile coverage, cross-host capacity or execution qualification. Source owners
have not authorized application; no provider job or production rollout occurred.

The final direction report is published alongside this log as
[POST-MILESTONE-ARGON.md](POST-MILESTONE-ARGON.md), byte-identical to independent
Argon commit `0d92f30412dadfbb9346ada31e969da55512f02a`. Its accepted inputs
remain coordination `20dabd3` and Hub `5dcdf71`; later task updates are additional
evidence, not a changed review scope.

Registry repair `ddaf80d82022736da82ff11d521c6a9f92ff593e` is frozen and
preserved in task `0405` fork/WIP. Its author reports 57 focused and 254 inherited
tests, including 61 M6 tests, plus typecheck and exact 20-file patch reconstruction.
Independent Argon reviewer `fe000dc1` is running against that exact proposal;
actual core source remains untouched and the required source handoff is open.

Transport candidate `d9b4cde07e3718d77b2db9308cd323a5c8e003ed` is frozen and
preserved in task `0408` fork/WIP. The final committed-source native run repeated
the seven-checkpoint, four-message, 26-browser-request exchange. Its author also
reports 113 focused, 611 host and two composition tests, typecheck, assets and
a local dry bundle passing. It leaves the reproduced retention gap unresolved;
independent review and a rerun after accepted API/registry/bridge repairs remain
required before main integration.

## Explicit gap recovery and remaining cleanup fairness — 17 October

API repair `9f6d5431e36d8a67104c89dbe5b63cf296eac489` is preserved in actual
task `0409` fork/WIP. Independent Codex report
`dde82cdc4af95a7f5fd5006d23403295ba463d67` gives **REVISE**: retained unread
counts, gap metadata, malformed migration versions and total deletion budgets
pass, while fixed-priority selection still starves categories under sustained
backlogs. The final 313 distinct checks comprise 307 passes and six failures
reproducing one F14 fairness defect at bus, composition and conversation-category
levels. Configured 50,000-message/1,000-header caps, real HTTP/RPC/alarm budgets
and transactional rollback passed. Original Grok task `0409` is resumed as
`platform-api-fairness` (`b2e4d314`) to implement bounded progress that survives
service/DO restarts. F7 remains required and uncredited.

Explicit bridge recovery candidate `0896ebe157cc732342b17fb40a6cf6e096ef93a2`
is preserved in actual task `0410` fork/WIP. It requires operator acknowledgement
and an authenticated proof that the proposed skip range contains no retained
messages; it atomically records the gap and advances only the local cursor.
Uncertain effects remain held. Author checks on the final source passed: 635
host tests, 55 focused tests and three real Worker/SQLite/Python CLI checks.
Eight genuine own-native checks and five late-join checks remain accurately
pinned to preceding `13b8153`; the final change only makes parser imports lazy
for Windows, with core bridge AST equality verified. The native fixture's
continuation used new conversations in a fresh local store, retaining the prior
journal/effect evidence; it is not original-store restart proof. Independent
Grok reviewer `038f97ef` is now reviewing the exact final source and evidence.

Independent Argon transport report `8ecac25` retains scoped acceptance of
`d9b4cde` composition and local no-gap transport, with follow-up observations
about native cursor versus server read position. Independent adjudication is
requested in the bridge review: the reviewed bridge contract explicitly replays
retained history from sequence zero, and M1 grants restored members retained
history access. Advancing to a remote read watermark must not silently bypass
unresolved native delivery intents. The actual retention gap remains a required
repair; no automatic cursor policy change or full bridge acceptance is inferred.

The two interrupted Grok safeguard reviews were diagnosed from persisted events:
headless permission prompts were cancelled before the test command ran. The
original review context is now genuinely resumed as `9285dcaf` with the installed
CLI's supported headless tool approval flag, private exit receipts and original
evidence preserved. Successful subsequent tool execution was observed. No
global configuration changed, and the optional adjacent Argon host-report request
was withdrawn to avoid duplicate ownership. Safeguard and full execution
qualification verdicts remain pending.

Hub main remains `5dcdf71`. No rejected API or registry source has landed.
Independent registry/launcher reviews, acknowledged source handoffs, accepted
combined-stack native verification, `GATE-CONV-REVIEW`, and the complete remaining
M2b/M4–M11 roadmap stay open.

Registry rereview is now **ACCEPT**: report
`426fdf7c9fe2929d81725d66e1d838c9d247ee2d` approves exact proposal `ddaf80d`,
with 319 independently executed tests, typecheck and exact reconstruction.
F7-R1–R5 and routing-client separation pass. A concrete accepted-patch request
was sent to the reserved Hub owner for the required source/test hunks; no source
was applied and no handoff is inferred. Separate API and integration gates remain.

Recovered Grok report `ba1681c3ce9d05ba794366c17c4d99314788534a` gives a split
verdict on host safeguard `b05384c`: **ACCEPT** for fail-closed pre-claim HOLD;
**REVISE** for the old launcher audit/owner contract documentation. Maintained
`5145d0d` guards and required modules must be described correctly before that
contract can be accepted. Full M8a remains open.

Public pairing is also an explicit source dependency: current agent device
approval cannot issue the machine-bound credential required by the native
bridge. Existing local transport evidence discloses its SQL-seeded credential;
it does not establish a usable production enrollment path. New actual task
`0411` (`platform-agent-pairing`, `a25c20d1`) prepares a minimal tested proposal
in private copies of the composed source plus accepted F7. Its new agent token
must come through public authenticated device APIs, with trusted existing
machine assignment and ordinary-agent permissions. It owns only two proposal
artifacts; leased core source and production enrollment remain untouched.


### Final repair candidates and independent reviews — 17 October 2026

F7's original rejection `eae7fdc` is preserved. Revised proposal `ddaf80d`
has independent scoped acceptance `426fdf7` (319 tests and typecheck), resolving
F7-R1–R5 and routing-client separation. Actual source remains unapplied; the
accepted patch has been sent to the reserved Hub owner for a scoped handoff.
A late acknowledgement to the original reviewer could not be delivered because
its native session was no longer recorded. No agreement is inferred.

API fairness candidate `7c004676dc9c0c6496656cb6a4bc62dbadff09ae` is preserved
in task `0409` fork/WIP. It adds persistent selection across bus, composition
and conversation cleanup categories; author verification reports 209 tests and
typecheck. Independent Codex `04cbc385` is reviewing the exact final tree,
including all six prior sustained-backlog failures and reconstruction between
cleanup calls. Candidate test results do not replace that verdict.

Bridge gap candidate `0896ebe` now has scoped independent Grok acceptance
`f19353e8c9a900f2697f6edeb7da08691cf901e8`. The reviewer independently ran
635 host, 55 focused, 30 HTTP/CLI, ten adversarial and six additional HTTP/CLI
checks. Own-native evidence remains pinned to predecessor `13b8153`; AST
comparison confirms that the final lazy-import change preserves bridge logic.
The reviewer also adjudicated the earlier transport cursor observation: the
explicit retained-history replay contract does not require automatically
advancing to the server read watermark. Such advancement could bypass uncertain
local deliveries. Actual retention gaps still require the explicit authenticated
proof and acknowledgement flow; no silent skip is accepted.

Public pairing proposal `1149f65394611d05c1f55fcec4e803f105930c8d` is preserved
in task `0411` fork/WIP. Author verification reports 333 tests, typecheck and
four browser/public-API/bridge qualification checks. The new agent token was
issued through public device APIs; human and machine fixtures remain local.
The proposal preserves ordinary-agent privileges and fixes two job-detail
checks that otherwise trusted a machine identifier without checking principal
kind. Independent Argon `252a3a83` is reviewing the inert patch against the
exact composed transport plus accepted F7 base. Actual source and production
enrollment are untouched.

Launcher companion `18dd854` received **REVISE** in independent report
`bed83934a52b65c8e91bd12be9f51e61b341469d`: M6 composition, uncertain-start
recovery and admission lifetime need repairs. New task `0412`, Codex `18f3d512`,
is repairing only the three proposal artifacts on private Hub `b05384c` and
maintained launcher `5145d0d`. Initial checkpoint `94c925b` passes all 61 M6
cases plus 158 launcher and 50 Worker cases, but hardening remains in progress
and it is explicitly not ready for acceptance. Grok CLI exit is not proof of
backend cleanup. The separate host safeguard review `ba1681c` accepts pre-claim
HOLD behavior and requests corrected documentation; full M8a remains open.

Hub main remains `5dcdf71`. Source ownership, exact combined-stack verification,
`GATE-CONV-REVIEW`, physical cross-host adoption, and the full M2b/M4–M11 roadmap
remain required. No deployment or global installation occurred.
