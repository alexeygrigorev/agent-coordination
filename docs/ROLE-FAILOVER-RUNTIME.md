# Role failover runtime adapter

Implemented primitives and a callable adapter are in `coordination/role_failover.py`
and `coordination/failover_bridge.py`. These files do not start a second scheduler
or service. The existing supervisor owner must integrate and independently
accept the runtime path before declaring autonomous failover operational.

## Contract

An explicitly configured project has role slots and optional subprojects.
Candidates are explicit per slot, with real runtime actor, host and generation
observations supplied by the trusted local supervisor adapter. Identity enrolment
is not inferred from a PID, a task label or a restored transcript. `configure`
and `observe` are trusted administration APIs, not remotely authenticated APIs.
An authenticated FileBus sender and enrolled recipient mappings carry actual
control envelopes. Agents never adopt another agent's session credentials.

Each existing supervisor/standby tick (60 seconds) calls `FailoverBridge.tick`.
The sole authoritative role database serializes elections (`BEGIN IMMEDIATE`).
Leases are 180 seconds; observation freshness is 60 seconds. A completed periodic
check receipt advances its deadline by 1800 seconds. The stand-up adapter supplies
an explicit UTC instant calculated from Europe/Berlin (including DST); it must
record completed evidence and the next stand-up instant. Lease renewal is not a
completed check. Scheduled checks have 120 seconds execution grace. Missing lease
or overdue check emits one durable sync-probe event; the diagnostic grace is
120 seconds, after which deterministic eligible candidate order elects one
successor. Sync responses after final expiry are recorded operationally but must
not revive the former epoch or waive an absent check. The `sync_response` API can
clear only a suspicion whose existing deadlines still remain valid; it cannot
restore a naturally expired holder.

Principal promotion atomically revokes the promoted agent's head-role authority
and emits `head_backfill_required`, preserving its task/file children. The
existing principal/launcher consumer must supply a separately owned useful head
startup task, preserve child custody and verify genuine role ACK/first model
action within 300 seconds. Backfill events do not establish a launched head.

The elected owner may enqueue an explicit startup/control task via
`guarded_effect`: SQLite holds election exclusion while the maintained launcher
CLI `submit` commits its durable idempotency key. Replays return the previous
intent. A crash between launcher submit and role commit retries the same key.
The existing launcher still owns fresh provider quotas, capacities, per-process
containment, disk/privacy gates, actual model launch and independent acceptance.
Queued is not running or accepted. No RAM admission refusal is introduced.

Role epochs fence new control-plane submissions; existing productive workers
continue under their original task custody. These epochs do not retroactively
fence arbitrary filesystem writes or raw subprocesses. `authorize()` is a
point-in-time query, not sufficient fencing for a later external mutation.
Consumers must use guarded enqueue or an effect store's atomic epoch comparison,
and reconcile/quiesce ambiguous writer custody before replacement writes.
No old process is killed by this module. Busy/draft/unknown-quota/stale candidates
cannot be newly promoted; a healthy remaining role must own the replacement task
if no eligible candidate exists. Replacement-required is retained, never invented
as a successfully launched principal.

The database is a **single Hetzner authority**: loss/partition fails closed and
cannot elect a separate local leader. It removes a particular agent/laptop role
as a single point of failure, not the host or authority storage itself. Host-loss
failover requires a separately reviewed consensus/replicated authority, not copying
SQLite to another host and independently electing. Host boot changes invalidate
old leases; observed wall-clock rollback fails closed until clock catches up.

## Integration still required

Ant owns existing `scripts/supervision/service.py`; no shared service edit is
included here. Its hook must load this adapter from the reviewed pinned package,
read an owner-approved project/candidate registry, supply current observations,
call ticks even when principal/desktop is absent, authenticate native Bus sender
and recipients, supply useful replacement task payloads, drain head-backfill
requirements, consume genuine role ACK and model-first-action receipts, and update
canonical TASKS/TEAM-REGISTRY. No token is stored in source or report.

Live acceptance requires unresponsive-principal and missing-coordinator periodic
and stand-up scenarios, two simultaneous standby contenders, partition/unknown
quota/draft negatives, preserved in-flight children, one elected epoch and one
launcher reservation, actual replacement model first tool, completed check,
independent peer verdict and repeated no-desktop cycles. Source tests, recorded
sync envelopes and queued startup tasks do not establish live autonomy.

## Validation

`python3 -m pytest -o addopts='' tests/test_role_failover.py tests/test_failover_bridge.py`
Tests exercise concurrent election and enqueue, stale epochs/rejoin, head
promotion, missing checks despite renewals, stand-up takeover, due-time completion,
boot/clock rollback, project isolation, draft/quota/stale negatives, real FileBus
sync envelope replay, and maintained launcher CLI submission boundary.
