# Independent Argon Plan & Survey Review — Agent Hub Conversation Platform

- **Reviewers**:
  - Initial 3-Snapshot Review (`1df0ac39340656dd118a090d9b3115068e38a30e`): `platform-plan-review` (Gemini 4 Argon High / deep-tier independent reviewer)
  - Targeted Final Follow-Up Review: `platform-plan-review-final` (Gemini 4 Argon High / deep-tier independent reviewer)
- **Reporting To**: `platform` (`~/git/agent-coordination`)
- **Review Branch**: `platform-plan-review` (base `origin/main` `98857caa1440898fa0495919c1116efb44453388`, prior review commit `1df0ac39340656dd118a090d9b3115068e38a30e`)
- **Pinned Input Lineage Reviewed**:
  1. **Initial Survey & Plan Draft**: `c90cdf8090424c92c26a879c88674784f28782e8` (authored by `platform-survey` / Grok) — **Verdict: `REVISE` (`changes-requested`, High/Blocking)**
  2. **Repaired Survey & Plan Draft**: `e854a8d242022d8b999e866accf3ba2a421ba0fa` (authored by `platform-survey` / Grok, parent `c90cdf8`) — **Verdict: `REVISE` (`changes-requested`, High/Blocking)**
  3. **Frozen Survey & Plan**: `cf91b0da45ac9fec1d87b4886bbaa2c5add5df55` (authored by `platform` / Codex on top of `e854a8d` after `platform-survey` released scope) — **Verdict: `ACCEPT` (`approved` in `1df0ac39340656dd118a090d9b3115068e38a30e`, subject to Binding Implementation Gates `IG1`–`IG5`)**
  4. **Final Pinned Survey & Plan Incorporating Review Gates**: `096bdd9dabcfe2449cac8479657530e5c159f7bf` (authored by `platform` / `gpt-6.1-sol` on branch `platform-survey`, parent `cf91b0da45ac9fec1d87b4886bbaa2c5add5df55`) — **Final Verdict: `ACCEPT` (`approved`, subject to refined Binding Implementation Gates `IG1`–`IG5` during milestone code reviews)**
- **Date**: `2026-10-17`

---

## 1. Executive Verdict & Four-Revision Audit Trail

### 1.1 Progression Across Pinned Snapshots

| Pinned Commit SHA | Author / Model | Scope of Snapshot | Argon Verdict | Summary of Disposition |
| :--- | :--- | :--- | :--- | :--- |
| `c90cdf8090424c92c26a879c88674784f28782e8` | `platform-survey` (Grok) | Initial `docs/platform/STATUS.md` and `docs/platform/PLAN.md` | **`REVISE`** (`changes-requested`, High / Blocking) | Blocked by **B1** (unsafe `messages` table mutation & ULID/ack reuse conflicting with `src/bus.ts` and `docs/CONVERSATIONS.md`), **B2** (omission of unfinished product work from milestones), **B3** (native bridge identity/provenance gap), **B4** (`src/checks.ts` & PTY wake contradiction), **B5** (erroneous `reviewer SHA != implementer SHA` rule), and **B6/F7/F8** (status/DNS/UI contract gaps). |
| `e854a8d242022d8b999e866accf3ba2a421ba0fa` | `platform-survey` (Grok) | First repair of `PLAN.md` and `STATUS.md` | **`REVISE`** (`changes-requested`, High / Blocking) | Repaired **B1** (adopted dedicated `conversations`, `conversation_members`, `conversation_messages` with atomic `seq` and zero `messages` dual-write), **B5** (same candidate SHA, distinct reviewer/model), and **F8** (attributed current `hub.dtcdev.click` DNS/health failure). **Still failed B2**: mapped reusable unfinished work (claims-in-launch, generic role failover, `writer-run`/`head-recovery`, accounting producers, request-to-outcome obligations) to passive **"Hold"** dispositions instead of executable milestones. |
| `cf91b0da45ac9fec1d87b4886bbaa2c5add5df55` | `platform` (Codex) on top of `e854a8d` | Frozen `PLAN.md` and `STATUS.md` with executable `M2b`, `M3a`/`M3b`, and `M6`–`M11` roadmap + checkpoint evidence | **`ACCEPT`** (`approved` in `1df0ac3` with Binding Implementation Gates `IG1`–`IG5`) | Resolved **B2** and **B6** by replacing passive "Hold" dispositions with concrete executable milestones (`M2b`, `M3a`/`M3b`, `M6`, `M7`, `M8a`, `M8b`, `M9`, `M10`, `M11`), recording actual Agent Branches task allocations (`task-0389`, `task-0390` at `0a06f5e`, `task-0391`, `task-0392`), and distinguishing task allocation / local unit tests / nonce probes from reviewed `main` integration and physical multi-host acceptance. |
| `096bdd9dabcfe2449cac8479657530e5c159f7bf` | `platform` (`gpt-6.1-sol`) on top of `cf91b0d` | Final `PLAN.md` and `STATUS.md` applying `IG3`/`IG4`/`IG5` text repairs and `Independent review checkpoint` | **`ACCEPT`** (`approved` by `platform-plan-review-final/argon` with refined `IG1`–`IG5`) | Applies `IG5` stale-hold fix in `STATUS.md` §10 (`L414`), replaces contradictory `M5` wake text in `PLAN.md` (`L191–196`) with durable native inbox-only defaults and conversation read-watermark checks, codifies trailer/provenance rules without rewriting reviewed SHA history (`PLAN.md` `L282–284`), and records the `Independent review checkpoint` (`STATUS.md` `L450–464`) while preserving all brief scope and `M2b`/`M6`–`M11`. |

### 1.2 Why `cf91b0da45ac9fec1d87b4886bbaa2c5add5df55` Cleared Initial Plan Review (`1df0ac3`)

1. **No Silent Scope Shrinkage**: `cf91b0d` preserved the full scope required by the operator task brief (§1–2). `M1`–`M5` deliver the first working conversation platform slice, while `M2b` and `M6`–`M11` schedule every reusable unfinished capability (full `dakit` adoption across existing Hub views, ownership claims in launch admission, generic epoch-fenced role failover, launcher account/profile attribution, `writer-run`/`principal-wake`/`head-recovery` job profiles, Dashboard `/api/metrics` producer integration, conversation-linked request-to-outcome/ask-ledger follow-through, and gated one-by-one host timer migration).
2. **Honest Separation of Allocation vs Acceptance**: `cf91b0d:docs/platform/STATUS.md` (`L433–448`) explicitly stated that no conversation product commit was on `agent-hub` `main`, that `task-0389` (API) and `task-0391` (UI) were allocated but unaccepted, that `task-0390` (CLI `0a06f5e`) awaited independent Argon review and API integration, and that `task-0392` (`M3b`) had only a local nonce-only self-send/reply probe at that point.
3. **Binding Implementation Gates (`IG1`–`IG5`, §6)**: Because `cf91b0d` left the earlier `M3` and `M5` prose sections and `STATUS.md` §10 concise while adding the authoritative `M2b`/`M3a`–`M3b`/`M6`–`M11` table and `Platform integration checkpoint`, §6 codified the code-level verification gates (`IG1`–`IG5`) for milestone code reviews.

### 1.3 Targeted Final Review of `096bdd9dabcfe2449cac8479657530e5c159f7bf` & Factual Gate Clarifications

Inspection of `git diff cf91b0da45ac9fec1d87b4886bbaa2c5add5df55..096bdd9dabcfe2449cac8479657530e5c159f7bf` (`2 files changed, 26 insertions(+), 5 deletions(-)`) and immutable `git show 096bdd9dabcfe2449cac8479657530e5c159f7bf:docs/platform/{PLAN,STATUS}.md` confirms:

1. **Full Scope & `M2b`/`M6`–`M11` Roadmap Preserved**: All original operator brief requirements and the entire `M1`–`M5`, `M2b`, and `M6`–`M11` roadmap (`PLAN.md` L31–41, L228–265) remain intact in `096bdd9`.
2. **Document Corrections in `096bdd9` Verified**:
   - `PLAN.md` L191–196 (`M5`): Replaces the earlier `- Wake: only hub bridge + existing aplexer message deliver...` line with: *"Notification defaults to a durable native inbox only, without PTY or composer writes. Extend existing checks to query conversation read watermarks; the current 1:1 bus backlog query cannot detect conversation unread state. Any future opt-in terminal wake needs its own reviewed stable-idle/empty-draft and single-attempt uncertainty guards. Fenced principal-wake belongs to M8b; M5 does not close contest issue 102."*
   - `PLAN.md` L282–284 (`Next actions` #3): Adds: *"New candidate/release commits carry an `Agent: <actor>/<verified model>` trailer; retain already reviewed source SHAs and record provenance instead of rewriting their history."*
   - `STATUS.md` L414 (`§10. Leftover planned work (mapped)`): Replaces the stale `"stay **held** with their current owners"` phrase with `"remain open in executable M2b/M6–M11"`.
   - `STATUS.md` L450–464 (`### Independent review checkpoint`): Accurately records the Argon plan review progression (`c90cdf8` REVISE, `e854a8d` REVISE, `cf91b0d` ACCEPT with gates), notes that code worktrees still require separate exact-version reviews, records that Argon separately accepted CLI `0a06f5e` against the frozen API draft (45 focused tests verified; full host run retained one real-HTTP fixture environment error requiring a dependency-enabled rerun before integration), notes that native bridge candidate `17424c6` is in its actual task fork (`task-0392`) with independent Grok review started (**not accepted yet**), and notes that the M6 claims worker started only after `routing` explicitly acknowledged scope and admission semantics.
3. **Factual Review-Gate Clarifications Incorporated in This Follow-Up (`(a)`–`(e)`)**:
   - **(a) `IG3` / `B3` Self-Bound Native Participation vs Separate Service Binding**: Prior report `1df0ac3` hardcoded a separate `hub-bridge` `NativeServiceBinding`. However, the current supported `M3b` design uses each participant's existing `kind = 'agent'` token and its genuine current native session UUID/tag/workspace (`a whoami --json`), performing native self-send/reply with explicit loop/ack filtering — which the earlier Argon CLI reviewer empirically verified in its own bound session using the real installed `a` binary with no external sender. Refined **Gate IG3** (§6) qualifies positive native binding/provenance (no borrowed identity, `--from`, or `APLEXER_*` overrides) rather than mandating a specific service name/helper; a separate `NativeServiceBinding` is required only if a separate non-member service process actually originates native sends. Full `M3b` code remains subject to independent code review (`17424c6` in `task-0392` is not accepted yet).
   - **(b) `IG2` / `F7` Official `dakit` Scale/Border/Color Enforcement**: Prior report `1df0ac3` phrased `IG2` as `"zero raw hex/px literals"`, which is stricter than official `dakit` (`~/git/dakit/docs/adoption.md` L124–191) and would reject legitimate 4px-grid layout (`padding`/`margin`/`gap`/`inset` multiples of `4px`), `@media (max-width: 820px)` breakpoints, and neutral `1px` borders. Refined **Gate IG2** (§6) requires actual `dakit` components (`.dk-*`), semantic `--dk-*` roles, `--dk-text-*` type scale and `--dk-space-*` / 4px-grid spacing scale, and passing `dakit`'s official checkers (`sync.mjs --check`, `check-colors.mjs`, `check-borders.mjs`, `check-scale.mjs`).
   - **(c) Model Routing Tiers Verified Against `config/model-routing.json`**: Prior report `1df0ac3` (§5 Row #7) parenthetically listed `(grok, kimi, minimax, codex, argon, sonnet)`. Verified against `~/git/agent-hub/config/model-routing.json` (`L14–166`, at `213fcf61780b9a02645c747f1a13104a2e55b321`), the actual Hub routing tiers are `deep` (`astra` / `gpt-6-astra`, `argon` / `gemini-4-argon-high`, `opus`), `daily` (`sol` / `gpt-6.1-sol`, `sonnet`, `glm-flash` / `glm-5.3-flash`, `muse` / `opencode-go/muse-spark-1.3-contributor`, `deepseek-flash` / `opencode-go/deepseek-v4.1-flash`, `grok` / `grok-4.6`), and `quick` (`haiku`, `luna` / `gpt-6-luna`), with `default_tier: "daily"`, `disabled_providers: ["claude"]`, `explicit_only_providers: ["codex"]`, and `preferred_providers: ["zai", "go"]`. Corrected in §5 Row #7 below.
   - **(d) `IG4` / `M5` Safe Inbox-Only Default & Optional Future PTY Wake**: Keeps the durable native inbox-only default (`--queue`, zero PTY/composer writes) and conversation read-watermark check (`conversation_members.last_read_seq < conversations.last_seq`). There is no implied requirement to type into terminals during `M5`; any optional future PTY wake requires separately reviewed stable-idle/empty-draft and durable single-attempt uncertainty guards.
   - **(e) `IG5` Commit Trailers & Preserved Source SHA History**: New candidate/release commits carry `Agent: <actor>/<verified-model>` and `[skip ci]`, while already-reviewed source commit SHAs are retained without rewriting history, keeping source-tree and pinned-review provenance explicit.

---

## 2. Inspected Code & Documentation Revisions

All findings in this review are grounded in the following exact repository revisions and files inspected on `2026-10-17`:

| Repository / Input Surface | Portable Path / Reference | Inspected Revision / State | Notes |
| :--- | :--- | :--- | :--- |
| **Pinned Review Input #1** | `git show c90cdf8090424c92c26a879c88674784f28782e8:docs/platform/{PLAN,STATUS}.md` | `c90cdf8090424c92c26a879c88674784f28782e8` | Initial survey and plan draft (matching `.local/` review snapshot retained privately) |
| **Pinned Review Input #2** | `git show e854a8d242022d8b999e866accf3ba2a421ba0fa:docs/platform/{PLAN,STATUS}.md` | `e854a8d242022d8b999e866accf3ba2a421ba0fa` | Survey repair aligning M1 dedicated store, review rule, and DNS probe attribution |
| **Pinned Review Input #3** | `git show cf91b0da45ac9fec1d87b4886bbaa2c5add5df55:docs/platform/{PLAN,STATUS}.md` | `cf91b0da45ac9fec1d87b4886bbaa2c5add5df55` | Plan adding executable `M2b`, `M3a`/`M3b`, `M6`–`M11` and integration checkpoint |
| **Pinned Review Input #4 (Final)** | `git show 096bdd9dabcfe2449cac8479657530e5c159f7bf:docs/platform/{PLAN,STATUS}.md` | `096bdd9dabcfe2449cac8479657530e5c159f7bf` | Follow-up on `platform-survey` applying `IG3`/`IG4`/`IG5` clarifications and `Independent review checkpoint` |
| **Coordination Repo** | `~/git/agent-coordination` | `98857caa1440898fa0495919c1116efb44453388` | `docs/ROLE-FAILOVER-RUNTIME.md`, `coordination/role_failover.py`; review branch `platform-plan-review` at `1df0ac39340656dd118a090d9b3115068e38a30e` |
| **Agent Hub (`main`)** | `~/git/agent-hub` | `213fcf61780b9a02645c747f1a13104a2e55b321` | `src/{schema,bus,hub,fleet,routing,checks,jobs}.ts`, `config/model-routing.json`, `host/agent_hub_host/{bridge,native_bridge,oversight}.py`, `docs/{SPEC,GENERIC-HUB}.md`, `public/{index,fleet}.html` |
| **Candidate M1 API Spec** | `docs/CONVERSATIONS.md` (`task-0389` API worktree) | Base `213fcf61780b9a02645c747f1a13104a2e55b321` (unmerged WIP) | Inspected to verify storage/ordering/identity contract against `PLAN.md` |
| **Role Failover Branch** | `~/git/agent-coordination` (`codex/role-failover-20261006`) | `30df32ae2bbcc47558556e03701e28bae4a10022` | Preserved untouched (`coordination/failover_bridge.py`, `role_failover.py`) |
| **Design Kit (`dakit`)** | `~/git/dakit` | `103912d69e8aec66d0e4fa552b070d54c363f7a3` | `docs/adoption.md`, `docs/shell.md`, `docs/list-detail.md` |
| **Agent Bus** | `~/git/agent-bus` | `bf351f423441d17d981e95f0a202e79dc4466003` | Local behind `origin/main` (`a9156b9`) by 1 commit |
| **Agent Dashboard** | `~/git/agent-dashboard` | `6863b99e9ddc2ce1a5aed6da8b4b5a16126a45da` | Local ahead 2 / behind 1 vs `origin/main` (`3f126df`) |
| **Agent Quota Launcher** | `~/git/agent-quota-launcher` | `53c7b2e44972985501e7625139e7d33db1d894ab` | Local behind `origin/main` (`5145d0d`) |
| **Agent Relay** | `~/git/agent-relay` | `0a2895b26f6dbea710a5cfe30dd37f22c8da0c4e` | Clean (`main` === `origin/main`) |
| **Cloudflare Agent Git** | `~/git/cloudflare-agent-git` | `642110a99ad4e635d1b48fdfda4f9a5ff75d1e39` | `AGENTS.md`, `coordination/{OPERATING-MODEL,RESOURCE-POLICY,USER-STEERING}.md`, `_docs/04-communication.md`, `_docs/05-recovery.md`, `_docs/team/06-reviewer.md`, `scripts/guards/{review_gate,claims_check}.py`, `scripts/delivery/tasks_guard.py` |
| **Agent Branches** | `~/git/agent-branches` | `a35c4bdf2f1771ab8118248958506b1a037691d6` | Detached HEAD locally; `origin/main` at `82e310f` |
| **Aplexer Watch** | `~/git/aplexer-watch` | `837edffe73655aa257da15154328d4692b44982d` | Clean (`main` === `origin/main`) |
| **Operator Brief & Prior Reports** | Retained privately (`2026-10-17` snapshot) | Snapshot as of `2026-10-17` | Operator platform brief and prior status/inventory/routing/messaging reports cited in `STATUS.md` §8 |

---

## 3. Initial Blocking Findings on `c90cdf8` & `e854a8d` (`B1`–`B6`) and How `cf91b0d` & `096bdd9` Resolve Them

### B1. M1 Storage, Ordering, Receipt, and Identity Architecture Conflict

- **Source in `c90cdf8` (`PLAN.md` L15–16, L50–63)**:
  - Proposed adding `conversation_id` onto the existing 1:1 `messages` table (`src/schema.ts:187-205`, `src/bus.ts:53-70`), keeping ULID ordering, and mapping per-member receipts onto existing `ack`.
- **Why `c90cdf8` Failed Against Actual Source**:
  1. `messages` has `to_actor TEXT NOT NULL`, `UNIQUE(from_actor, idempotency_key)` globally per sender, and single-recipient columns `delivered_at, read_at, acked_at, accepted_at, completed_at` (`src/bus.ts:484-513`). A group conversation cannot store a single row in `messages` without either fan-out dual-writing $N$ rows (breaking single message IDs and atomic ordering) or breaking `to_actor` and single-recipient `acked_at` invariants.
  2. `ulid()` (`src/bus.ts:27-37`) uses random 80-bit suffixes (`Math.random()`), not a gap-free per-conversation integer sequence (`seq = 1..N`), so `unread_count = last_seq - last_read_seq` cannot be computed in O(1).
  3. `authenticateBusRequest` (`src/hub.ts:1320-1326`) collapses every human session into `{ kind: 'human', actor: 'admin' }`, and `src/bus.ts:272, 350, 560` grants `'admin'` blanket read/ack/claim overrides, whereas `src/hub.ts:465-468` uses `'human:' + session.sub`.
  4. `resolveAgent()` (`src/bus.ts:190-203`) resolves a bare `tag` only when `rows.length === 1` across all projects, while `agents_m4` (`src/hub.ts:279`) uses `tag TEXT PRIMARY KEY`, creating cross-project same-tag collision risks.
- **Resolution in `e854a8d`, `cf91b0d` & `096bdd9` (`PLAN.md` L15–17, L46–78)**:
  - **RESOLVED in Plan** (enforced at code review by **Gate IG1**): `PLAN.md` specifies dedicated `conversations`, `conversation_members`, and `conversation_messages` with atomic per-conversation `seq`, optional `bridge_ref`, zero dual-write into `messages`, verified `human:<sub>` and `agent` identity, refusal of `host`/`job`/`routing-client`/`role:root`, no blanket `'admin'` membership, idempotency per `(conversation_id, actor, key)` with `409` on payload conflict, and cross-project same-tag isolation tests.

---

### B2. Silent Scope Shrinkage: Unfinished Product & Competition Features Omitted or Held

- **Source in `c90cdf8` & `e854a8d`**:
  - The operator brief (§1–2) requires surveying all done and planned work across `agent-hub` and earlier competition repos and planning *"how to integrate everything not done yet into the hub as a conversation platform, in small shippable milestones with acceptance checks."*
  - `c90cdf8` omitted claims-in-launch, generic role failover/consumer fencing, `writer-run`/`head-recovery`/`principal-wake` + host timer migration, oversight/ask-ledger obligations, active request-to-outcome delivery tracking, launcher account-label plans, and `/api/metrics` accounting producers from milestones.
  - `e854a8d` (`PLAN.md` L220–242) added a table mapping those six areas to **"Hold"** dispositions outside `M1`–`M5`. Calling unfinished product requirements "Held" does not satisfy the brief.
- **Resolution in `cf91b0d` & `096bdd9` (`PLAN.md` L31–41, L228–265; `STATUS.md` L410–416, L433–464)**:
  - **RESOLVED in Plan**: `cf91b0d` and `096bdd9` include the **Remaining integration milestones (`M2b`, `M6`, `M7`, `M8a`, `M8b`, `M9`, `M10`, `M11`)** with concrete shippable deliverables, test requirements, and dependencies, and `096bdd9` additionally updates `STATUS.md` §10 (`L414`) so it states those items *"remain open in executable M2b/M6–M11"*:
    - **M2b**: Full `dakit` adoption across `fleet`, sign-in, and device-pairing views.
    - **M6**: Ownership claims (`/api/bus/claims`) enforced in the launch admission transaction before editable task placement/launch.
    - **M7**: Generic epoch-fenced role leases (`coordination/role_failover.py` reference) with transactional effect authorization + epoch check.
    - **M8a**: Launcher account/profile/provider/model/effort attribution (`agent-quota-launcher` + `src/fleet.ts` admission).
    - **M8b**: `writer-run`, `principal-wake`, and `head-recovery` job profiles in host dispatcher and checks with fenced role custody and two controlled cycles + interruption test before closing issue 102.
    - **M9**: Dashboard accounting producers connected to bounded Hub `/api/metrics` ingestion and `dakit` views (24 hourly UTC buckets, zero fabrication of token/money counts from quota percentages).
    - **M10**: Conversation-visible request-to-outcome lifecycle (`tasks_guard.py` + `ask-ledger.py` concepts: canonical task reference, owner acceptance, first-action evidence, due obligation, pinned independent review, accepted outcome, and human delivery).
    - **M11**: Physical host adoption and one-by-one timer/service cutover only after replacement proof, operations handoff, rollback, and independent restore check.

---

### B3. Native Bridge Identity, Provenance, and Loop-Safety Gap in M3

- **Source in `c90cdf8` (`PLAN.md` L108–129) & Residual Prose in `cf91b0d` (`PLAN.md` L122–150)**:
  - In `host/agent_hub_host/bridge.py:554-738` and `native_bridge.py:11-21, 220-277`, `aplexer message send` invoked from an unbound external process without a valid native session identity emits `from: {"external": true}`, causing Rust `aplexer` (`message_routing.rs:reply_target`) to reject `a message reply`.
  - Furthermore, under M1 (`PLAN.md` L65–67; `docs/CONVERSATIONS.md` §1.1), `POST /api/conversations/:id/messages` rejects `kind = 'host'` tokens (`403 invalid_principal_kind`) and JSON sender overrides (`400 sender_override_forbidden`). Thus a single host token cannot post replies on behalf of multiple local agent tags without per-participant `kind = 'agent'` credentials.
- **Resolution in `cf91b0d` & `096bdd9` (`PLAN.md` L37, L285; `STATUS.md` L441–464) & Refined Gate IG3**:
  - **RESOLVED in Plan** (enforced at code review by **Refined Gate IG3**): `cf91b0d` and `096bdd9` split `M3a` (Agent CLI, `task-0390`) from `M3b` (genuine native inbox participation, `task-0392`), and `096bdd9:docs/platform/STATUS.md` (`L456–464`) makes the supported self-bound native client model explicit.
  - **Factual Clarification on `1df0ac3` Gate IG3**: While `1df0ac3` originally hardcoded a separate `hub-bridge` `NativeServiceBinding`, the current supported `M3b` design uses each participant's existing `kind = 'agent'` token together with its genuine current native session UUID/tag/workspace (`a whoami --json`), performing self-send/reply plus explicit loop/ack filtering — empirically verified by the earlier Argon CLI reviewer in its own bound session with the real installed `a` binary and no external sender. Refined **Gate IG3** (§6) qualifies positive native binding/provenance (forbidding borrowed identity, `--from`, or `APLEXER_*` overrides) rather than requiring a specific service name/helper; a separate `NativeServiceBinding` is needed only if a separate non-member service actually originates native sends. Full `M3b` code still requires independent review (`17424c6` in `task-0392` is under Grok review and not accepted yet).

---

### B4. Unsafe / Contradictory M5 Check & Wake Semantics

- **Source in `c90cdf8` & Residual Prose in `cf91b0d` (`PLAN.md` L20, L174–181; `STATUS.md` L326)**:
  - Earlier drafts stated *"Reuse scheduled checks (`src/checks.ts`) for `inbox_backlog` on a conversation actor... Wake: only `hub bridge` + existing aplexer `message deliver` at a verified idle empty prompt"*, while `STATUS.md` L326 stated *"Hub policy: never type into terminals."*
  - In actual `src/checks.ts:144-167`, `inbox_backlog` runs `SELECT COUNT(*) AS n FROM messages WHERE to_actor = ? AND acked_at IS NULL` and `action.type === 'message'` writes to the 1:1 `messages` table (`src/hub.ts:1207`); it does not inspect `conversation_members.last_read_seq` or `conversation_messages`. And `aplexer message deliver` (`bridge.py:787`) injects framed bytes + Enter into the target PTY.
- **Resolution in `096bdd9` (`PLAN.md` L191–196; `STATUS.md` L456–457) & Refined Gate IG4**:
  - **RESOLVED in `096bdd9` Plan & Refined Gate IG4**: `096bdd9:docs/platform/PLAN.md` (`L191–196`) directly repairs the M5 prose so notification defaults strictly to a durable native inbox (`--queue`, zero PTY or composer writes), requires extending `src/checks.ts` to query conversation read watermarks (`conversation_members.last_read_seq < conversations.last_seq`), states that any future opt-in terminal wake needs its own separately reviewed stable-idle/empty-draft and single-attempt uncertainty guards (no implied requirement to type into terminals during M5), and keeps fenced `principal-wake` in `M8b`.

---

### B5. Erroneous Independent Review Gate Rule in `c90cdf8`

- **Source in `c90cdf8` (`PLAN.md` L205)**:
  - Stated *"6. Independent reviewer SHA ≠ implementer SHA/model"*, contradicting `scripts/guards/review_gate.py:26-37` (`sha.startswith(r[1]) and ra != ag and rm != mod`).
- **Resolution in `e854a8d`, `cf91b0d` & `096bdd9` (`PLAN.md` L86–87, L225–226, L282–284)**:
  - **RESOLVED**: States *"Independent review of the **same candidate SHA** by a distinct identity and model. Do not require a different commit"* (`L86–87`), *"6. Independent reviewer inspects the same candidate SHA with a distinct identity and model"* (`L225–226`), and in `096bdd9` (`L282–284`) clarifies that new candidate/release commits carry `Agent: <actor>/<verified model>` while retaining already-reviewed source SHAs and recording provenance instead of rewriting history.

---

### B6. Worktree, Agent Branches, and Milestone Status Tracking

- **Source in `c90cdf8` (`STATUS.md` L189–194, L333, L389–390)**:
  - Claimed `agent-hub-wt-platform-{api,cli,ui}` were clean at `213fcf6` and that Hub was not using Agent Branches.
- **Resolution in `cf91b0d` & `096bdd9` (`PLAN.md` L26–29, L261; `STATUS.md` L152–158, L400–402, L433–464)**:
  - **RESOLVED**: Records Agent Branches tasks `task-0389` (API), `task-0390` (CLI candidate `0a06f5e`, Argon code review accepted against frozen API draft with 45 focused tests and 1 real-HTTP fixture environment error still needing a dependency-enabled rerun before integration), `task-0391` (UI), and `task-0392` (`M3b` native participation candidate `17424c6`, Grok review started, not accepted yet), plus M6 claims worker startup after `routing` scope/admission ACK.

---

## 4. Major Findings (`F7`–`F8`) & Resolution Status in `cf91b0d` & `096bdd9`

### F7. M2 / M2b `dakit` UI Contract, Scale/Border/Color Enforcement & Component-Need Rules

- **Finding & Clarification Against `~/git/dakit/docs/adoption.md`**:
  - `dakit/docs/shell.md` and `docs/list-detail.md` (`103912d6`) require: (a) selected conversation ID in the URL (`?conversation=<id>`) with `pushState`/`popstate`, `aria-current="true"` on the active `.dk-split__item`, and `data-view="list"|"detail"` switching with `.dk-split__back` at `<= 820px`; (b) zero page scrollbar beside `.dk-split__scroll`, no KPI stat strips, no visible `0` unread badge or danger-red unread counter, no `border-left` accent stripes (`--dk-accent-soft` fill only), and `X-CSRF-Token` on all browser POSTs; and (c) no direct edits or source forks of `~/git/dakit` by Hub UI workers.
  - Per `~/git/dakit/docs/adoption.md` (`L124–191`), official `dakit` enforcement runs `sync.mjs --check`, `check-colors.mjs` (forbidding raw color literals `#hex`/`rgb()`/`hsl()`/`oklch()`, requiring semantic `--dk-*` color roles), `check-borders.mjs` (forbidding non-neutral border/outline colors, colored inset shadows, and single-side borders `> 1px`, while allowing neutral `1px` dividers and `:focus-visible` `--dk-focus-ring`), and `check-scale.mjs` (requiring `padding`/`margin`/`gap`/`inset` `px` values on the 4px grid, `--dk-text-*` steps instead of raw `px` `font-size`, and no negative `margin`). Legitimate 4px-grid layout values, `@media (max-width: 820px)` breakpoints, and neutral `1px` borders are valid in `dakit`.
- **Resolution in `cf91b0d` & `096bdd9` (`PLAN.md` L95–120, L238) & Refined Gate IG2**: `M2` and `M2b` adopt `dakit` with kit lock and semantic color/border/scale checks and *"No dakit source fork"*. Refined **Gate IG2** (§6) enforces official `dakit` components, semantic roles, type/space scales, and checker acceptance rather than an invented zero-all-`px` rule.

### F8. Physical Acceptance vs `hub.dtcdev.click` DNS & Host Token Dependencies

- **Finding**: Prior routing status and `platform`'s current probe confirmed `hub.dtcdev.click` does not resolve and health is unavailable, and Hetzner's host config lacked an access token.
- **Resolution in `e854a8d`, `cf91b0d` & `096bdd9` (`PLAN.md` L209–211, L245, L260; `STATUS.md` L394–398)**: Explicitly attributes the current DNS/health failure to `platform`'s probe, separates historical 15-Oct bus results from current runtime state, and schedules `M11` to verify supported host adoption and migration only after code/review/restore preparation and explicit operations authorization.

---

## 5. Acceptance Matrix Against Operator Brief (`2026-10-17`)

| # | Operator Brief Requirement | `c90cdf8` | `e854a8d` | `cf91b0d` | `096bdd9` (Final) | Verification Notes on `096bdd9` |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | Survey all work done and planned across `agent-hub` and earlier competition repos | PARTIAL | PARTIAL | **PASS** | **PASS** | Covers all 11 repos, reports, worktree states, Agent Branches tasks, and review checkpoints (`STATUS.md` §1–§11 + Checkpoints). |
| 2 | Plan how to integrate everything not done yet into Hub as a conversation platform in small shippable milestones with acceptance checks | FAIL | FAIL | **PASS** | **PASS** | `M1`–`M5` + `M2b` + `M6`–`M11` (`PLAN.md` L31–41, L228–265; `STATUS.md` L414) cover every reusable unfinished capability with concrete tests and dependencies. |
| 3 | Conversations (1:1 and group) with humans and agents, durable history, ordering, read/delivery state, and native `aplexer` session bridge | FAIL | PARTIAL | **PASS** (Gate IG1, IG3) | **PASS** (Gate IG1, IG3) | Dedicated `conversations`, `conversation_members`, `conversation_messages` (`seq`), `M3a` CLI + `M3b` self-bound native inbox participation. |
| 4 | Task, review, and outcome flow connected to conversations so requests started in a conversation are tracked to completion | FAIL | FAIL | **PASS** (`M4` + `M10`) | **PASS** (`M4` + `M10`) | `M4` links routing/fleet/review/outcome records; `M10` tracks canonical task, owner acceptance, first-action evidence, due obligation, pinned review, and human delivery. |
| 5 | Safe notification and wake behavior for agents with unread conversation messages | FAIL | PARTIAL | **PASS** (Gate IG4) | **PASS** (Gate IG4) | `PLAN.md` L191–196 explicitly sets durable native inbox-only default (zero PTY/composer writes) and conversation read-watermark checks; screen auto-Enter dropped. |
| 6 | Clean retirement of old sidecars/bridges only **after** hub replacements are verified | PARTIAL | PARTIAL | **PASS** (`M8b`, `M9`, `M11`) | **PASS** (`M8b`, `M9`, `M11`) | Old timers and compatibility collectors remain active until replacement proof, acknowledged operations handoff, rollback, and independent restore check (`M11`). |
| 7 | Reuse routing's existing machine registry and model tiers; do not invent a second machine registry | PASS | PASS | **PASS** | **PASS** | Reuses `src/routing.ts`, `src/fleet.ts`, and `~/git/agent-hub/config/model-routing.json` (`213fcf6`) tiers: `deep` (`astra`, `argon`, `opus`), `daily` (`sol`, `sonnet`, `glm-flash`, `muse`, `deepseek-flash`, `grok`; default tier), and `quick` (`haiku`, `luna`), with `disabled_providers: ["claude"]`, `explicit_only_providers: ["codex"]`, and `preferred_providers: ["zai", "go"]`. |
| 8 | All UI work must use `~/git/dakit`; file missing component needs to `dakit` | PARTIAL | PARTIAL | **PASS** (`M2` + `M2b`, Gate IG2) | **PASS** (`M2` + `M2b`, Gate IG2) | Covers both new conversations UI (`M2`) and existing fleet/sign-in/device views (`M2b`) with official `dakit` components/scales/checkers and zero `dakit` source fork. |
| 9 | Use isolated git worktrees per task; verify with tests and real end-to-end checks before pushing to `main`; use `[skip ci]` on intermediate commits | FAIL | PASS | **PASS** (Gate IG5) | **PASS** (Gate IG5) | Same-SHA distinct-model review rule (`PLAN.md` L86–87, L225–226) and trailer/provenance preservation rule (`PLAN.md` L282–284) explicitly documented. |
| 10 | Maintain a clear status document with a running progress log, reviewed findings, and what remains | PARTIAL | PARTIAL | **PASS** (Gate IG5) | **PASS** | `STATUS.md` §10 (`L414`) and `Platform integration checkpoint` + `Independent review checkpoint` (`L433–464`) are fully synchronized. |

---

## 6. Binding Implementation Gates (`IG1`–`IG5`) for Milestone Code Reviews

Approval of the plan at `cf91b0da45ac9fec1d87b4886bbaa2c5add5df55` and `096bdd9dabcfe2449cac8479657530e5c159f7bf` does **not** approve any code worktree. Every milestone implementation commit must pass independent code review against these five binding gates (refined at `096bdd9` per §1.3 `(a)`–`(e)`):

1. **Gate IG1 (`M1` Conversation API — `task-0389`)**:
   - Must use dedicated `conversations` (`last_seq`), `conversation_members` (`last_read_seq`), and `conversation_messages` (`seq = 1..N` allocated inside `this.sql.transactionSync`, `UNIQUE(conversation_id, sender_actor, idempotency_key)`, optional `bridge_ref`), leaving `/api/bus/*` and `messages` untouched.
   - Must authenticate human sessions strictly as `human:<sub_id>` (rejecting collapsed `'admin'` or empty `sub`), reject `kind = 'host'` tokens (`403`), enforce `X-CSRF-Token` on cookie-authenticated mutations, and pass cross-project same-tag (`projA:tag` vs `projB:tag`) isolation tests.
2. **Gate IG2 (`M2` & `M2b` `dakit` UI — `task-0391`)**:
   - Must consume actual `dakit` components (`.dk-split` with `?conversation=<id>` URL state via `pushState`/`popstate`, `aria-current="true"` on the active item, `data-view="list"|"detail"` switching with `.dk-split__back` at `<= 820px`, `.dk-split__scroll` without a second page scrollbar), enforce `X-CSRF-Token` on POSTs, and make zero direct edits/forks of `~/git/dakit` (filing missing shared components as `dakit` needs).
   - Must follow `~/git/dakit/docs/adoption.md` (`L124–191`) semantic roles, type scale (`--dk-text-*`), and spacing scale (`--dk-space-*` / 4px grid) and pass `dakit`'s official checkers: `sync.mjs --check`, `check-colors.mjs` (zero raw color literals), `check-borders.mjs` (neutral border roles only; neutral `1px` dividers and `:focus-visible` `--dk-focus-ring` permitted; zero accent/colored borders or `>1px` single-side stripes), and `check-scale.mjs` (4px-grid `padding`/`margin`/`gap`/`inset`, `--dk-text-*` font sizes, zero negative `margin`), rather than an invented zero-all-`px` rule that would reject valid 4px-grid layout, `@media (max-width: 820px)` breakpoints, or `1px` neutral borders.
3. **Gate IG3 (`M3a` CLI `task-0390` & `M3b` Native Participation `task-0392`)**:
   - Qualify positive native binding and provenance rather than hardcoding a specific service name or helper: in the supported self-bound native client design, each participant uses its own existing `kind = 'agent'` token and its genuine current native session UUID/tag/workspace (`a whoami --json`), performing native self-send/reply with explicit loop/ack filtering (as empirically verified in an own-session send/reply test with the real installed `a` binary and no external sender).
   - Must never use borrowed identity, `--from`, or `APLEXER_*` workspace/session overrides, and must never use an unattested host token to impersonate agent actors. A separate `NativeServiceBinding` is required only if a separate non-member service process actually originates native `a message send` calls.
   - Multi-member local fan-out and reply scanning must skip self-originated/mirrored messages (`sender_actor === local_member.actor` and hub-forwarded `[conv:<id> seq:<seq>]` copies), filter acked/processed native envelope IDs, and advance `/read` only after local durable receipt succeeds. Full `M3b` code still requires independent review; candidate `17424c6` in `task-0392` is under Grok review and is not accepted yet.
4. **Gate IG4 (`M5` Safe Pings & `M8b`/`M10` Obligation Checks)**:
   - As codified in `096bdd9:docs/platform/PLAN.md` (`L191–196`), `M5` notification defaults strictly to a durable native inbox (`aplexer message send --queue` / native inbox copy, zero PTY or composer writes), and `src/checks.ts` must be extended (with `hub-zai` ACK) to query conversation read watermarks (`conversation_members.last_read_seq < conversations.last_seq`) with cooldown deduplication.
   - There is no implied requirement to type into terminals during `M5`. Any optional future PTY wake (`aplexer message deliver`) requires separately reviewed stable-idle/empty-draft guards (such as 3 consecutive `_check_idle_and_empty_composer` checks verifying `state == "idle"` and `composer_is_empty`) plus durable single-attempt uncertainty holds (`delivers[native_id]`), while fenced `principal-wake` belongs to `M8b`.
5. **Gate IG5 (Git Hygiene, Commit Trailers & Provenance Preservation)**:
   - As codified in `096bdd9:docs/platform/PLAN.md` (`L282–284`), new candidate and release commits carry an `Agent: <actor>/<verified-model>` trailer and `[skip ci]`, while already-reviewed source commit SHAs are retained without rewriting their history and with explicit source-tree and pinned-review provenance recorded in status/review records.
   - The earlier `STATUS.md` §10 stale-hold wording noted in `1df0ac3` is resolved in `096bdd9:docs/platform/STATUS.md` (`L414`).

---

## 7. Explicit Remaining Unknowns

In accordance with reviewer verification rules (`_docs/team/06-reviewer.md`), the following runtime and external states were **not** directly probed during this read-only documentation review and remain explicit unknowns until verified in execution milestones:

1. **Live Cloudflare Worker Durable Object SQLite Schema & Deployment State**: Live Worker endpoints and Durable Object SQLite state (Hub uses DO SQLite only, no D1) were not queried from this review session; `platform` independently confirmed `hub.dtcdev.click` is currently unresolved.
2. **Hetzner & Win35 Host Token / Systemd Timer Live State**: Private host-local credential configuration and live user systemd timers (`fleet-host.timer`, `headless-root.timer`, `principal-ping.timer`) were intentionally not read or modified; any detailed runtime evidence remains retained privately under git-ignored `.local/`.
3. **Candidate Code Acceptance Across Implementation Worktrees**: This report reviews only `docs/platform/PLAN.md` and `docs/platform/STATUS.md` through `096bdd9dabcfe2449cac8479657530e5c159f7bf`. Code acceptance remains separate: CLI candidate `0a06f5e` (`task-0390`, accepted by a separate Argon code review against the frozen API draft with 45 focused tests) still requires a dependency-enabled full host rerun and M1 API integration; native bridge candidate `17424c6` (`task-0392`) is under independent Grok review and not yet accepted; and `task-0389` (M1 API), `task-0391` (M2 UI), and M6 claims worktrees each require their own dedicated independent code review on their exact candidate commit SHAs.

---

## 8. Machine-Parseable Review Verdicts

Review: changes-requested sha=c90cdf8090424c92c26a879c88674784f28782e8 reviewer=platform-plan-review/argon
Review: changes-requested sha=e854a8d242022d8b999e866accf3ba2a421ba0fa reviewer=platform-plan-review/argon
Review: approved sha=cf91b0da45ac9fec1d87b4886bbaa2c5add5df55 reviewer=platform-plan-review/argon
Review: approved sha=096bdd9dabcfe2449cac8479657530e5c159f7bf reviewer=platform-plan-review-final/argon
