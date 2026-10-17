# Post-Milestone Argon Direction Review — Agent Hub Conversation Platform (`M6` Foundation & Full `M1`–`M11`/`M2b` Roadmap)

- **Reviewer**: `platform-product-review` (`gemini-4-argon-high`, independent deep-tier direction reviewer)
- **Reporting To**: `platform` (`agent-coordination` product head)
- **Verdict on Post-M6 Direction Checkpoint**: **`ACCEPT`** *(early foundation & direction checkpoint only; **does not** accept full conversation-platform completion, working conversation-path runtime delivery, or post-`M1` integration, which remain gated on the findings and open review gates below)*
- **Reviewed Coordination Snapshot**: `20dabd3e87ad1bf1c4cfd91b1449b7504f232ef0` ([`docs/platform/STATUS.md`](STATUS.md), [`docs/platform/PLAN.md`](PLAN.md) at `096bdd9dabcfe2449cac8479657530e5c159f7bf`, prior Argon plan review [`docs/platform/ARGON-PLAN-REVIEW.md`](ARGON-PLAN-REVIEW.md) at `6cb7a77`; pinned checkout preserved without silent rebase while incorporating subsequent head bus updates recorded in `5a118b5` / `312c53c`)
- **Reviewed Agent Hub `main` Snapshot**: `5dcdf7164b28bd0e3a1d717ac9090c054eca3f24` (exact `M6` source `71349b42ec88f9a0a1e228d4411e1c716c2d8e0f` + sanitized independent Argon review `docs/reviews/CLAIM-ADMISSION.md`, fast-forwarded from `213fcf61780b9a02645c747f1a13104a2e55b321`)
- **Date**: `2026-10-17`

---

## 1. Executive Verdict & Mandatory Open Gate for Working Conversation Path

### 1.1 Direction Verdict (`ACCEPT` with Explicit Post-`M1`/`M2`/`M3` Review Gate)

1. **Foundation Direction on `main` is Sound**:
   - The first product milestone integrated onto Agent Hub `main` (`5dcdf7164b28bd0e3a1d717ac9090c054eca3f24`, containing exact `M6` source commit `71349b42ec88f9a0a1e228d4411e1c716c2d8e0f` from Agent Branches task `0400` and the sanitized independent Argon acceptance report `docs/reviews/CLAIM-ADMISSION.md`) delivers genuine control-plane ownership enforcement over the authoritative `/api/bus/claims` table for editable Fleet and Routed launches without regressing existing routes, model-routing policy, or host lifecycle invariants.
   - Across `docs/platform/PLAN.md` (`096bdd9dabcfe2449cac8479657530e5c159f7bf`) and `docs/platform/STATUS.md` (`20dabd3e87ad1bf1c4cfd91b1449b7504f232ef0`), the head (`platform`) has preserved the **entire user objective** — turning Agent Hub into a real human/agent conversation platform and integrating all reusable unfinished competition work (`M1`–`M5`, `M2b`, and `M6`–`M11`) — rather than shrinking scope to a static UI mock, passive hold labels, or what already worked before this initiative.
   - Crucially, `platform` has maintained strict discipline between **scoped branch candidates** and **`main` integration**: `M2` UI (`7179868ae9f1723d9070a37f107a3b4f635c5cb6`), `M3a` CLI (`0a06f5e8409c00a95e85e7a43f8691c7df5f97b9`), and `M3b` native inbox bridge (`17424c66be6501a4c763ebfe694679880ff2cca7`) have each passed scoped independent reviews against frozen/fixture contracts, and the head has properly **held them off `main`** until `M1` Conversation API and `F7` project-qualified agent registry clear security review and pass genuine composed Worker/browser/CLI/native verification.

2. **Why a Second Post-Conversation-Path Argon Review Gate Remains Mandatory**:
   - This report is an **early post-land direction review** after the `M6` foundation milestone landed on `main` (`5dcdf716`).
   - At `5dcdf716`, **zero human/agent conversation routes (`/api/conversations/*`), conversation tables, conversation UI pages, or conversation CLI/bridge modules are on Agent Hub `main` yet**.
   - Therefore, this `ACCEPT` verdict on direction **must not** be cited as acceptance of the working conversation path or completion of the post-milestone review requirement in the operator brief (§4) for `M1`–`M5`.
   - **Mandatory Open Gate (`GATE-CONV-REVIEW`)**: A follow-up independent Argon review remains **explicitly open and required** once `M1` + `F7` + `M2` + `M3a`/`M3b` are integrated and verified against a real composed Worker (`src/worker.ts` exporting `ConversationHub` or wired `Hub`), rendered browser session, CLI client, and self-bound native `aplexer` inbox.

---

## 2. Pinned Inputs & Inspected Artifacts

| Surface / Milestone | Repository / Branch / Artifact | Pinned SHA / Digest | Inspected State |
| :--- | :--- | :--- | :--- |
| **Operator Brief** | `hub-platform-brief.md` | `2026-10-17` snapshot (`2403` bytes) | Full 5-part brief: survey, milestone plan, isolated worktree execution with `[skip ci]`, Argon plan + post-milestone reviews, and `dakit` design system. |
| **Coordination `main` (`STATUS.md`)** | `agent-coordination` (`main` / `origin/main`) | `20dabd3e87ad1bf1c4cfd91b1449b7504f232ef0` | Pinned review checkout recording `M6` landing at `5dcdf71`, AB canonical sync, private recovery clone restore, and candidate/review states for `M1`, `F7`, `M2`, `M3a`/`M3b`, and `M8a` (subsequent head updates in `5a118b5` / `312c53c` noted as live pipeline context without rebasing our checkout). |
| **Accepted Platform `PLAN.md`** | `agent-coordination` (`docs/platform/PLAN.md`) | `096bdd9dabcfe2449cac8479657530e5c159f7bf` | Full `M1`–`M5`, `M2b`, `M6`–`M11` roadmap; accepted by Argon plan review published at `6cb7a77` (`docs/platform/ARGON-PLAN-REVIEW.md`). |
| **Agent Hub `main` (`M6` Landed)** | `agent-hub` (`main` / `origin/main`) | `5dcdf7164b28bd0e3a1d717ac9090c054eca3f24` | Fast-forward from `213fcf61780b9a02645c747f1a13104a2e55b321` containing exact `M6` source `71349b42ec88f9a0a1e228d4411e1c716c2d8e0f` (`task-0400`) + public sanitized review `docs/reviews/CLAIM-ADMISSION.md` (`0` code diff between `71349b42` and `5dcdf716`). |
| **`M1` Conversation API R1 + Review** | `agent-hub` (`platform-api-repair` / `platform-api-rereview`) | Candidate `033d7105bdf0b8995f5c5e9e00047f2fc38d341b`; Review `95bb542` | Independent Codex review `95bb542` (`docs/reviews/CONVERSATION-API.md`) verified `F1`–`F5`/`F8`–`F9` fixes and requested `REVISE` for retention/accounting findings `F10`–`F16` plus open `F7` registry dependency. |
| **`M1` Conversation API R2 & Review** | `agent-hub` (`platform-api-r2`, task `0401`; combined `f872fd1`, task `0406`) | Checkpoint `a7452d84af6228ea8caa4e563a3f171e35272209`; final `da38cb2a00c092423d0b67419b0ea45d6a09dfa9` / `f872fd1`; Codex `REVISE` `626dac6` | Argon R2 repair of `F10`–`F16`; independent Codex review `626dac6` (`983c8d74`) found two remaining defects on `f872fd1` (`101`-row mixed cleanup at `limit=100` and interior-pruned `unread_count`), now under Grok repair in `task-0409`. |
| **`F7` Project-Qualified Agent Registry Proposal & Review** | `agent-hub` (`platform-registry-proposal` / `platform-registry-review` / `platform-registry-r2`, task `0399`) | Proposal `7d8cd282d292a45b0ec297ec1a8e86ff327fc332` (patch SHA-256 `5b149655d9a3a7ea3377eba15a69770314f0c5ba2bfdcc68950c7b0cf51aa684`); Review `eae7fdc0519f60681ff5e885061682471bb53193`; R2 base `cd74a27811cd984d1751a005b003ccc0d92e5c4e` | Inert patch in `docs/proposals/PROJECT-AGENT-REGISTRY.{md,patch}` (`110/110` core files untouched). Independent Argon review `eae7fdc0` (`docs/reviews/PROJECT-AGENT-REGISTRY.md`) returned **`REVISE`** with findings `F7-R1`–`F7-R5`; `task-0405` Codex repair active (see **Finding P1**). |
| **`M2` Conversations `dakit` UI R2 & Review** | `agent-hub` (`platform-ui-r2` / `platform-ui-rereview`, task `0403`) | Candidate `7179868ae9f1723d9070a37f107a3b4f635c5cb6`; Review `35fa7cd8599cd782a9a8d5ccf5d3f9196a77028b` | Independent Grok review `35fa7cd8` (`docs/reviews/CONVERSATION-UI.md`) returned **scoped `ACCEPT`** against protocol fixtures (`5/5` prior blockers resolved, official `dakit` checks `0` failures, `12` PNGs inspected). Held until `M1` + `F7` + composed Worker integration. |
| **`M3a` Agent Conversation CLI & Review** | `agent-hub` (`platform-cli` / `platform-cli-review`, task `0390`) | Candidate `0a06f5e8409c00a95e85e7a43f8691c7df5f97b9`; Review `c49c47e3` | Independent Argon review `c49c47e3` (`docs/reviews/CONVERSATION-CLI.md`) returned **scoped `ACCEPT`** (`45` focused CLI tests + `30` repaired `TestHttpCliReal` tests). Held until `M1` lands. |
| **`M3b` Native Inbox Bridge & Review** | `agent-hub` (`platform-bridge` / `platform-bridge-review`, task `0392`) | Candidate `17424c66be6501a4c763ebfe694679880ff2cca7`; Review `c5336283` | Independent Grok review `c5336283` (`docs/reviews/CONVERSATION-BRIDGE.md`) returned **scoped `ACCEPT`** (self-bound native inbox client, fsynced journal, loop filter, uncertain-effect hold; explicit limit that installed `aplexer 0.1.16` lacks `--idempotency-key`). |
| **`M8a` Host Execution Safeguard & Companion Proposal** | `agent-hub` (`platform-executor` `1f6d1913`, task `0402`; `b05384c1`, task `0407`; `platform-launcher-proposal` task `0404`) & `agent-quota-launcher` | Hub `1f6d1913bff86d82f6b4c806065905889f42c188` / `b05384c19afb5ac8d3b1594669e63c6b79bb6bb6`; Launcher `github/main` `5145d0df3ab6b6bcb06dcab500335ff61b8ff80c` (vs installed `53c7b2e44972985501e7625139e7d33db1d894ab`); Private launcher `f7e920a` | Task `0402` (`1f6d1913`, rebased as `b05384c1` in `task-0407`) holds unqualified headless offers before claim/submission. Task `0404` prepares a 3-artifact private companion proposal on `5145d0df` + `1f6d1913` (`docs/proposals/QUALIFIED-LAUNCHER.md`). Full `M8a` remains open. |
| **Design System (`dakit`)** | `dakit` (`main`) | `103912d69e8aec66d0e4fa552b070d54c363f7a3` (vendor lock `0e283cd`) | Unmodified by Hub workers; missing conversation thread/composer primitives filed to `dakit` owner. |

---

## 3. Assessment of Landed `M6` Foundation (`5dcdf716` / `71349b42`)

Inspection of `git diff 213fcf61780b9a02645c747f1a13104a2e55b321..5dcdf7164b28bd0e3a1d717ac9090c054eca3f24` in `agent-hub` (`docs/CLAIM-ADMISSION.md`, `docs/reviews/CLAIM-ADMISSION.md`, `src/claim_admission.ts`, `src/fleet.ts`, `src/routing.ts`, `test/claim-admission.test.ts`) confirms that the landed `M6` foundation satisfies its acceptance criteria and preserves existing Hub contracts:

1. **Single Claim Authority & Transactional Atomicity**:
   - `ClaimAdmission` (`src/claim_admission.ts:57-240`) reads existing `/api/bus/claims` rows (`claims` table) directly and reuses `BusService.validateClaimProject` and `BusService.isAuthorizedForActor` without introducing a competing lock table.
   - Claim authority, workspace policy (`fleet_claim_policy`), live credential validity (`credentials`), active-launch scope conflicts (`conflictingLaunches`), and capacity/job mutations run inside the same synchronous Durable Object SQLite transaction across all three phases:
     - `enqueue`: `POST /api/fleet/tasks` (`src/routing.ts:179-187`) and `POST /api/fleet/plan` (`src/fleet.ts:181-185`).
     - `reserve`: `FleetService.reserve()` (`src/fleet.ts:173-202`) and `RoutingService.dispatch()` (`src/routing.ts:72-120`).
     - `start`: `POST /api/fleet/launches/:id/claim` (`src/fleet.ts:333-350`).

2. **Verified Lifecycle & Capacity Invariants (`F1`–`F4` Resolutions)**:
   - **Unstarted Offer Retirement (`F1`)**: `retireInvalidOffer(row)` (`src/claim_admission.ts:69-77`) strictly guards `row.state === 'offered'`. When `heldReason(row)` is non-null, it atomically transitions `fleet_launches` (`state = 'failed'`, `verification_status = 'not_started'`, `exit_reason`, `finished_at`) and any linked `routing_jobs` row (`state = 'failed'`, `report = 'Not started: ' + reason`). `reconcileOffers()` (`src/claim_admission.ts:80-88`) performs a bounded `LIMIT 100` circular keyset sweep supported by `CREATE INDEX IF NOT EXISTS fleet_offered ON fleet_launches(id) WHERE state = 'offered'` (`src/fleet.ts:74`), and `/claim` re-reads the row after `accountStatus()` (`src/fleet.ts:345-348`) so an offer retired during capacity reconciliation can never be revived into `starting`.
   - **Retained Active Effects**: Once `offered -> starting` commits, `starting`, `running`, and `uncertain` launches are never retired by `retireInvalidOffer()` and continue holding account/machine slots and blocking overlapping edit scopes (`conflictingLaunches` at `src/claim_admission.ts:145-162`) even after the underlying bus claim expires or is released, until host-confirmed exit (`confirmed_exit: true`).
   - **Enqueue/Plan Conflict Enforcement & Truthful Queue Views (`F2`)**: `conflictingLaunches` runs in `enqueue`, `reserve`, and `start` (`src/claim_admission.ts:222-224`), and `RoutingService.view()` (`src/routing.ts:56-59`) computes `admission_hold` for unlaunched queued jobs while suppressing the generic capacity `queue_reason`.
   - **Dynamic Workspace Policy Enforcement (`F3`)**: `heldReason(row)` (`src/claim_admission.ts:229-239`) re-evaluates all access modes (`read`, `legacy_unspecified`, `edit`) against current `fleet_claim_policy`, retiring unstarted `legacy_unspecified` offers (`exit_reason = 'claim_required'`) if `require_claim: true` is enabled before `/claim`.
   - **Least-Privilege HTTP-Paired Agent Routed Edits (`F4`)**: Agents paired via standard HTTP device flow with `['bus:send', 'fleet:launch']` (`fleetEditor` in `src/routing.ts:132-135, 175-188`) can submit routed `edit` tasks (bound to `permission: 'fleet:launch'` and the exact `credential_id`), cannot submit routed `read`/`legacy_unspecified` tasks (`403 forbidden` without `routing:submit`), and cannot replay idempotency keys across token refresh (`sameEditCaller` at `src/claim_admission.ts:253-259`).

3. **Explicit Trust Boundary & Mandatory `F7` Merge-Time Adapter**:
   - `M6` is a control-plane admission and lifecycle gate over declared intent (`access.mode`); it is **not** an OS filesystem sandbox on the execution host and **not** `M8a` provider/account execution qualification.
   - **Merge-Time Requirement When `F7` Lands**: `src/claim_admission.ts:197-205` currently queries `SELECT kind, actor, subject, scopes, revoked_at, expires_at FROM credentials WHERE id = ?` and checks `(credential.actor || credential.subject) !== principal.actor`. When `F7` (`src/agent_registry.ts`) merges onto `main`, `src/claim_admission.ts:197-205` **must** include `registry_actor` and compare `credentialActor(this.sql, credential) !== principal.actor` so migrated bare credentials bound to `project:tag` via `registry_actor` match `authenticateBusRequest` (tracked in **Finding P1 / `F7-R4`** below).

---

## 4. Completed / Partial / Planned / Runtime-Unknown Map (`M1`–`M11` & `M2b`)

Passing local test counts (`vitest` / `unittest` / Playwright against fixtures) establish **source evidence only** and never prove physical multi-host or deployed runtime delivery. All milestones in the accepted `PLAN.md` (`096bdd9dabcfe2449cac8479657530e5c159f7bf`) remain required:

| Milestone | Target Capability | Current Source & Review State | Classification (`main` vs Branch vs Runtime) | Remaining Gates & Runtime/Ops Unknowns |
| :--- | :--- | :--- | :--- | :--- |
| **`M6`** | Ownership-aware launch & routing admission over `/api/bus/claims` | **Landed on Hub `main`** at `5dcdf7164b28bd0e3a1d717ac9090c054eca3f24` (source `71349b42ec88f9a0a1e228d4411e1c716c2d8e0f`, task `0400`). Argon `ACCEPT` (`docs/reviews/CLAIM-ADMISSION.md`; `163` Worker + `5` adversarial + `42` host tests + fresh-`main` integration rerun). | **Completed (Source on `main`)** / **Runtime Unknown (Not Deployed)** | Needs `credentialActor` adapter in `src/claim_admission.ts:197-205` when `F7` merges (`F7-R4`). Control-plane intent only (not OS sandbox or `M8a` account proof). Live Worker not deployed. |
| **`M1`** | Conversation API (`conversations`, `conversation_members`, `conversation_messages` with atomic `seq`, receipts, Free-plan retention) | `033d7105` rejected by Codex review `95bb542` (`F10`–`F16` + open `F7`). Argon R2 repair in task `0401` committed `a7452d84af6228ea8caa4e563a3f171e35272209` and `da38cb2a00c092423d0b67419b0ea45d6a09dfa9` (`31` public + `20` adapted probes), rebased as byte-identical combined candidate `f872fd1` (`task-0406`) on `5dcdf716`. Independent Codex review `626dac6` (`983c8d74`) of `f872fd1` found two remaining retention/unread defects (`101`-row mixed `bus`+`claims`+`conversation` cleanup at `limit=100` and `unread_count` miscounting interior-pruned gaps); Grok repair is active in `task-0409` on frozen `f872fd1`. | **Partial (Branch Candidate `f872fd1` Under `task-0409` Repair After Codex `REVISE` `626dac6`; Not on `main`)** | Requires `task-0409` repair of the two remaining `f872fd1` defects, independent different-model re-review on the new exact SHA, resolution/integration of `F7` (`task-0405`), and wiring `ConversationHub` / `src/hub.ts` under owner ACK. |
| **`F7` (`M1b`)** | Project-qualified agent registry (`(COALESCE(project,''), tag)` uniqueness + immutable `credentials.registry_actor` + bus/conversation/claim consumers) | Inert patch proposal `7d8cd282d292a45b0ec297ec1a8e86ff327fc332` (`task-0399`, patch SHA-256 `5b149655...`, `227` author tests in private copy). Independent Argon review `eae7fdc0519f60681ff5e885061682471bb53193` returned **`REVISE`** (`F7-R1`–`F7-R5`). Private-copy Codex repair is active in `task-0405` on Hub `main` `5dcdf716` (`cd74a278`) + `M1` `da38cb2a`. | **Partial (Inert Patch Proposal; `REVISE` at `eae7fdc0`; `task-0405` Repair Active; Not Applied)** | Must complete `task-0405` repair of `F7-R1`–`F7-R5` (including `src/claim_admission.ts` `credentialActor` adapter), pass Argon re-review, and obtain `hub-zai` ACK or explicit principal/operator source-lease decision before applying to `src/schema.ts`, `src/hub.ts`, `src/bus.ts`. |
| **`M2`** | `dakit` human conversation UI (`public/conversations.{html,css,js}`) | Candidate `7179868ae9f1723d9070a37f107a3b4f635c5cb6` (`task-0403`, parent `213fcf61`). Scoped Grok `ACCEPT` `35fa7cd8599cd782a9a8d5ccf5d3f9196a77028b` (`docs/reviews/CONVERSATION-UI.md`; all `5` R1 findings resolved, official `dakit` checks `0` failures, `24+7` browser probes, `12` PNGs inspected). | **Partial (Scoped Branch `ACCEPT` Against Fixtures; Held Off `main`)** | Still uses protocol fixtures and `src/worker.ts` still imports base `Hub`. Local composed transport verification is running in `task-0408`; must remain held off `main` until `M1` + `F7` clear review and pass composed real-Worker + browser verification. |
| **`M3a`** | Agent conversation CLI (`hub conversations ...`) | Candidate `0a06f5e8409c00a95e85e7a43f8691c7df5f97b9` (`task-0390`, parent `213fcf61`). Scoped Argon `ACCEPT` `c49c47e3` (`docs/reviews/CONVERSATION-CLI.md`; `45` focused CLI tests + `30` repaired `TestHttpCliReal` tests). | **Partial (Scoped Branch `ACCEPT` Against Frozen Contract; Held Off `main`)** | Held until `M1` + `F7` land; local composed transport verification in `task-0408` and final rebased `main` check required. |
| **`M3b`** | Opt-in self-bound native `aplexer` inbox participation (`conversation_bridge.py`) | Candidate `17424c66be6501a4c763ebfe694679880ff2cca7` (`task-0392`, parent `0a06f5e8`). Scoped Grok `ACCEPT` `c5336283` (`docs/reviews/CONVERSATION-BRIDGE.md`). | **Partial (Scoped Branch `ACCEPT`; Held Off `main`; Native Idempotency Gap Open)** | Installed `aplexer 0.1.16` lacks `--idempotency-key` (uncertain native sends hold and reconcile via `message log` without blind resend). Needs composed `M1` + `M3b` check (including `F11` pruned-gap behavior; see **Finding P3**). |
| **`M2b`** | Adopt `dakit` across existing `fleet`, sign-in, and device-pairing views | Not started (depends on `M2` and shared `src/hub.ts` / `public/fleet.*` scope agreement). | **Planned** | Requires `hub-zai` / operator scope handoff for `public/fleet.html`, `public/fleet.css`, and auth views, plus `dakit` checker + light/dark desktop/mobile verification. |
| **`M4`** | Conversation <-> routing job / fleet launch / review / outcome links (`conversation_links`) | Not started (depends on `M1` landing on `main` and `routing` schema ACK). | **Planned** | Must preserve `routing` policy/placement semantics untouched and pass member ACL + non-conversation routing regression tests. |
| **`M5`** | Safe conversation-unread checks (`src/checks.ts` watermark query, inbox-only default) + physical host/human acceptance | Not started (depends on `M1`–`M3` landing on `main` and host/domain ops readiness). | **Planned / Ops-Gated** | Source check must query `conversation_members.last_read_seq < conversations.last_seq` with zero PTY/composer writes. Physical acceptance gated on `hub.dtcdev.click` DNS (recorded as unresolved in the `20dabd3e` snapshot; no fresh production/DNS probe in this review scope) or enrolled `workers.dev` origin + host token + human session. |
| **`M7`** | Generic epoch-fenced role leases (`coordination/role_failover.py` semantics in Hub) | Reference source exists in `agent-coordination` (`98857ca` / preserved dirty worktree `30df32a`); Hub currently fences only `root` lease epochs (`src/jobs.ts`). | **Planned** | Depends on `M6`; requires transactional effect authorization + epoch check, Win35 root stand-down preservation, and independent fencing review. |
| **`M8a`** | Qualified host execution (launcher plan/run/status + bound account/profile/model/effort receipt) | Host safeguard/audit `1f6d1913bff86d82f6b4c806065905889f42c188` (`task-0402`), rebased onto `5dcdf716` at `b05384c19afb5ac8d3b1594669e63c6b79bb6bb6` (`task-0407` recovered Grok review after original reviewer session exited without a report), holds headless offers before claim/submission. Companion 3-artifact private proposal in `task-0404` (`docs/proposals/QUALIFIED-LAUNCHER.md`) targets `5145d0df` + `1f6d1913` for a narrow Grok/native `profile=null` OS-context variant. | **Partial (Host `HOLD` at `b05384c1` + Narrow Private Companion Proposal; Full `M8a` Open)** | `1f6d1913` audited stale `53c7b2e` (while `github/main` `5145d0df` has +5,086 lines and holds task-unit quota cohorts). `0404` covers only one `profile=null` variant; all other routes/named profiles and multi-host shared-vs-distinct account proof remain open (see **Finding P4**). |
| **`M8b`** | `writer-run`, `principal-wake`, and `head-recovery` job profiles in host dispatcher & checks | Not started (depends on `M7` and `M8a`). Contest issue 102 remains open. | **Planned** | Requires fenced role custody, draft preservation, uncertain-start reconciliation, and 2 controlled cycles + interruption test before retiring any host timer or closing issue 102. |
| **`M9`** | Connect Dashboard accounting producers to bounded Hub `/api/metrics` ingestion & `dakit` views | Compatibility collectors remain in `agent-dashboard`; Hub metrics ingestion/views not yet integrated. | **Planned** | Depends on `M2b` and producer owner agreement; must preserve 24 hourly UTC buckets and never fabricate token/cost numbers from quota percentages. |
| **`M10`** | Conversation-visible request-to-outcome & ask-ledger follow-through | Host-side `tasks_guard.py` / `ask-ledger.py` exist in contest repo; Hub conversation linkage not yet built. | **Planned** | Depends on `M4`/`M5`/`M8b`; must track canonical task, owner ACK, first action, due obligation, pinned review, accepted outcome, and human delivery with one safe inbox follow-up on overdue obligations. |
| **`M11`** | Supported host adoption, multi-host verification & one-by-one timer/service cutover | Not started (depends on `M1`–`M10`, DNS/enrollment/token ops gates, and explicit operations authorization). | **Planned / Ops-Gated** | Existing host systemd timers (`fleet-host`, `headless-root`, `principal-ping`, supervisor) remain active until replacement proof, acknowledged ops handoff, rollback, and disposable restore check pass. |

---

## 5. Verification of Ownership, Provenance, Recovery, `dakit`, Communication & Resource Guards

1. **File Ownership & Non-Inferred Leases**:
   - Reserved Hub files owned by `hub-zai` (`src/hub.ts`, `src/schema.ts`, `src/bus.ts`, `src/env.ts`, `src/liveness.ts`) and reserved `agent-quota-launcher` files were **not** modified on `main` or in unleased branches.
   - `M6` (`71349b42`) touched only `docs/CLAIM-ADMISSION.md`, `src/claim_admission.ts`, `src/fleet.ts`, `src/routing.ts`, and `test/claim-admission.test.ts` after explicit scope release and ACK from `routing`.
   - For `F7` (`task-0399` / `task-0405`, `7d8cd282`) and `M8a` (`task-0404`, `docs/proposals/QUALIFIED-LAUNCHER.md`), where `hub-zai` (pane quota-exhausted/empty while native session remains recorded) and `desktop-orchestrator` (`quota-launcher-head` has no native record) have not ACKed durable handoff requests, `platform` properly kept changes as inert proposal artifacts tested only in private scratch copies rather than inferring a lease from timeout or silence.
   - Protected `SPEC.md`, research archives, the dirty shared `aplexer` checkout, dirty `agent-coordination-role-failover` (`30df32a`), and peer worktrees remain untouched.

2. **Agent Branches Task Provenance & Independent Ordinary Git Recovery**:
   - Every implementation and review lane is tracked in real Agent Branches task forks (`task-0389` through `task-0409`), and `M6` (`5dcdf7164b28bd0e3a1d717ac9090c054eca3f24`) fast-forwarded cleanly onto both shared `agent-hub` `main` and the Agent Branches canonical branch from `213fcf61780b9a02645c747f1a13104a2e55b321` (with the completed `M6` integration worktree subsequently archived and cleaned).
   - Independent ordinary Git recovery was verified via the separate private recovery repository (`agent-hub-recovery`): a disposable clone restored `5dcdf7164b28bd0e3a1d717ac9090c054eca3f24`, passed `git fsck`, verified nine source/report blob hashes, and executed the restored host CLI `--help` check (and coordination `STATUS.md` follow-up `5a118b5` similarly verified private restore + `git fsck`).
   - Commit hygiene (`[skip ci]`, `Agent: <actor>/<verified-model>` trailers, and preservation of exact reviewed source commit `71349b42` as parent of `5dcdf716` without history rewriting) complies with Gate `IG5`.

3. **`dakit` Design System & Native Communication Guards**:
   - `M2` UI (`7179868ae9f1723d9070a37f107a3b4f635c5cb6`) uses official `dakit` (`103912d6`, lock `0e283cd`), passes `node test/conversations-ui.checks.mjs` and official `dakit` `check-{borders,colors,scale}.mjs` with `0` failures, and filed missing conversation thread/composer component needs to the `dakit` owner without forking `dakit`.
   - Native `aplexer` sessions use genuine self-bound identity (`a whoami --json`, `a context`, `a message`), inbox-only defaults (zero PTY/composer injection into busy or unknown terminals), and strict hold-on-uncertainty rules under the Rust build/install hold.

4. **Physical Resource & Financial Boundaries**:
   - Worker containment (`MemoryMax=1500M`, `TasksMax=256`), worktree-local scratch (`TMPDIR` under `.local/tmp` `<= 30 MiB`), host memory (`~37.5 GiB` available, `>= 10 GiB` floor), and root disk (`~74 GiB` free, `>= 50 GiB` floor) are respected.
   - As of the `20dabd3e` snapshot (with no fresh production or DNS probes executed in this review scope), no Cloudflare deployment, paid service activation, DNS mutation, global binary installation, dependency installation, or production/provider credential changes occurred.

---

## 6. Findings & Required Corrections (`P1`–`P5`)

### P1 [HIGH]: `F7` Project-Qualified Agent Registry Proposal (`7d8cd282`) Received Independent Argon `REVISE` (`eae7fdc0`) with Two High-Severity Blockers (`F7-R1`, `F7-R2`) and Three Medium/Low Fixes (`F7-R3`–`F7-R5`)

- **Evidence**:
  - While `STATUS.md` at pinned `20dabd3e` recorded the independent Argon review of `7d8cd282d292a45b0ec297ec1a8e86ff327fc332` (`task-0399`) as running, that review completed at commit `eae7fdc0519f60681ff5e885061682471bb53193` (`docs/reviews/PROJECT-AGENT-REGISTRY.md`, reviewer `platform-registry-review/gemini-4-argon-high`, recorded in subsequent `STATUS.md` `5a118b5`) with verdict **`REVISE`**:
    1. **`F7-R1` (High — Asymmetric Projectless + Project-Qualified Coexistence)**: Registering `{ project: 'pA', tag: 'worker' }` first and projectless `{ tag: 'worker' }` second is rejected (`409`), but registering projectless `{ tag: 'worker' }` first and `{ project: 'pA', tag: 'worker' }` second is permitted by `POST /api/agents` (`src/hub.ts:1019-1022`) and `POST /api/device/approve/:code` (`src/hub.ts:751-756`). Once both rows exist, the projectless agent's bound credential (`registry_actor = 'worker'`) is immediately bricked (`credentialActor` returns `null` -> `401`/`403`), and `DELETE /api/agents/worker` locks out with `409 ambiguous_agent_tag`.
    2. **`F7-R2` (High — Reserved Namespace & Singleton Actor Hijack)**: `registryAddress` (`src/agent_registry.ts:5-11`), `POST /api/agents`, and `POST /api/device/code` do not block reserved actor/namespace tokens (`admin`, `system`, `root`, `principal`, `hub`, `routing-client`) in both `project` and `tag`. Registering `projA:admin` or `projA:system` causes `BusService.canonicalActor` and `messages_bind_agents` to rewrite human `'admin'` and `'system'` bus messages to `projA:admin` / `projA:system`; pairing `projA:root` enters `JobsService.evaluateRootIncumbent()`; and imported `project = 'machine' | 'role'` rows bind `registry_actor = 'machine:*' | 'role:*'`, enabling bus inbox/send impersonation.
    3. **`F7-R3` (Medium — Ambiguous Bare Credential Sentinel & Deletion Revocation)**: Bare credentials migrated/issued while `pA:tag` and `pB:tag` collide store `registry_actor = <tag>` and can later promote if colliding rows are deleted; `DELETE /api/agents/:actor` leaves bound credentials unrevoked across re-registration.
    4. **`F7-R4` (Medium — `M6` `src/claim_admission.ts` Adapter)**: `src/claim_admission.ts:197-205` on `main` (`5dcdf716`) checks `(credential.actor || credential.subject) !== principal.actor` without `registry_actor` / `credentialActor(this.sql, credential)`, rejecting migrated F7 bare credentials with `403 claim_authority_unsupported`.
    5. **`F7-R5` (Low — Root `bus_dispatch` `reply_to` & `ConversationsService` `401` vs `403`)**: `src/jobs.ts:2486` compares uncanonicalized `toActor` against canonicalized `replyMsg.from_actor`, and `src/conversations.ts:633, 967-978` returns `401` instead of `403 unregistered_agent_principal` when `credentialActor` returns `null`.
- **Concrete Action**:
  1. Complete the active `task-0405` private-copy Codex repair (from Hub `main` `5dcdf716` / `cd74a278` + `M1` `da38cb2a`) covering `F7-R1` through `F7-R5` (including the `src/claim_admission.ts:197-205` `credentialActor` adapter now that `M6` is on `main`), and obtain an exact-SHA Argon re-review `ACCEPT`.
  2. Do **not** apply the patch to live Hub source until both (a) Argon re-review accepts the repaired patch and (b) either `hub-zai` ACKs the broadened `src/schema.ts` / `src/hub.ts` / `src/bus.ts` handoff on the bus or the principal/operator issues an explicit source-lease reassignment.

---

### P2 [HIGH]: `M1` Conversation API R2 (`da38cb2a` / `f872fd1` in `task-0401` & `task-0406`) Received Independent Codex `REVISE` (`626dac6`) for Two Remaining Retention/Unread Invariants (`task-0409` Repair Active)

- **Evidence**:
  - In `task-0401` (`platform-api-r2`), the Argon implementer committed `a7452d84af6228ea8caa4e563a3f171e35272209` and `da38cb2a00c092423d0b67419b0ea45d6a09dfa9` (`31` public + `20` adapted probes), which was rebased onto `5dcdf716` as byte-identical combined candidate `f872fd1` in `task-0406`.
  - While `f872fd1` resolved `F10` (`128` tombstone-cap LRU eviction), `F12` (retained child reply replay after parent pruning), `F13` (creator `created_by` fallback), `F15` (`last_message_preview` clearing), and `F16` (atomic counter backfill), the independent Codex reviewer (`983c8d74`, report commit `626dac6`) found that `f872fd1` still fails **two invariants**:
    1. **Cross-Service Cleanup Batch Bound (`F14`)**: Mixed `bus` + `claims` + `conversation` retention cleanup deletes **101 rows** when configured with `limit = 100`.
    2. **Interior-Pruned Unread Gap (`F11`)**: `unread_count` (`last_seq - Math.max(my_read_seq, pruned_through_seq)`) miscounts unread messages when **interior** messages are pruned (leaving retained messages both before and after a pruned gap) rather than a contiguous prefix.
  - Grok repair (`task-0409`) is active on frozen `f872fd1` with no `main` apply.
- **Concrete Action**:
  1. Complete `task-0409` Grok repair of both remaining `f872fd1` defects identified in Codex `REVISE` `626dac6` (strict cross-service `<= limit` deletion accounting across bus/claims/conversations, and exact retained-row `unread_count` / `pruned_through_seq` handling across interior gaps) and obtain an independent different-model re-review on the new exact SHA.
  2. Keep full `M1` main integration gated on: (a) independent `ACCEPT` of the `task-0409` repair, (b) repaired `F7` (`task-0405`) `ACCEPT` + source-lease resolution so cross-project same-tag registration works against the real `SCHEMA_SQL` `agents` table, and (c) wiring `src/hub.ts` / `src/worker.ts`.

---

### P3 [MEDIUM]: Maintain Hold on Scoped-Accepted `M2` UI (`7179868a`), `M3a` CLI (`0a06f5e8`), and `M3b` Bridge (`17424c66`) Until Composed `M1` + `F7` Integration, and Reconcile `M3b`'s Pruned-Gap Behavior

- **Evidence**:
  - `M2` UI (`7179868a`, Grok `ACCEPT` `35fa7cd8`), `M3a` CLI (`0a06f5e8`, Argon `ACCEPT` `c49c47e3`), and `M3b` Bridge (`17424c66`, Grok `ACCEPT` `c5336283`) are all based on `213fcf61` where `src/worker.ts` still imports base `Hub` (`./hub`) and `/api/conversations/*` is unwired. Merging them before `M1` + `F7` would ship dead static/CLI surfaces on `main`.
  - Furthermore, cross-checking `M1` R2 (`da38cb2a:src/conversations.ts:2978-3030`, `docs/CONVERSATIONS.md` §4.9 `F11`) against `M3b` (`17424c66:host/agent_hub_host/conversation_bridge.py:258-266`) shows an explicit integration intersection:
    - In `conversation_bridge.py:263-266`, `M3b` enforces `msg['seq'] != cursor + 1 -> raise BridgeCapabilityGap('History is not contiguous/canonical')`.
    - Under `M1` `F11`, if retention cleanup prunes messages ahead of a bridge participant's local `cursor` (`cursor < pruned_through_seq`, `gap_detected: true`, or across an interior gap), `msg['seq'] != cursor + 1` causes `M3b` to fail closed with `BridgeCapabilityGap` on every cycle.
- **Concrete Action**:
  1. Keep `M2`, `M3a`, and `M3b` held off `main` while `task-0408` exercises the local composed Worker/browser/CLI/native transport harness against frozen inputs and until `M1` (`task-0409`) + `F7` (`task-0405`) are accepted and wired.
  2. In `task-0408` and `task-0409`, explicitly test and document `M3b`'s behavior when `gap_detected: true` (`pruned_through_seq > cursor` or interior gap): either (a) keep `BridgeCapabilityGap` fail-closed by default and provide an explicit operator/CLI cursor catch-up option to `resume_after_seq` (`pruned_through_seq`) so pruned history is never silently skipped, or (b) record a durable gap notice and advance to `pruned_through_seq` if authorized, with a focused regression test.
  3. Re-run the composed verification (bound `ConversationHub` Worker + Playwright browser UI + `hub conversations` CLI + self-bound native `a message` inbox round-trip) on the final accepted `M1` + `F7` SHAs before pushing the conversation stack to `main` and triggering the second Argon review (`GATE-CONV-REVIEW`).

---

### P4 [MEDIUM]: Complete Recovered `M8a` Host Safeguard Review (`b05384c1` in `task-0407`), Reconcile `53c7b2e` vs `5145d0df` Launcher Audit, and Keep Full `M8a` Open Beyond `0404`

- **Evidence**:
  - Task `0402` (`1f6d1913bff86d82f6b4c806065905889f42c188`, `docs/EXECUTION-QUALIFICATION.md` + `host/agent_hub_host/execution_receipt.py`) makes the Hub host fail closed (`HOLD`) before claiming or submitting headless offers when account/profile/effort qualification is missing. After the initial Grok reviewer (`2ddf3991`) exited without a report, `platform` preserved its files/probes, rebased the frozen `1f6d1913` safeguard onto `5dcdf716` as `b05384c19afb5ac8d3b1594669e63c6b79bb6bb6` (`task-0407`), and launched a recovered Grok review.
  - Its `docs/EXECUTION-QUALIFICATION.md` table audited the installed shared checkout `53c7b2e44972985501e7625139e7d33db1d894ab`, whereas `agent-quota-launcher` `github/main` (`5145d0df3ab6b6bcb06dcab500335ff61b8ff80c`, `+5,086` lines ahead of `53c7b2e`) already contains `provider_admission.py`, `root_profile.py`, and `task_units.py` (which deliberately holds model task-unit quota acquisition until whole-cohort cleanup is qualified in `1c714bc`).
  - Task `0404` (`docs/proposals/QUALIFIED-LAUNCHER.md`) prepares a 3-artifact private companion proposal on `5145d0df` + `1f6d1913` for a single narrow execution path (Grok / native fixed owner-verified OS context `profile=null` variant, preserving the task-unit cohort hold).
- **Concrete Action**:
  1. Complete the recovered Grok review of `b05384c19afb5ac8d3b1594669e63c6b79bb6bb6` (`task-0407`) as the **host-side fail-closed safeguard (`HOLD`)**, and update its documentation note before or at merge so it cites `5145d0df3ab6b6bcb06dcab500335ff61b8ff80c` alongside installed `53c7b2e44972985501e7625139e7d33db1d894ab` rather than implying `5145d0df`'s guards are absent.
  2. Complete `task-0404`'s private companion proposal and obtain independent different-model review plus explicit launcher-owner handoff (currently pending response from `desktop-orchestrator`; `quota-launcher-head` has no native session record).
  3. Never call host `HOLD` (`1f6d1913` / `b05384c1`) or the single-variant `profile=null` companion (`0404`) full `M8a` completion: all other configured routes, providers, and named profiles (`profile != null`) and multi-host shared-account vs distinct-account runtime proof remain **open** in `M8a`, and provider labels or quota percentages must never be equated with actual account identity, tokens, or cost.

---

### P5 [LOW]: Qualify Blanket `"No ... credentials ... were changed"` Summary Line in `docs/platform/STATUS.md` (As of `20dabd3e` Snapshot)

- **Evidence**:
  - In `docs/platform/STATUS.md` as of the pinned `20dabd3e87ad1bf1c4cfd91b1449b7504f232ef0` snapshot, lines `617–618` accurately report: *"An expired scoped development token was renewed privately; the peer's original token file was preserved."*
  - However, lines `641–642` at the end of that same `20dabd3e` snapshot state: *"No deployment, cloud resources, domain, credentials, services or timers were changed."*
- **Concrete Action**:
  - In the next `docs/platform/STATUS.md` update (acknowledged by `platform`), qualify that line to read: *"No deployment, cloud resources, domain, production/provider credentials, services or timers were changed (only an expired scoped Agent Branches development token was renewed privately while preserving the peer's original token file)."*

---

## 7. Ordered Critical Path & When Concrete Owner/Operator Decisions Are Needed

### 7.1 Immediate Next Priorities for `platform` (No Operator Escalation Needed Yet)

1. **`M1` R3 (`task-0409`) Repair & Independent Re-Review**:
   - Complete the `task-0409` Grok repair on frozen `f872fd1` fixing the two defects from Codex `REVISE` `626dac6` (`101`-row mixed `bus`+`claims`+`conversation` cleanup at `limit=100` and `unread_count` across interior-pruned gaps), then obtain an independent different-model review on that exact new SHA.
2. **`F7` (`task-0405`) Private-Copy Repair & Argon Re-Review**:
   - Complete the `task-0405` Codex repair of `F7-R1` through `F7-R5` from `eae7fdc0519f60681ff5e885061682471bb53193` on Hub `main` `5dcdf716` + `M1`, including the `src/claim_admission.ts:197-205` `credentialActor` adapter (`F7-R4`), and pass an exact-SHA Argon re-review.
3. **`M8a` (`task-0407` & `task-0404`) Review Completion**:
   - Collect the recovered Grok review of `b05384c19afb5ac8d3b1594669e63c6b79bb6bb6` (`task-0407`) and complete + independently review the 3-artifact private companion proposal in `task-0404` (`docs/proposals/QUALIFIED-LAUNCHER.md` on `5145d0df` + `1f6d1913`), keeping full `M8a` explicitly open for non-`profile=null` routes.
4. **Composed Conversation Stack Verification (`task-0408` -> Final `main` Integration -> `GATE-CONV-REVIEW`)**:
   - Use `task-0408` to validate the local Worker/browser/CLI/native transport harness (including `M3b` `F11` pruned-gap handling per **Finding P3**); once `M1` (`task-0409`) and `F7` (`task-0405`) pass review and the `hub-zai` source-lease gate clears, re-verify the composed stack on `5dcdf716`, fast-forward `main` with private GitHub recovery verification, and trigger the mandatory **second Argon review (`GATE-CONV-REVIEW`)** before advancing to `M4`/`M5` and `M2b`/`M7`–`M11`.

### 7.2 Concrete Owner / Operator Decisions (Request Only When Pinned Artifacts Are Review-Accepted)

1. **`hub-zai` Shared Hub Source Lease (`src/hub.ts`, `src/schema.ts`, `src/bus.ts`, `public/fleet.*`)**:
   - **Current State**: `hub-zai`'s terminal pane is quota-exhausted/empty while its native session remains registered; repeated durable bus handoff requests have received **no ACK**, and `platform` has properly inferred no lease.
   - **When to Escalate**: Once `F7` R2 (`task-0405`) and `M1` R3 (`task-0409`) both have **accepted** independent review verdicts on their exact SHAs, if `hub-zai` still has not ACKed on the bus, present the exact reviewed patch SHAs and touched hunks (`src/schema.ts`, `src/agent_registry.ts`, `src/hub.ts`, `src/bus.ts`, `src/claim_admission.ts`) to the principal/operator for an explicit custody/lease transfer decision before applying them to Hub source.
2. **`agent-quota-launcher` Source Lease (`task-0404` Companion Patch on `5145d0df`)**:
   - **Current State**: `quota-launcher-head` has no native session record; durable request reached `desktop-orchestrator` with **no ACK** yet.
   - **When to Escalate**: Only after `task-0404`'s 3-artifact companion proposal on `5145d0df` + `1f6d1913` passes independent different-model review.
3. **Operational Rollout Gates (`M5` / `M11` — DNS `hub.dtcdev.click`, Host Enrollment Tokens, Live Deploy & Timer Cutover)**:
   - **Current State**: As of the `20dabd3e` snapshot (no fresh production or DNS probes were run in this review scope), `hub.dtcdev.click` DNS was unresolved, host access tokens / multi-host enrollments remain operational dependencies, and live systemd timers remain untouched.
   - **When to Escalate**: Only after the composed `M1`–`M4` conversation + task-link stack is reviewed, integrated on `main`, and verified locally.

---

## 8. Machine-Parseable Review Verdicts

Review: approved sha=20dabd3e87ad1bf1c4cfd91b1449b7504f232ef0 reviewer=platform-product-review/gemini-4-argon-high
Review: approved sha=5dcdf7164b28bd0e3a1d717ac9090c054eca3f24 reviewer=platform-product-review/gemini-4-argon-high
