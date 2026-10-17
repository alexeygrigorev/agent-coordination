
## 2026-10-17 urgent shipping override, 16:19 Berlin

Alexey waived review/custody/activation/budget gates for shipping. Finished work goes immediately to main; no frozen WIP or long-lived task branches. M12, M13, M15 module slice, hub-zai alert/operations follow-up and M14a landed. Nineteen merged task worktrees/branches retired with private evidence preserved.

Real Muse session d18e1de8-43b3-4a7e-a992-ed1b22d0f5a0 passed the repeatable public CLI/HTTPS start → automatic binding → correlated receipt → capture (3686 characters) → confirmed stop loop before 16:25 Berlin. Main 7df2dd9; deployed Worker version 9dd0127f-f405-4fbc-8c2e-153347dc56cf includes server changes through cdf5e5a; subsequent commits add host/client tooling. Exact commands and truthful remaining gaps are at the top of ~/tmp/agent-reports/hub-platform.md.

Alexey urgent point6 at16:23 now sets Hetzner-only runtime/testing. Win35 is intentionally offline for two weeks and is not a failure or blocker. The Hetzner milestone passed; physical Grok Bot box client execution was not performed. Fresh Muse worker platform-intake-live owns the next live intake assignment/handoff integration, pushing small tested commits immediately to main. Unattended host-service recovery, other-machine adoption and remaining M12 crash/tier findings are next. Receipt proof is not task-completion proof. Canonical latest urgent state: .local/platform/URGENT-CURRENT.json.
# Conversation platform status

As of 2026-10-17. Survey owner: `platform-survey` (Grok) in isolated worktree
`~/git/agent-coordination-wt-platform-survey` from `origin/main` `98857ca`.
Implementation target is Agent Hub (`~/git/agent-hub`, GitHub main `2eb0c3b`).
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

## Current checkpoint — 17 October 2026

**Latest accepted source — 13:46 UTC.** Hub main, canonical Agent Branches and
private recovery now equal `2eb0c3b09628871c281307775dbb729b2193cc3e`. Independent
Argon report `7871854` accepts exact lifecycle repair `1b7e109` for module seams
only. The head verified the report hash/sole parent, all eight full Git references,
12 reviewer guard receipts (11 clean, one preserved failed probe, zero aborts),
and all 237 pre/post source pairs. Integration preserves all 231 prior accepted
files and all nine reviewed lifecycle files: 240 hashes verified in private
restore/fsck/CLI checks. Publication only fixes report links/task-ID spelling;
original report and failed/aborted author runs remain preserved. M15 actual
registration, API/CLI, durable decisions and host/Git cleanup remain open.

M14a now has source owner Muse `platform-status` (`b5add0a1`), actual0443,
verified native identity and explicit ACK, on fresh main `2eb0c3b`. It implements
the authorized one-call status API/public CLI projection with real canonical
metadata and explicit gaps. M14b native/report collection, M14c verified Git/
active deployment/CI, M14d durable diffs and physical acceptance remain open.
Unused ended-source caches were retired after exact declarations and privileged
process/inode/socket proofs, making room for the worker within the 512 MiB
aggregate scratch budget. All source, reports, histories and receipts remain.

Primary M12 Argon actual0440 continues compatibility and novel/native tests;
M13 Argon actual0442 reviews seed `2041df5` / author `811c086`, including actual
native quota coverage and the Grok hold. No deployment, credential/config,
enrollment, service or timer change was made by this session. The physical shared
checkout remains clean at old `5dcdf71`; its default host config is unusable.
An investigation mistakenly applied that old checkout’s auth-test behavior to
current main. A quarantined current-source probe disproved the allegation and
the reviewer received an explicit retraction; no unnecessary source fix was made.
The historical writer of the fixture-like config remains unproven.


**Latest publication — 13:28 UTC.** Hub main, canonical Agent Branches and
private recovery are `77ab932c421c39397b20636a77fb3d3d72c280e8`. This adds
only the independently reviewed ops guide, two regression cases/config and review
report; production application code is unchanged. The two focused cases passed
under a real 1500M/256-task scope and scratch guard without aborts or survivors.
All 231 accepted source hashes, private restore/fsck and CLI checks passed;
the protected clean physical checkout stays at `5dcdf71`. No deploy occurred.

M13 Muse source `811c086` now includes the approved no-new-Grok policy and
focused real HTTP/SQLite boundary test. Actual0439 fork/WIP is verified. Its
worker ended normally after consuming the pending policy approval; no duplicate
was started. Independent Argon `5db97f80` (actual0442) has verified native
identity and explicit ACK. Its immutable review seed `2041df5` combines current
main with all 19 author files byte-identical: 238 source pairs, 219 unchanged
accepted files, 12 changed and seven new. Native-unit coverage, least privilege,
claim-time freshness and live rollout still need independent acceptance.

M12 Argon actual0440 continues compatibility and adversarial/native review of
`1f4e300`; its earlier Python batch passed 187 cases. M15 Argon actual0441 is
finishing the module-only `1b7e109` report after 11 clean runs and one preserved
failed reviewer probe, with no guard abort. A draft verdict is not acceptance;
wait for the committed exact-source report. M15 integration/effects remain open.

Corrected independent CF reads succeeded with the existing token: deployment
and version metadata are available, with a listed rollback candidate. Exact
active chronology/GitSHA remain unproven. The user fleet unit resolves a default
host config with a placeholder base URL and missing access/machine binding;
its historical writer and full failure cause remain unknown. No config or
credentials were changed. Source acceptance and exact custody/budget/qualification
still gate runtime activation. Earlier checkpoints retain history.


**Authoritative update — 13:12 UTC.** Full goal remains M1–M15 plus M2b.
Hub main/canonical/private remain `91b8b6c`; this turn publishes coordination
updates only. The protected physical checkout remains clean at `5dcdf71`.
No deployment, enrollment, credential refresh, service or timer change occurred.

- **M12 first:** actual0430 source `1f4e300` is frozen, with 253 verified source
  hashes. Independent Argon `a935a199` (actual0440) has verified 187 Python
  cases and is continuing selected Worker/SQLite, novel authority and native
  protocol checks. Full engine/tier/host/cwd/brief and all five R2 finding groups
  remain acceptance gates. The real Grok Bot box -> Hub -> Hetzner AI loop is
  open; intake assignment/backfill/fresh-agent handoff follow it.
- **M13:** Muse `62c9c839` (actual0439) continues the full native collection,
  authenticated API/CLI/dakit UI and routing-admission source slice. Its failed
  and scratch-aborted tests remain failed, including `quota-hhttp`. The head
  reclaimed only explicitly requested ended temporary paths after privileged
  inode/maps/fd/cwd/socket checks, retaining all receipts and source. A fresh
  aggregate proof permits future guarded runs at 28 MiB hard / 24 MiB early;
  earlier 16/12 and 24/20 runs are not retroactively reclassified. Live native
  credits/spend coverage remains required; a fixture roundtrip is insufficient.
- **M15:** independent report `444f5ba` accepts plan `2119268` under M15-IG1..7
  and rejects original source `4e0f864` on six findings. Muse `964f24fe` froze
  repair `1b7e109` in actual0436. The head verified 237 source hashes: all 228
  accepted files unchanged plus nine new lifecycle files. Argon `73f1ad33`
  (actual0441) has verified native identity and explicit ACK and is reviewing
  the repair. Two author runs have early-scratch aborts despite exit zero;
  their claimed success is unaccepted. API/CLI, durable custody/decisions,
  guarded Git/process effects and physical acceptance remain M15c/d work.
- **Hub-zai follow-up:** actual0437 Muse recovery ended normally with candidate
  `10796ab`, three new docs/test files and two earlier focused liveness passes.
  First identities and task handoffs are verified; actual fork/WIP is updated.
  Corrected evidence places failed USER `agent-hub-fleet-host.service` on local
  RMTHZ. Its root cause is unknown. Earlier wrong-unit/scope conclusions and
  discovery parser errors are preserved with an erratum. Current active Worker
  revision/rollback, credential audience and activation readiness still need
  bounded verified reads. Runtime changes remain gated behind M12 acceptance.
- **Routing override:** Alexey prohibits new `grok` engine workers because Build
  shares Bot limits; running Grok sessions may finish. New workers prefer Muse,
  Z.ai `glm-5.3-flash` or Antigravity, with Codex coordinating/reviewing. The M13
  owner ACKed and proposed the existing disabled-provider policy. The head
  approved that exact config edit with reserve/claim enforcement and boundary
  tests in its isolated source; integration/runtime enforcement is pending.

M13/M14’s seven plan gates and M15’s separate seven gates are explicit in PLAN.
M9 UI `aa048b7` and full DTO `f20b35a` remain independently unaccepted and are
not blanket prerequisites for M12. Prior checkpoints below are historical;
this update and private CURRENT.json govern current assignments and results.

### Earlier checkpoints (retained history)

**Quota implementation staffed (17 October, 12:20 UTC).** Actual0439 Muse Spark
worker `platform-quota` (`62c9c839`) is running in its own fresh-main quota
worktree with verified native identity, task ACK and design artifact. Its scope
covers the full M13 collector/API/CLI/dakit UI/routing-admission source slice,
with all three binding quota gates. M12 remains first priority. Admission became
possible after retiring only three exact regenerable caches from ended workers:
privileged read-only maps/fd inode checks found no references or unreadable
processes, exclusive file scopes were held, and source/reports/histories/worktrees
were preserved. This is source work in progress, not deployed quota coverage.


**Plan-review publication (17 October, 12:06 UTC).** Hub GitHub, canonical Agent
Branches and private recovery now equal `91b8b6c189c4f54b9d9e2c44d7dfcb09e5208396`.
The only delta from `6bc91a1` adds the corrected independent M13/M14 plan report.
All 228 accepted source hashes remain unchanged; private restore/fsck/CLI checks
passed and the shared clean checkout at `5dcdf716` was preserved. Seven binding
M13/M14 gates are explicit in PLAN. This is plan acceptance only. M15's separate
Argon review is active in actual0438. UI candidate `aa048b7` now has a verified
252-pair manifest and actual0435 fork/WIP; independent guarded validation remains
open. Primary M12 repair is making guarded test progress, with no source freeze
or real cross-host acceptance yet. Earlier paragraphs below retain history.


**Latest execution update (17 October, 11:55 UTC).** Full scope is M1–M15 plus
M2b. Addendum 5 is M15: session provenance/ownership, needs-action grouping,
durable limit decisions and guarded dry-run/apply cleanup feeding status/handoff.
Actual0436 is assigned to OpenCode Muse Spark worker `platform-lifecycle`
(`ee366bf6`) in its own fresh-main worktree; native identity, explicit task ACK
and design artifact are verified. It owns new modules/tests/docs. Shared API/CLI
integration, independent review and actual host acceptance remain open.

Primary actual0430 is resumed by Muse `platform-session-r3-recovery2`
(`a9da74f2`) in the preserved isolated source tree, committed `a46213fc` plus
unfinished changes. Its predecessor was stopped by the head after repeatedly
running guard-aborted whole suites and claiming 26/26 green. That result is
withdrawn; code, history, patch and receipts are preserved, and the new worker
ACKed the correction. The head-owned replacement guard passed success, early
abort and unfiltered-Vitest rejection self-tests after correcting shared-cgroup
attribution. Product tests must select at most two Vitest cases per invocation.
The first recovery model turn `ea30db81` then ended normally awaiting a design
reply; its model record confirms the cause. Resumed turn `a9da74f2` has explicit
permission to continue without a generic ACK wait. No session source or real AI
cross-host acceptance is implied.

Both full R5 Codex reviews ended without final reports; cause unknown. Retained
probes identify an atomic authority gap and two UI pagination races. UI repair
`aa048b7` awaits guarded independent validation; its author supplied no real
in-run guard. Argon session report `db3dcbc` is final SCOPED REVISE, with only
mechanical metadata corrected in `9f9a5fc`. Plan correction `7408769` is complete
but awaits head audit; source/runtime acceptance remains separate.

Alexey handed over hub-zai's unfinished work while stopping that quota-blocked
session. Processed once despite repeated notification: actual task0437 is
assigned sequentially to Muse `a9da74f2` after primary M12 source freeze.
The worker explicitly ACKed task0437 and wrote a verified read-only inventory.
`f5efc43` alert default already landed; the stale report's uncommitted claim is
obsolete. Remaining work is targeted validation/test-runner diagnosis, domain
capability, host enrollment/grok-bot pairing and replacement-check migration.
The old full-suite pipeline script must not run again. Shared checkout and
existing timers remain preserved; activation requires exact custody, current
capability and independent evidence. The cleanup report explicitly protected
Hub worktrees and does not explain the interrupted Hub reviews.

Earlier checkpoint paragraphs below are historical and may name ended workers.
The latest execution update and private CURRENT.json govern current ownership.


**Accepted Hub main, canonical Agent Branches and private recovery equal
`6bc91a1278250b374ea1d0b11acd353fae51a8cb`.** M12a ledger/API/public CLI and
`hub handoff` received independent Argon scoped acceptance: 36 Worker/SQLite HTTP,
15 stdlib/public CLI and 14 novel cases passed (65 unique), plus typecheck.
All 216 reviewed source hashes match; private restore, fsck and CLI help passed.
Actual assignment, backfill, assistant adoption, MCP and cross-host session
control remain open. Earlier checkpoint entries below retain historical evidence.

**Current priority and steering.** Deliver the working M12e start/send/confirmed
delivery/capture/stop loop first, then intake assignment/backfill and actual
handoff adoption. Prefer OpenCode Go / Muse Spark 1.3 implementation workers;
Z.ai Flash is also available per Alexey’s reset notice. Keep Codex for coordination
and review, with fresh quota/launcher/resource admission before every launch.
Addendum 3 is now M13 in PLAN: all enrolled machines collect provider usage
locally, publish no raw tokens, expose hub quota CLI/API/dakit UI, and existing
routing avoids exhausted engines. This is planned work, not shipped coverage.
Addendum 4 is now M14 in PLAN: authenticated `hub status [--since 2h] [--json]`
and API return per-task sessions on all hosts, engine and working/waiting/limit/
context-low/unsubmitted-input observations, report headlines, main versus deployed
commits, CI, pending Alexey actions and a short diff. It reuses existing records
and remains planned; no one-call implementation or runtime acceptance is claimed.

M13/M14 plan report `b033eea` was produced in actual task0432 on coordinator
pin `6750e34`. Its 28 source-receipt hashes/bytes/blobs match, but head audit found
three invalid Git references, incorrect metadata and priority/quota interpretations.
The original report remains immutable; new Argon correction worker
`platform-quota-status-plan-review-r2` (`5de3093f`) has verified identity and task
ACK. Plan acceptance remains pending correction. No implementation/runtime
acceptance follows from the original conditional verdict.
The earlier task-create failure was reconciled: the generated 65-character fork
name exceeded the sidecar's 63-character limit. A shorter prefix created task0432.

The original M12e API/host workers completed their isolated component work;
the connected source and independent review are recorded below. The current
Muse repair is complete; a new Argon reviewer owns its exact source review.
A separate Muse worker repairs the host-auth dependency and metrics findings.

Retention/roles composition with M12a at
`aec97138afd5bccd9cd053794d85ee6dcfef548f` received Argon scoped acceptance in
`4c7cf04bd689b81c867bd2622f2c116bede9d94a`: 138 original/repair cases, five
new adversarial probes, 36 intake and seven host cases passed (186 distinct),
with typecheck and local bundle dry-run. Head corrected factual report metadata
in `6bc91a1`, preserving the original report and all failures. No source changed
in that correction. Normal GitHub and canonical Agent Branches fast-forwards,
private restore/fsck/nine baseline blobs/all 228 reviewed source hashes and CLI
helps passed. The digest is
`ee2e0f158e46067ed77cbf8ac9addcbed55d4a4988c6a2c8fece1786dbcf70a0`.
No deployment or physical acceptance is claimed.

Session-control source is registered in actual tasks0428/0429: final API
`cd0e9d099efea884ee9e52fcbe7c0901e03d4128` reports 26 Worker and 20 Python CLI
cases, with actual hub/public CLI wiring, claim attempt fencing and native-envelope
proof validation. Host `69ae9f1e9a8f4cf6e33fc205080f7ee1350ca15e` reports 28 focused
cases, including journal locking and retirement of raw Enter/working-as-ACK.
Their original failures and broader test evidence remain preserved. Their
initial session-UUID/message-envelope mismatch was repaired in the connected
source below; the components remain outside main pending full repair review.
A premature API freeze report was caught by the clean-tracked WIP guard; its
immutable intermediate commit was registered explicitly as early WIP, then the
actual clean final commit was registered after the author stopped.

Integration task0430 has a fresh-main worktree at seed
`d84ca875898a3aaf89ef8dabdefcf93c7f4640b6`, a normal no-conflict union of accepted
main and both frozen components. Muse Spark 1.3 worker `platform-session-compose`
(`ae075e9a`) completed the connected receiver/CLI source at
`f9417de39d7818f18cf6f4a3a8770c6a67518db0`. Its 77 author cases include one
actual Worker/SQLite + public CLI + receiver + native-fixture loop, four composed
Worker cases, 26 service cases, 12 CLI cases, six explicitly stubbed unit cases
and 28 executor cases. The final source is registered in task0430 and frozen:
243 source pairs, digest
`11f084b9fe73c9d031ea18cc4bc0a13e2da58246da28a4d80b55dee943d51483`.
Argon reviewer `platform-session-compose-review` (`0aaf19de`) has acknowledged
the exact pin and produced a verified native first-action receipt. Its independent
verdict is **SCOPED REVISE**, preserved in `4d1462c` with report-only metadata
and cadence correction `bd3d641`. Both commits are retained; all 243 source
hashes and 13 Git ancestry rows match the audited report.
The 77 baseline cases, 64 selected compatibility cases and typecheck pass, while
12 novel probes successfully reproduce defects. Confirmed findings cover delayed
recipient-ACK lockout, anonymous native senders, stale/foreign host access to
private command offers and binding, lost ACK-response recovery, canonical Fleet
binding reconciliation, and pagination/reply provenance. Intermediate fixture
failures remain retained separately. A separate repair and new exact review are
required; the actual Grok Bot box -> Hetzner throwaway test remains open.
OpenCode Go / Muse Spark 1.3 worker `platform-session-repair` (`1f455987`)
finished repair `2ca4700a80af316538319da462a4c17dac17867a`, directly parented
by corrected report `bd3d641`. Actual task0430 records the source; all 246
source pairs are verified at digest
`6ec9613d0a6cc22a67bd1bc73d23e719bc004f5bd1881c6af284fbcb8a7cd15c`.
The author reports 169 distinct passing cases, including delayed-ACK reconciliation
after execution-lease expiry and canonical Fleet/native/workspace binding. Three
early-guard aborts and original failures remain preserved; bounded disjoint
retries completed coverage. The first-model-tool identity requirement was missed;
the later genuine native identity receipt does not erase that deviation.
Argon `platform-session-r2-review` (`e0fb234a`) has acknowledged the exact pin,
with its own first-tool identity verified. It independently reviews the source,
installed-native behavior and inherited host-auth dependencies. The verdict is
pending. At most two bounded genuine shell-native probes are authorized;
these cannot establish real-AI or cross-host acceptance. Source, full tier/cwd
qualification and the Grok Bot box -> Hetzner physical loop remain open.
Argon's latest checkpoint independently passed all 169 unique source cases and
typecheck, with no early-guard abort. Novel probes still reproduce inherited host
authority holes and new session defects: authorization changes during body reads,
late ACKs while an expired claim has not yet been swept, irrecoverable local
uncertain states, pending journals starved behind completed files and repeated
terminal ACK retries. Two genuine bounded shell probes also expose cross-workspace
reply-mailbox and timestamp mismatches, engine-binding and stop-containment gaps.
The final SCOPED REVISE report is being written; shell probes are not real AI
cross-host acceptance. The next repair must retain full tier/cwd scope.

M9 repair has 37 distinct author cases plus rendered UI checks. New composition
`ae21e27bc769e878af109ce50144da0fed5a5611` on accepted current main is registered
in actual task0424, with 240 source pairs frozen at digest
`2a2e6489c31062c7bb77b92639cde96f3c5c7863807420f8d5075a93945f8a10`.
Independent Codex reviewer `platform-metrics-r2-review` (`f5b90545`) has acknowledged
the exact pin and produced a matching native first-action receipt. Final report
`ce40f492ea15887116770e82ece799ab7b58ab8e` is SCOPED REVISE (two P1 and two P2
groups), directly parented by the reviewed source; all 240 source hashes remain
unchanged. The report is registered in actual task0424 and stays outside main.
New Muse worker `platform-metrics-r3` (`289bf092`) owns the bounded repair in a
fresh-main isolated worktree seeded from that immutable report; its actual native
first-action receipt is verified. Its frozen repair
`c85f4585dd7e6e5548f1fa3e74aefad374ac1e7a` reports the original 37 plus 13 new
regressions, six selected compatibility cases, typecheck and fixed reproductions
passing. Reviewer-label counts were corrected to unknown without event proof;
genuine empty zero/deduplication/explicit-event cases remain. Codex reviewer
`platform-metrics-r3-review` (`2210bd63`) completed **REVISE** report
`9618d972cd0f7e07e9e8eae34e181df73f7d5128`, directly parented by that exact
source. The report-only delta and all 243 source hashes match digest
`a65a54c122a618dd0eb3bb466af86414210487cc93450adcc6dfbad0040fb2f7`.
This is a different envelope from the session candidate. All 50 existing metrics
cases and the 15 earlier independent probes pass. New actual-route probes find
two P1 failures: a denied stale credential can purge current metrics, and a
superseded family can reclaim a newer registration. Three P2 groups remain in
outbound DTO validation, acceptance evidence/deduplication, and preserving the
selected host when the list becomes empty. An uncertain sparse-map expectation
is explicitly excluded from the verdict. Original reports and failures remain.

Muse worker `platform-metrics-r4` (`8ffb996f`) completed frozen repair
`0c7791761b8e762810430aad253613602637e707` and stopped. Actual task0424 records
the source; all 246 frozen hashes are verified, preserving the original envelope
and three new regression files. Digest:
`4877d9537661b9b45039ebe4cd6a19c8483ed6b8602c18a3f78f4f6e3362e737`.
Independent Codex HIGH reviewer `platform-metrics-r4-review` (`b84e62ea`)
finished **REVISE** report `4e6bfc2e5b1331bd0df497420a1d6b111611bae5`,
directly parented by the reviewed source. All 246 source hashes and the report-only
delta are audited. All 64 existing metrics cases pass independently. Novel
actual-route probes reproduce two P1 host-authority holes: revoking a credential
while the registration body streams still permits mutation, and consuming an
older approved grant after newer enrollment can replace the current owner.
Three P2 groups remain: Python/Worker DTO parity, invented aggregate review
counts and a delayed host response rendering under a different selected host.
Original tests, failures and all earlier reports remain preserved.

Muse Spark 1.3 `platform-metrics-r5` (`5deb7db5`) completed full repair
`f20b35a60af2de17c91303dd317da70b44f56174`, registered in actual task0424.
All 251 source hashes and 20 unchanged earlier reports are verified at digest
`67d07d9d545ef12eebc02c28d71a9c9238e455326b39c865e368a58c44cd310d`.
The author reports 58 Worker cases (29 existing, 11 new, 18 selected compatibility),
42 Python cases, three browser races, four renders, dakit checks and typecheck
passing. Original failures, a preventive guard abort and a three-case split
incident remain preserved; retries do not erase them.

The earlier Codex core review of `ab725d1` passed its eight author cases but
found two new unbound-machine issuance failures. Its native session/PIDs/cgroup
and history path disappeared before a final report; interruption cause is unknown.
Retained probes/results remain partial evidence. Muse repaired those cases in
`e795f00`, included in final `f20b35a`.
Fresh Codex HIGH `platform-metrics-r5-review` (`bf8cb749`) has acknowledged
actual task0433, verified its own native first-tool identity and owns full exact
R5 review. Its independent verdict is pending. No real enrollment or migration
was performed.

Head-owned actual task0434 has unaccepted draft `b9698bf3`, combining the two
source candidates. Its fresh 269-file union manifest is verified; only additive
Hub imports and CLI registrations needed manual conflict resolution. Separate
source and coupled reviews remain required. During its first push, the private
Agent Branches sidecar exited on an unhandled stdin EPIPE. The fork remained at
its original head. One restart of that existing private service, an authenticated
head reconciliation and one normal retry restored actual fork/WIP registration.
Source/config/store stayed unchanged; production runtime custody remains open.

The R4 author disclosed a monitoring gap and actual 46.29 MiB and 27.06 MiB
scratch peaks against an assigned 18 MiB; the monitor recorded growth without
aborting. These incidents remain. The independent review's 53 product commands
fell within its first sampled window; sampler exit143 has unknown cause.
Startup and metadata/disposal monitoring gaps are disclosed separately. Neither
final retained size nor later safe cache retirement proves historical continuous
compliance. New workers require preventive child-group guards and bounded serial
test groups. Source, producer adoption and runtime acceptance remain open.

- Host-binding source `8ff51a1` received Grok scoped acceptance in `b6f0f06`.
  The registration-field wording correction `85fdcec` received exact independent
  acceptance in appendix `80921a6`; the original report remains in history.
  Independent validation passed 30 focused host cases, one mock HTTP CLI flow
  and seven new probes. No tests were repeated for the documentation-only delta.
  This repairs source login/refresh binding transitions and the migration runbook;
  it performs no actual login, registry deletion, migration or credential rotation.
- Head verified all 209 source files byte-identical to accepted `85fdcec`,
  digest `b79a1675ff340548728e1c5fff05bad45ed4c05dd8647237a1de077b1ea12650`.
  Actual task 0425 contains `037bf03`. Canonical synchronization used the existing
  scoped token and normal fast-forward. Private remote restore passed fsck, nine
  baseline blob checks, all 209 source hashes and submit/conversations CLI help.
- Corrected Argon plan review `a13d227` accepts exact M12 plan `27e4b32` and its
  earlier pins as plan-only. All 17 checked Git/blob/SHA claims now match; the
  original report and its failed hash audit remain preserved. Explicit grants,
  verbatim storage, transport versus processing, and strict privacy boundaries
  were corrected before publication. This does not accept M12 source/runtime.
- Argon confirmed two retention defects in composed candidate `f6ec420`:
  blocked archived-parent discovery can wedge bounded cleanup, and a mismatched
  receipt can consume the SQL slot limit ahead of retireable work. The original
  diagnostic failure is distinguished from the clean defect assertions.
  Codex repair source `3518a850c0fd377b6bc7894912a4fcb83b3cdbe9`, on new main
  plus the frozen candidate, has 17 new regressions, nine original composed cases
  and typecheck passing. Its immutable report-only merge `254091a` is registered
  in task 0426. The initial two expected-behavior probes changed from failures
  to passes; original tests and failure evidence are retained. Remaining affected
  cohorts, final source freeze and
  distinct exact review remain required. No M4/M7 composition is on main yet.
- M12a reviewed source `c290454e88c49c6fe863d20dd2717d58522851d0` and
  report/main `bc796013d9f522d8a2e3ea050f7b264e2fabfc41` are registered in
  task 0427. The report’s nine checked hash claims match; the full source digest
  is `a9df93a3940de5e4f3c8205f07218a11aa7d33464f20f84b7cc570f5fae4a05f`.
  Source acceptance does not imply real session control or fresh-host takeover.
- M9 remains out of main after independent report `645ab784` requested eight
  repairs. The new Grok repair generation retains task 0424 and all evidence.
  Producer agreement, runtime ingestion and physical adoption remain open.

### Prior foundation and M5 integration checkpoint

**Conversation foundation, portable host storage and reviewed M5 follow-ups are on Hub main `6cf0c185495a33cf04ec2b986c3c901ed3de2cda`.**
It includes the conversation API, project-qualified F7 registry and credential
fixes, machine-bound public pairing, dakit conversations/fleet/auth/device UI,
CLI/native conversation bridge and explicit P3 retention-gap recovery. This is
source integration; deployment and physical fleet adoption remain open.

- Exact bundle `cfb4dc2`, patch `e8c91a9c`, was independently accepted by Argon
  in `5a4b938`. At foundation commit `7929a1b`, all 199 source hashes match digest
  `17aab235`; fresh integration
  typecheck passed. Retained independent evidence includes 453 Worker cases,
  635 host cases, 30 mock-browser cases, 89 real browser screenshots, public
  pairing and genuine own-session native round trips. Earlier counts are not
  additional unique coverage. Two metadata fields in the published report were
  explicitly corrected against Git; the original report remains in history.
- Actual Agent Branches task0418 fork contains the integrated main commit with
  a head-custody WIP receipt. The Windows follow-up is also preserved in genuine
  task0420. At that checkpoint, canonical Branches main and private GitHub recovery main
  both equalled `6cf0c18`. A disposable remote restore passed fsck, nine blob checks,
  all 207 source SHA-256 checks and old/new CLI help checks.
- Shared `~/git/agent-hub` remains at local HEAD `5dcdf71`: all 131 tracked files
  are verified unchanged. Native context confirmed zero physical scope overlap
  for the isolated integration worktree. The earlier cross-worktree dispatch
  hold was overly broad: peer ownership of the shared checkout and live ops
  remains respected; no peer ACK was inferred. Disjoint worktree integration
  follows the user's existing authorization.
- Windows composition `d79fab0` preserves all 193 non-Windows bundle paths and
  produces 203 source files, digest `5fb8eeac`. Argon `0da55c0` independently ran
  653 host passes plus one actual-Windows skip, 749 separate subtests, 92 Worker
  cases, six POSIX probes, public pairing and its own native round trip. Head
  reconciled the native journal and IDs with zero unresolved effects. Its report
  had inaccurate module paths, APIs, hash tables and source/pairing descriptions.
  Distinct Grok corrective audit `e5133fc` gives **SCOPED ACCEPT** to actual source
  `3888a43`: all 203 hashes verified, 49 focused host passes plus one Windows skip,
  58 files compiled, with prior execution evidence separately attributed. Original
  reports remain immutable. Publication annotation `16d66d6` normalizes evidence
  locators, corrects tracked-file counts and distinguishes final resource samples;
  it changes no source, verdict or test claims. Code is now on main, canonical
  Branches and private recovery; physical Windows DLL/NTFS/Win35/M11 is unproven.
- M5 source `212560b` received independent Grok **SCOPED ACCEPT** in
  `34ee3d0`. The five original defects and R2's MEDIUM retirement failure are
  repaired: current intervals continue after 4,096 historical receipts are
  reclaimed, unresolved effects survive cleanup/restart, retired keys cannot
  authorize new writes, and target read cursors stay unchanged. Independent
  evidence: 80 focused cases, 53 distinct compatibility cases, 12 adversarial
  probes, four memory-bridge cases and typecheck; repeated runs are not extra
  unique coverage. A Low hooked UTF-8 detail-size mismatch remains fail-closed.
  Head normal-merged the source and report as `6cf0c18` with all 207 source files
  byte-identical to the accepted pin and typecheck passing. Actual task0419
  fork/WIP, canonical main and private remote restore contain that integration.
  The restore verified all 207 source hashes (`1aee1637`) and both CLI help
  checks. Checks are not enabled by this source change. Physical M5, M8b,
  issue 102 and M11 remain open.
- M4's first composed source `1a15cb1` was rejected by Argon report `ab3b953`:
  stale target authority on replay, incomplete standalone lifecycle, false
  terminal/review dispositions and expiry filtering after pagination LIMIT.
  Codex repaired these in `7b6f7ff`, preserved in genuine task0422 fork/WIP.
  Author evidence: 19 link HTTP/lifecycle cases, two platform, five retention,
  one export and typecheck; intermediate failures remain retained. Distinct
  Argon `platform-links-r2-review` (`9673eaac`) accepted the exact candidate in
  `fc5bd30`: 27 selected tests, three independent probes and typecheck pass,
  with no findings. A mechanical report audit found one historical table cell
  assigning a report hash before that report existed; head will annotate this
  metadata before publication, preserving the original and source verdict.
  Codex `platform-links-m5-compose` (`fa957e2f`) is resolving two source conflicts
  with M5 main and adding shared retention/rollback tests. That composition needs
  a new independent review. Routing compatibility ACK remains pending.
- M7 source `abd48b8` received **REVISE** in Grok report `9574242` despite its
  23 role cases passing. An unresolved writer intent can permit a second project
  to execute for the same date after its active lease expires. This source stays
  unmerged. Codex `platform-role-leases-r2` (`3b36ac3f`) ACKed and traced both
  claim and execute transactions; it owns a bounded global writer-date repair
  and HTTP/SQLite regression. Final candidate `275c84a` is in actual task0423
  fork/WIP: 30 role cases, two identity cases and typecheck pass. Grok
  `platform-role-leases-r2-review` (`b8ffcce6`) ACKed and started independent
  review of that exact pin. Different dates must remain usable and unresolved
  evidence retained. The real writer backend still holds before process start;
  fake-effect tests do not implement M8b or prove physical M11.
- M9 has genuine task0424 on `6cf0c18`. Grok `platform-metrics` (`0295eaea`)
  ACKed its isolated Hub scope and committed early receiver `738f45e` to the
  actual task0424 fork/WIP. This is an untested source checkpoint. It is
  implementing authenticated bounded summary ingestion, a strict host projection
  adapter and dakit views. Existing Dashboard producers are read-only; private
  raw metrics and transcripts are excluded. No live Dashboard head was listed,
  so a producer-contract ownership request is recorded with the orchestrator.
  Producer agreement, observed ingestion and adoption remain pending.
- The first M4 bootstrap was stopped immediately after a head shell failed to
  halt on a capacity assertion. No tracked edits were produced; native history
  and first-action evidence are retained. Corrected fail-fast launch gating,
  lossless snapshot compression and fresh quota/resource admission preceded the
  new worker. Two exact disposable source reconstructions were removed only
  after 399 hash checks, retaining all original/reviewer sources and evidence.
  That launch’s four-worker admission was 511.52 MiB including remaining growth, below the
  512 MiB scratch limit. This incident is recorded rather than relabelled success.
- Optional creation of a new Branches integration task returned HTTP 500; no task
  ID or successful creation was claimed. Existing genuine task0418 was used for
  the actual main integration. New task identity must be reconciled before retry.

Argon completed the required post-main review of exact `16d66d6`: SCOPED
ACCEPT in `c1951e2`, no blocking source bugs and two Low host workflow findings.
Its valid manifests/probes are retained; Grok factual audit `a5685ed` corrected
invented commit/path/API descriptions while preserving the attributed Argon
source verdict. Publication `10c65ff` adds explicit parent/audit-snapshot notes
and separate head typecheck evidence; that record is on main and in recovery.
F-POST-1 concerns stale local machine identity after login/refresh transitions;
F-POST-2 concerns manual machine migration. F-POST-1 is assigned to task0425: Codex `platform-host-binding` (`cb9e7288`)
ACKed and confirmed the authenticated token-response contract. It is repairing
local binding transitions and documenting F-POST-2’s existing controlled migration
procedure, using synthetic config fixtures. No enrollment or migration is run.
Physical rollout and full-roadmap acceptance remain separate. M4, physical M5,
M7, M8a/M8b, M9, M10 and M11 remain active; M6 is already integrated. No deploy,
physical enrollment, service migration, native CLI/Rust installation or
credential change occurred.
Sections below retain the original survey and dated development checkpoints;
their historical main pins and pending-source statements are superseded here.

## New requirement — intake to tasks

Alexey’s 17 October intake brief adds M12 to the full roadmap: capture every
request with original text/source/time, status, notes, session/hub/host links,
report paths, commits and follow-ups/blockers needing Alexey. The existing `hub`
CLI must support task management and assignment through current routing, linking
the actual created session automatically. Assistants need authorized open-task
listing and follow-up. Current sessions and report files must be backfilled;
The addendum also requires per-task durable handoff context (verbatim requests,
decisions, rules, state, next action and approvals) and a global `hub handoff`
briefing so another authorized agent can continue with no previous chat context.
Assistants must maintain it as they work through CLI/API and later MCP.
A second addendum makes the hub the primary session-orchestration interface
across Hetzner, laptop and Win35, with psc retained as backup. M12 now includes
list/start/send with delivery confirmation/capture/stop via CLI/API and later
MCP, plus a required Grok Bot box -> real Hetzner throwaway-session loop.
API support comes first, MCP exposure later. These are new requirements, not
completed features. Routing-contract coordination is recorded; no ACK or runtime
assignment is inferred. See [M12 in PLAN.md](PLAN.md#m12--intake-becomes-tracked-assignable-work).

### 17 October source and intake checkpoint

Hub accepted main remains `6cf0c185495a33cf04ec2b986c3c901ed3de2cda`.
The following candidates remain subject to independent review and normal
integration; their test results do not establish deployment or host adoption.

- Combined M4/M5/M7 candidate `f6ec420cec3ab28fbea218dda478539b96fd4bbc`
  is registered in actual Agent Branches task 0426. Head verification passed
  typecheck and 39 unique focused cases: 30 role cases proved by the disjoint
  union of two bounded runs, plus nine conversation/link/ping cases. An initial
  larger run stopped at its early resource guard; its evidence remains retained.
  Argon explicitly acknowledged the final review pin; its verdict is pending.
- M9 metrics source `cef74e2bc09f48b104f775399c0e1d56cf7effc5` is registered
  in task 0424. The author reports seven real Worker/SQLite HTTP cases, six Python
  cases, typecheck, dakit checks and local fixture renders passing. A distinct
  Codex reviewer independently passed those 13 cases and typecheck, then reported
  nine adversarial failures across four defects: credential mutation during a
  streamed upload, revoked/expired snapshot reads, global storage caps and older
  idempotency replay after a newer snapshot. Final review and repair are pending;
  the original green tests do not establish source acceptance.
  Producer agreement, live ingestion, physical adoption and an observed live
  24-hour window remain unproven.
- Host-binding source `8ff51a1fac456849529d2e8728eae454caf9ec75`, task 0425,
  has entered distinct Grok review. Author synthetic tests and the mock HTTP CLI
  flow passed; no actual credentials, registry rows or host configurations were
  changed. The early source commit's unnecessary per-command hooks bypass was
  disclosed and prohibited; the final commit used normal hooks and checks.
  Independent review and normal integration remain required.
- M12a task 0427 now has an actual Codex worker in its own fresh-main worktree,
  with acknowledged first action. Its scope is durable intake/task API, existing
  public CLI integration, explicit assistant grants, versioned handoff context
  and `hub handoff`. Argon has separately acknowledged the full M12 plan and
  both addenda at coordination commit `da9fa7a`. Actual assignment, backfill,
  assistant adoption, later MCP and cross-host session orchestration remain
  required subsequent phases. Routing coordination remains pending; an attempted
  delivery was refused by the native readiness guard and left queued.

Argon’s M12 plan review at report commit `1f000fea` gives conditional scoped
acceptance of plan commits `598e7b8` and `da9fa7a`, with seven concrete contract
amendments and separate implementation/runtime gates. The plan now spells out
assistant access, atomic assignment linkage, CAS-fenced handoff, pending voice
transcripts, backfill provenance, authority boundaries and safe session control.
Head review requested corrections to the report’s grant alternatives, verbatim
storage/rendering distinction, transport acknowledgement semantics, privacy
claims and one source hash; the reviewer acknowledged those corrections. This
is plan review, not source or runtime acceptance.

M9’s final independent verdict is REVISE, report
`645ab784a2c7920089f313b5453f578cfc2f7635`, direct child of `cef74e2`.
Its eight findings cover current authorization, global storage bounds, retained
receipt replay, adapter windows/coverage/zero-review semantics and UI host/token/
access states. A new Grok repair worker now owns the exact report and source in
an isolated fresh-main worktree, retaining task 0424 and all failed evidence.
The original 13 passing cases remain baseline evidence. A new exact independent
review is required after repair; no M9 source is on main yet.

New workers each have a 1500 MiB/256-task limit, one-core execution and private
scratch bounds. Conservative aggregate admission after the M12a launch was
526,921,728 bytes against the 536,870,912-byte scratch limit. Fresh provider
quotas and the protected Codex gate passed. No additional launch or test growth
is admitted without a fresh measurement and outstanding-reservation accounting.

## 1. Product map

| Product | Checkout | GitHub main observed | Role in a conversation platform |
|---|---|---|---|
| Agent Hub | Shared checkout preserved at `5dcdf71` | `6cf0c18` | Control plane: auth, bus, registry, checks, fleet, routing, dashboard |
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


Private integration development is now allocated as actual Agent Branches task
`0414` (`platform-conv-int-0414`), Grok session `51db3a5a`. The worker reconstructs
one combined tree from transport `d9b4cde`, API `7c00467`, accepted registry
`ddaf80d`, accepted bridge gap recovery `0896ebe`, and pairing `1149f65`.
It owns only two inert proposal artifacts and private scratch. API and pairing
inputs remain provisional until their independent reviews finish; no reserved
source is edited. The combined acceptance path must issue its new agent token
through public device APIs before browser/CLI/native qualification.

Independent API review has so far passed typecheck and observed 208 passes and
one failure in the unchanged 209-case compatibility selection. The failing HTTP
fixture uses wall-clock claim expiry with a later pinned scheduled-tick clock;
the reviewer is testing that mismatch deterministically and continuing the
fairness/rollback audit. It is not yet a verdict or evidence that a genuinely
unexpired claim was deleted. Exact total-budget assertions remain required.
Both component reviewers and the new integration worker have verified genuine
native first actions. The main conversation source remains unchanged.


### Atomic cleanup repair and existing-view adoption — 17 October 2026

Independent API verification of `7c00467` executed 383 distinct cases: 379 pass,
four fail, plus typecheck passing. All six previous successful-call fairness
counterexamples now pass, including service reconstruction before each call.
Three failures reproduce one remaining composition atomicity defect: a later
conversation deletion or Hub cursor write can fail after earlier bus work has
committed. The authenticated retention endpoint also reproduces the partial
commit. The fourth failure is the confirmed HTTP fixture clock mismatch.
Grok `6c5ddc7b` is repairing both on original task `0409`; a new exact-source
review remains required. The combined worker has been told to retain `7c00467`
as provisional and wait for the committed repair before final validation.

M2b is now allocated as actual task `0415` (`platform-existing-ui-0415`), Codex
`1f675592`, in a fresh-main worktree. It owns only two inert proposal artifacts
and private scratch. It will adopt the official reviewed dakit package across
fleet, sign-in and device-pairing views, preserving routes, auth, CSRF and
trusted machine selection. Acceptance requires actual Worker/browser checks
across desktop and narrow layouts, both themes and authenticated/expired/error
states. The dakit owner has received a concrete scope/kit-lock request; no
agreement or source handoff is inferred. Native first action and ACK are verified.

Launcher repair checkpoint `6f7e1d1c533b7040840090fdf5e1a9c81c394ab9` is
preserved in task `0412` fork/WIP. The author verified all 25 reconstruction
hashes and reports 195 launcher, 182 guard, 48 host, 61 M6 and 32 qualified
Worker tests passing; final 42 Fleet/routing checks remain in progress.
A Miniflare test transiently used about 37 MiB against its assigned 25 MiB
scratch cap. The head has explicitly raised the task cap to 45 MiB after
checking aggregate headroom, without retroactively claiming compliance. No
production source/state or runtime account qualification is credited.

The full platform goal remains active. Hub main is still `5dcdf71`; component
reviews, combined validation, source handoffs and later milestones remain open.


### Frozen launcher revision and combined reconstruction — 17 October 2026

Launcher revision `6ee79d6ae13265135b89ca87d37d503de0099b76` is frozen and
preserved in task `0412` fork/WIP. Author verification passed 560 checks and
typecheck, with all 25 reconstruction hashes verified. The bounded SQLite M6
rerun covered all 61 cases exactly once at a 20,914,176-byte peak. The earlier
38,756,352-byte peak remains a disclosed overrun against the initial cap;
the later head reservation does not retroactively change that result.
Independent Argon `253dcd33` has acknowledged the exact pin, scope and first
action and is reviewing all original findings. Source owners have not handed
off, no runtime job ran, and full M8a/M8b remains open. In particular, Grok
thin-client exit still cannot release capacity while backend effects are unknown.

The private combined conversation reconstruction now applies F7, P3 and pairing
cleanly alongside the API candidate, including three-way merges of bus and
conversation services. The worker found no textual conflicts or omitted added
lines; this is preservation evidence, not semantic acceptance. It is running
characterization checks and will replace rejected API `7c00467` with the
committed atomicity repair before final validation. Pairing review is still
active. No tracked application source changed in this integration worktree.

M2b now has an initial executable inert patch. Typecheck, official kit lock,
color/border/scale checks and 107 inherited regression tests pass; the real
Worker/SQLite browser matrix is running. The new sign-in asset allowlist must
remain restricted to required static assets, with nearby private paths denied.
The worker will checkpoint the artifacts into its actual task `0415` fork.

The accepted F7 source handoff has also been escalated to the existing
orchestrator for explicit ownership adjudication of the reviewed Hub registry,
credential/device/auth hunks and liveness fixture. Deployment, environment,
domain and enrollment remain reserved. No handoff is inferred from silence.
Hub main remains `5dcdf71`; the complete roadmap and combined review gates
remain required.


### Public-issued token reaches the combined native path — 17 October 2026

Actual task `0414` now preserves inert integration checkpoint
`4f9bc78930d73db88b83420e687eb28b4aed92ee`. Its portable patch applies to fresh
main and leaves tracked application source unchanged in the development
worktree. Characterization passes typecheck and 426 author cases across
registry/pairing/conversations, inherited M6, host/P3, retention and composition.
The real local Worker/browser/Python CLI path issues the new agent token through
public device APIs and passes seven checks. The worker's genuine own native
inbox/reply/reconnect fixture also passes. Local human/machine fixtures and one
physical host remain the limits; this is not production enrollment or M11.

This checkpoint remains unaccepted. It still contains rejected API `7c00467`
and provisional pairing `1149f65`; both require the existing repair/review
outcomes before final combination. One of 29 mocked browser assertions fails
on an in-flight account switch. The head has required a reproducible diagnosis
that preserves account-isolation assertions; the real happy path does not clear
that failure. Existing native journals/effects are preserved, including an
initial fixture that stopped on a workspace assertion. The head also requested
correction of journal paths outside the assigned scratch scope before any
further native cycles. No uncertain effect is reset, deleted or blindly retried.

M2b's initial `9d80233` checkpoint is preserved in actual task `0415` fork/WIP.
Its expanded real Worker/SQLite browser matrix passes 84 screenshot cases, and
the sign-in duplicate-error refinement is in progress. A transient head sample
observed 52,051,968 allocated bytes against the earlier 30 MiB task scratch cap;
the head subsequently raised that task cap to 65 MiB within aggregate headroom.
The worker cleaned only completed owned scratch and is measuring both allocated
and apparent sizes. The earlier overrun remains disclosed; its exact historical
cause was not instrumented. Final reconstruction and independent review remain
required. Hub main is unchanged at `5dcdf71`.


API repair `8dc9235ce246ff8316048fa837b34b53ae7a0cdd` is now committed and
preserved in task `0409` fork/WIP. Its author passes typecheck and 387 tests,
including both real SQLite rollback regressions and deterministic early/late
HTTP clocks. Independent Codex `35054b0e` is reviewing the exact pin: initial
verification passes 211 tracked cases and all 59 persistent/fault probes,
including the three former atomicity failures. Expanded checks remain in
progress; no API acceptance is inferred yet.

Pairing review `8fa824c0046ec147e3d552987ca001e998dbb722` gives **REVISE** on
`1149f65`. Its independent tests exposed two MEDIUM gaps beyond the green
baseline: token/refresh responses omit the machine identifier required by the
actual CLI login configuration, and approval can resolve a different actor or
machine than displayed after concurrent registry changes. New actual task
`0416`, Codex `c645a36f`, is repairing these in two inert artifacts with real
CLI and GET/change/POST regressions. The integration and M2b workers have been
told to preserve that dependency and avoid duplicate protocol fixes.

M2b final `d80dfebd806ae320af699ab149b6c183e376ed07` is preserved in task
`0415` fork/WIP: 349 author tests, typecheck, official kit checks and 85 real
route screenshots pass. Independent Argon `44a36b91` is reviewing this exact
adoption proposal while the separate pairing repair remains required. Earlier
scratch overrun is retained in its report; the sampled later regular-file peak
is distinguished from an unknown historical maximum. This is a source proposal,
not a deployed or fully integrated M2b release.

The integration worker has received prospective scopes for its two exact
existing journal sets, so it can reconcile them against its own native
envelopes. The earlier path mismatch remains disclosed. Further native effects
stay paused pending that inventory and updated source inputs. All original
journal/effect evidence remains preserved; no uncertainty is discarded.


Independent API review is now **ACCEPT**, scoped to exact `8dc9235` and excluding
the separately reviewed F7 dependency. Report
`8ca59dc1b67d584aff724a50deef450f66a08af1` has the exact source as its parent;
all 394 distinct tests and typecheck pass. Expanded full-state rollback checks
cover Hub cursor faults, later message/member/header deletion faults, real
HTTP500 without partial commit, reconstruction and bounded retry. F7 remains
separately accepted, and pairing/combined validation/source handoff gates remain.
The integration worker has received the accepted API pin.

Pairing repair checkpoint `6dc1919395ca079de237b1ab3864db989972ce52` is now
preserved in actual task `0416` fork/WIP. Author evidence passes 33 new cases
and actual public Python CLI login with automatic bound/NULL/conflicting-machine
configuration checks and genuine own-UUID qualification without journal writes.
Final fresh reconstruction and a new independent review are still required.
M2b reviewer `44a36b91` has acknowledged its exact final input and dependencies.


### Accepted components and final assembly — 17 October 2026

Pairing revision `eee4d2f88305a6e64545c8e7b68f329a162811d1` now has scoped
independent acceptance in Argon report `fcbb782028187b6c669367596df3f6e79047e2ad`.
It fixes automatic CLI machine configuration and approval-time actor/machine
changes. Review covers 90 focused cases, 254 compatibility cases including all
61 M6 cases, 23 host cases, nine public Worker/browser/CLI/own-UUID qualification
groups and seven additional adversarial checks. No native journal was written
by that qualification. The head verified the retained reconstruction outputs.

M2b adoption proposal `d80dfebd806ae320af699ab149b6c183e376ed07` likewise has
scoped acceptance in Argon report `d10b09b34c81d49d6ca46f8b56da756203f31c99`:
349 cases, typecheck, 85 real Worker route screenshots, plus independent
private-path and browser probes. The official 21-file dakit lock is preserved.
All 16 proposed output hashes match the retained reconstruction and report.
This proposal's older pairing base requires the final assembly to preserve the
accepted revision's canonical displayed actor and explicit nullable machine
when extracting approval HTML into the UI module and scripts.

The previous integration worker ended; its committed artifacts and native
journals remain preserved. Read-only reconciliation found each recorded native
envelope exactly once and zero unresolved effects under the bridge's actual
cursor/delivery/reply predicate. This neither erases the earlier journal-scope
mismatch nor authorizes reusing that identity.

Actual Agent Branches task `0418`, Codex session `d19b72bc`, now owns the final
assembly. Early checkpoint `f9f6fb258e5abdf4d97e9292043828b4cc80ac82` is preserved
in its fork/WIP. It combines accepted API `8dc9235`, F7 `ddaf80d`, P3 `0896ebe`,
pairing `eee4d2f` and M2b `d80dfeb` with the reviewed transport. The candidate
has 199 reconstructed files, manifest digest
`74d1f17dcbf6acb0d2fa9a82827ac04cd9198a6411cc3d705cdd274d7a42c882`,
and an 88-path portable patch digest
`2ad3698a0ec376b2e3cb9de8f9e063ab8785eb0c53769f482cdba5230a7b200b`.
Author evidence passes 635 host cases, 453 unique Worker cases, typecheck,
85 M2b route screenshots and the public CLI/browser path. The mocked browser
suite passes 30 cases, including both causal orders of an account switch with
the same store/context through each switch. The earlier failure was a within-case
request/commit race; the initial cross-test-leak explanation is retracted.
Product conversation JavaScript remains unchanged. An optional importer test
still has one ambient registry-schema error; no production schema widening or
fake registry is used to hide it. The native self-message/reply check has an
explicit prospective scope ACK for the new genuine session's exact journals.
Its result, final artifact pin, distinct combined review and source-owner
handoff remain pending. Hub main is still `5dcdf71`.

Six accepted component snapshots are now on dedicated refs in the existing
private Hub recovery repository. A fresh remote checkout verified all six
pins, 14 selected blobs and `git fsck`; recovery main stayed exactly
`5dcdf7164b28bd0e3a1d717ac9090c054eca3f24`. These backups preserve component
source and proposals, without claiming integrated runtime delivery.

### Launcher audit and Windows portability — 17 October 2026

Argon launcher report `f5aed5c87cfccd42caed78fa870c1acdd5651c44` is disputed:
its purported 25-file hash table names different files and hashes from the
committed proposal. That immutable report supplies no integration credit.
Fresh Grok audit `f194f4fdc227592829b1ceb87f95423977b638f4`, directly on
`6ee79d6ae13265135b89ca87d37d503de0099b76`, independently reconstructs the
actual 25 paths and accepts the narrow source protocol after 560 suite cases,
four adversarial probes and typecheck. Full M8a/M8b stays open. Thin Grok
client exit does not prove backend death; inventory is owner attestation;
real native start/whoami first-action compatibility still fails closed. The
isolated leader option is help-supported, without runtime qualification.
Actual launcher/Hub execution source and ownership remain unchanged.

Actual task `0417` preserves Windows host proposal
`2de0a6c1846b110227cd1d15e99a7af6999158f5`, based on accepted P3 source.
It adds a stdlib POSIX/Win32 storage and lock implementation with portable
imports and a bounded Windows smoke kit. Author evidence: 205 passing tests,
one actual-Windows skip, 71 subtests and 58 compiled Python files; all 146
reconstructed output paths verified. New independent Argon session `be5df693`
is reviewing that exact proposal. It is separate from the first combined tree.
Linux and controlled Windows contracts do not prove actual DLL/ABI execution,
physical Win35 delivery or M11. Windows root remains stood down, and native
Rust source/build/install remains held. Full M1–M11 and M2b acceptance gates
remain in force.


### Final combined source enters independent review — 17 October 2026

Actual task `0418` now preserves final two-artifact proposal
`cfb4dc26985cbe39a1ae770ade4a6a57880edcbc` in its fork/WIP. The 88-path patch
has digest `e8c91a9c3f3a795360c85eec300d3df9187a361d57f9a9dfc9312ad60e673d10`;
all 199 reconstructed files match the final frozen manifest. Author evidence:
453 unique Worker cases, 635 host cases, 30 mocked browser cases, 85 real
fleet/auth/device screenshots plus four conversation theme/width screenshots,
nine public pairing/CLI/browser groups and ten final native/P3 groups pass.
Typecheck and kit/bundle checks pass. The optional importer retains its
29/30 external-schema limitation.

Two earlier native runs stopped on harness assumptions: the CLI's generic
HOLD output and the monotonic server-read watermark already advanced by
self-authored sends. Only the harness changed. The final run proves the gap
stage first with zero native mail: local cursor 1 remains below server-read 3,
a retained-message skip is refused, the missing sequence is explicitly audited
without changing server-read, replay is refused, and local catch-up reaches 3.
It then completes exactly one own delivery/reply and reconnect/dedup. The head
independently reconciled the final genuine native envelopes and journal:
cursors 3 and 4, one delivery, one completed reply, one gap audit, zero unresolved
effects. Both earlier settled journals and failed logs remain preserved.

Independent Argon `4aab5128` is reviewing exact `cfb4dc2` in a separate workspace.
No source acceptance, source-owner handoff or main integration is inferred.
Windows report `3d0dfadbed35812aeaacbb98f304acfecf711e91`, directly on `2de0a6c`,
gives SCOPED ACCEPT after independently reproducing 205 cases with the
real-Windows skip, stdlib smoke and seven further probes. Head verification of
its retained reconstruction evidence remains pending; physical Windows and
combined-tree portability acceptance remain open.
Private recovery now holds eight source/review refs, including the accepted
launcher protocol and corrected audit, with a fresh restore, 18 selected blobs
and fsck verified. Hub main remains `5dcdf71`; the full roadmap stays active.


### M5 development and source recovery checkpoint — 17 October 2026

Grok session `ace5d868` has acknowledged actual Agent Branches task `0419`
(`platform-pings-0419`) in a fresh main worktree. Its scope is a two-artifact
M5 proposal: extend existing scheduled checks with genuine conversation unread
backlog and safe conversation follow-up messages. It will preserve current
membership, project-qualified actors, interval/idempotency and retained-unread
semantics, and add no scheduler or terminal writes. It works privately against
frozen `cfb4dc2` as a provisional dependency; acceptance and integration require
the combined review and M1–M3 integration. M5 physical host/human/agent acceptance
remains a separate required gate.

Combined reviewer `4aab5128` has independently reconstructed all 199 files,
verified all 88 changed-path input/output hashes and all 131 unchanged tracked
files, and acknowledged the exact pin. The head has prospectively acknowledged
its precise own-session native journal scope and gap-first test sequence;
independent native results and the final verdict remain pending.

The head also reconstructed all 146 Windows proposal outputs from immutable
Git input and verified the aggregate and ten table rows against review `3d0dfad`.
The review retained logs/manifests but removed its temporary candidate and probe
source; the head's reproduction is retained separately. Physical Windows/DLL
execution and portability against the eventual combined tree remain unproven.
Private recovery now holds ten accepted source/review refs, with a fresh remote
restore, 21 selected blobs and fsck verified; recovery main remains `5dcdf71`.

The M4 routing ownership request remains queued: native delivery rejected a
stale idle report contradicted by later terminal activity. No readiness event
or ownership ACK was fabricated. Hub main is unchanged; existing source leases
and all later milestone gates remain in force.


### Windows composition checkpoint and preflight repair — 17 October 2026

Actual Agent Branches task `0420` (`platform-win-merge-0420`), Codex session
`4a0b74cb`, preserves early two-artifact checkpoint
`981430f4793160e4580789889e13d5c29e0a824f` in its fork/WIP. All six existing
Windows patch inputs match the frozen conversation tree and its four new paths
are absent there. Composition uses the reviewed Windows delta without adaptation:
203 frozen output files, with all 193 paths outside that delta unchanged.
The conversation base remains provisional pending its distinct Argon review.

The initial host union ran 654 cases: 649 passed, four mock-HTTP fixture errors
and one actual-Windows skip. Diagnosis found the runner's `HUB_CONFIG_FILE`
overriding fixtures' isolated XDG configuration, and fixture directories created
without the new backend's private-parent precondition. Removing that runner
override and setting child umask `077` makes the affected eight tests pass;
product source, tests, assertions and security predicates are unchanged. The
full union is rerunning and original failures remain retained. After a narrow
scope ACK, only the assigned workspace's `.local` parent metadata changed from
`0775` to `0700`; no journal existed and no native effect had occurred. This is
an adoption precondition, not permission to modify other workspaces.

The composed source still needs final tests, public CLI and bounded own-native
proof, distinct review, source ownership handoff and integration. Physical
Windows/DLL and M11 acceptance remain unproven. M5 has reconstructed its input
and is implementing conversation backlog/follow-up methods in private source;
its scheduler, membership and idempotency tests remain pending. The combined
Argon review is live with serial verification suites. Hub main is unchanged.


### Operational preparation for the prioritized session loop

The native hub operator has been asked to identify an existing enrolled Hetzner
host-agent entrypoint, configured workspace/profile and genuine native service
sender binding for the later throwaway acceptance test. The request is recorded;
no reply, activation custody transfer, deployment, enrollment or credential change
is inferred. A read-only runtime check found the operator's native session showing
a quota-exhausted error, and the existing fleet-host service exiting with status 1
while its timer remains active. The journal emits only a generic fleet failure;
the underlying cause is unknown. The protected shared checkout remains clean at
`5dcdf71`, behind accepted main `6bc91a1`. Metadata and binary-version receipts
are preserved privately; no service, config, credentials or checkout was changed.
A custody request is recorded with the existing desktop orchestrator, without an
ACK or authority transfer. Both new source candidates still require exact review.

A fresh admission check refused even a 1 MiB document-only M13 quota-plan review
while the two source lanes retain their reservations. No new worker, task or
worktree was created. Recompute capacity after confirmed completion; prioritize
the session repair, then run the independent quota-plan extension review.
