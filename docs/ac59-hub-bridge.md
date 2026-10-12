# AC59 Hub Bridge

This document details the implementation of the Hub proposed wire contract within the `ac59_service` receiver.
The bridge is designed as a loopback/source-level implementation only, mapping the proposed wire contract endpoints onto the existing `FileBus` core.

## Supported Endpoints

- **POST /api/bus/send**: Accepts messages with `from_actor`, `to_actor`, `kind`, `body`, and `idempotency_key`. Enforces a strict 16384 byte UTF-8 limit on the `body` field.
- **POST /api/bus/reply**: Same as send, but requires the `reply_to` parameter pointing to a valid existing message ID. Enforces original participant rules.
- **GET /api/bus/inbox**: Provides a bounded limit parameter (1 to 100, default 50). Returns `message_rows` representing the inbox for the specified `actor`.
- **GET /api/bus/messages/{id}**: Show endpoint for message details. Access is restricted to the original `sender` or `recipient` only.
- **POST /api/bus/messages/{id}/ack**: Transitions the message state to acknowledged (populates `acked_at`).
- **POST /api/bus/messages/{id}/accept**: Transitions the message state to accepted (populates `accepted_at`).
- **POST /api/bus/messages/{id}/complete**: Transitions the message state to completed (populates `completed_at`).

*Note: Legacy v1 APIs `/v1/send`, `/v1/inbox`, etc. are preserved unchanged.*

## Claim endpoints
- **POST /api/bus/claims** and **POST /api/bus/claims/{id}/release**: These are currently NOT supported and safely return a `501 Not Implemented` with a clear JSON error message to satisfy the contract without faking success.

## Authentication and Binding

Authentication relies on the HTTP `Authorization: Bearer <host credential>` header.
The bearer token is compared in constant-time against the local FileBus token store. 

- Token verification occurs *without* logging the token in paths, query strings, logs, or error bodies. 
- The token authenticates one registered `BusIdentity`; that identity's `device_id` (machine) and `project_id` define the caller's machine scope.
- The caller may act as any identity registered on the same `device_id` and `project_id` (the host's own registered actors), matching the Hub owner's c888 reading.
- Actors registered on another machine or project, or not registered at all, are rejected with HTTP `403 Forbidden`; this applies to sender, inbox actor, show and stage checks.

## Not supported

- `POST /api/bus/claims` and `POST /api/bus/claims/{id}/release` return HTTP `501 Not Implemented`. The host kit's integration flow does not use them; they remain an open gap against the proposed c888 contract.

## Limits and Constraints

- **Message Body Size**: The length of the `body` field inside the JSON payload is strictly limited to `16384` UTF-8 bytes. The HTTP layer rejects chunked transfers and enforces an overall request size cap.
- **Idempotency**: Requests specify an `idempotency_key`. Sending the exact same payload with the same key returns the original message ID. Sending a different payload with a pre-used idempotency key returns a `409 Conflict`.
- **Message IDs**: Newly created messages receive a Crockford base32 ULID instead of a standard UUID, meeting the `new_ids` wire requirement while safely preserving legacy compatibility.

## Rejected uploads and slow clients

- Chunked uploads (400) and bodies over the request cap (413) are read and discarded before the reply, so clients see the status instead of a reset connection. Draining is bounded to 1 MiB and to 3 seconds of total wall time; larger declared bodies are refused without draining.
- Known limitation (pre-existing, not introduced by the bridge): the receiver is a single-threaded `HTTPServer` with a 30-second per-read socket timeout, so a client that trickles an otherwise valid request can still occupy it. It must not be exposed beyond trusted callers until that is addressed.

## Deployment Notes

- This feature is for loopback/source-level testing and bridging.
- No device proofs, real TLS deployments, or external network reachability is provided by this local bridge implementation.
