# Demo Evidence Validator

The `demo_evidence` adapter provides a stdlib-only CLI and API consistency validator for transport-neutral demo manifests. It validates that cross-computer coordination traces meet the consistency requirements for actual Agent Branches product proofs.

## Usage

You can run the validator from the command line:

```bash
python3 -m adapters.demo_evidence path/to/manifest.json [--json]
```

It will output the status:
- `CONSISTENT`: Valid manifest with all milestones complete. Exit code 0.
- `INCOMPLETE`: Valid manifest but missing some completion milestones (e.g. missing `transport_receipt`, `handled_ack`, `ownership_agreement`, or `completed_artifact`). Exit code 0.
- `INVALID`: Validation failed. Exit code 1.

**WARNING**: Because both `CONSISTENT` and `INCOMPLETE` statuses exit with code 0, exit code 0 does **not** imply task completion. Automated callers must explicitly inspect and parse the output text or JSON `status` field to verify completion, and they must independently verify physical proof separation.

For both physical proofs and scripted fixtures, it will additionally report `PHYSICAL_EVIDENCE_MISSING (supplied-but-unverified evidence from JSON manifest)` as a reminder that JSON metadata alone cannot establish physical authenticity.

If `--json` is supplied as the third argument, the output will be printed as a JSON object: `{"status": "...", "details": ["..."]}`.

## API Usage

The public API provides `validate_manifest(manifest: Dict[str, Any]) -> Tuple[str, List[str]]` where the first element is the status string and the second is a list of detailed string flags/errors.
You can also use `compute_sha256_and_size(content: str) -> Tuple[str, int]` for computing the correct hashes.

## Schema Version 2.0 Requirements

The validator checks for:
- Required top-level fields: `version` (1.0 or 2.0), `project`, `task`, `correlation_id`, `presentation_claim`.
- Defined `actors` with `device_id`, strictly positive integer `role_epoch` (> 0), and non-empty string `generation`.
- Valid presentation claims: `"physical_proof"` or `"scripted_fixture"`.
- Consistent `messages` (source, transport_receipt, handled_ack, ownership_agreement, completed_artifact) requiring:
  - Exact payload/artifact SHA256 hashes (strictly 64 hex chars).
  - Explicit non-negative `payload_byte_size` (for source) and `artifact_byte_size` (for completed_artifact). Size can be 0.
  - For supplied `payload` or `body` or `artifact` text content, deterministic UTF-8 size and hash verification against the declared size and hash.
  - Explicit sender strictly positive integer `epoch` (> 0) and non-empty string `generation` on every message matching the sender's current `role_epoch` and `generation`.
  - Source messages require `recipient`, strictly positive integer `recipient_epoch` (> 0) matching recipient's `role_epoch`, and non-empty string `recipient_generation` matching recipient's `generation`.
  - Per-event binding: `project`, `task`, `correlation_id` matching manifest on every message.
  - Correct idempotency payload linkage. Dedup is scoped per sender+recipient+key (same key under same sender+recipient must have the exact same message ID and payload hash). Additionally, a reused sender+key is bound to its original recipient; changing the recipient for a reused key is an INVALID conflict.
  - Valid receipt ACK devices (must match enrolled actor's device).
  - Valid recipient replies.
- All IDs, sender, recipient, task, correlation, device must be non-empty strings. Epochs must be strictly positive true integers, not booleans.
- Rejection of scripted/single-host fixtures presented as physical proofs.

### Complete Schema 2.0 Example

```json
{
  "version": "2.0",
  "project": "proj-1",
  "task": "task-1",
  "correlation_id": "corr-1",
  "presentation_claim": "scripted_fixture",
  "actors": {
    "actor-1": {
      "device_id": "dev-1",
      "role_epoch": 1,
      "generation": "gen-1",
      "is_scripted": true
    },
    "actor-2": {
      "device_id": "dev-2",
      "role_epoch": 2,
      "generation": "gen-2",
      "is_scripted": true
    }
  },
  "messages": [
    {
      "id": "msg-1",
      "type": "source",
      "project": "proj-1",
      "task": "task-1",
      "correlation_id": "corr-1",
      "sender": "actor-1",
      "epoch": 1,
      "generation": "gen-1",
      "recipient": "actor-2",
      "recipient_epoch": 2,
      "recipient_generation": "gen-2",
      "idempotency_key": "idem-1",
      "payload_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
      "payload_byte_size": 0,
      "payload": ""
    },
    {
      "id": "msg-2",
      "type": "transport_receipt",
      "project": "proj-1",
      "task": "task-1",
      "correlation_id": "corr-1",
      "sender": "actor-2",
      "epoch": 2,
      "generation": "gen-2",
      "reply_to": "msg-1",
      "device_ack": "dev-2"
    },
    {
      "id": "msg-3",
      "type": "handled_ack",
      "project": "proj-1",
      "task": "task-1",
      "correlation_id": "corr-1",
      "sender": "actor-2",
      "epoch": 2,
      "generation": "gen-2",
      "reply_to": "msg-1",
      "device_ack": "dev-2"
    },
    {
      "id": "msg-4",
      "type": "ownership_agreement",
      "project": "proj-1",
      "task": "task-1",
      "correlation_id": "corr-1",
      "sender": "actor-2",
      "epoch": 2,
      "generation": "gen-2",
      "reply_to": "msg-1"
    },
    {
      "id": "msg-5",
      "type": "completed_artifact",
      "project": "proj-1",
      "task": "task-1",
      "correlation_id": "corr-1",
      "sender": "actor-2",
      "epoch": 2,
      "generation": "gen-2",
      "reply_to": "msg-1",
      "artifact_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
      "artifact_byte_size": 0,
      "artifact": ""
    }
  ]
}
```
