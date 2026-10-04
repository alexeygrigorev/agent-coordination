# Coordination side of the host-admission contract

Peer document: `/home/alexey/git/agent-quota-launcher/docs/host-admission-contract.md`
(owner: quota-launcher design; native head `quota-launcher-head` /
`6be4c247-4410-4bdb-968e-7fc2d5844941`). This file does not edit that repo.

## Split

| Concern | Owner |
| --- | --- |
| Device enrollment, SSH alias allowlist, native catalog at send time, durable message IDs, send receipt / read ACK / semantic outcome | `agent-coordination` |
| Quota windows, resource floors, adapter/model admission, launch reservation | `agent-quota-launcher` |
| Dashboard events `project_id=agent-coordination` | `agent-dashboard` (consume only; no duplicate collectors) |

Transport success is not quota eligibility. A launcher decision is not a
send receipt. Remote dispatch in the launcher remains
`unsupported_remote_dispatch` until they implement and test it.

## Fields this project supplies to a launcher request

- `device_id` from the coordination registry (opaque, not a raw hostname)
- `catalog_version` / `catalog_observed_at` from `aplexer list --json` on the target
- `native_session_id` resolved at send time
- `idempotency_key` and durable `message_id`
- `bridge_device_id` vs `originating_agent` (Windows has no native aplexer)

## Error classes this transport reports

`unknown_device`, `unregistered_alias`, `transport_unavailable`,
`catalog_stale`, `native_binding_missing`, `guard_rejected`,
`idempotency_conflict`.

Quota/resource classes stay with the launcher. This project will not
write launcher files without an ACK from `quota-launcher-head`.
