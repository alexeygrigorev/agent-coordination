# AC59 HTTP Adapter

This document describes the design and configuration of the AC59 HTTP adapter.

## Security Model

The adapter operates over mutually authenticated TLS (mTLS) and binds the HTTP identities directly to the certificate `allowlist`.

1. **Strict mTLS Validation**: All requests except those on insecure loopback (when explicitly enabled with `--insecure-loopback` and `--host 127.0.0.1`) require a client certificate. The certificate fingerprint must be registered in the `--allowlist` JSON file.
2. **Registration Bound to Scope**: Registration (`POST /v1/register`) explicitly requires `device_id` and `project_id`. The adapter verifies that these requested scopes are permitted for the presented client certificate.
3. **Identity Bound to Certificate**: Subsequent actions (`/v1/send`, `/v1/inbox`, `/v1/ack`, `/v1/accept`, `/v1/complete`) accept an `identity_id` and `token`. The adapter extracts the `device_id` and `project_id` for that identity directly from the `FileBus` and ensures the client certificate allows access to those scopes. This prevents compromised tokens from being abused by unauthorized certificates.
4. **Idempotency and Replay Protection**: The adapter delegates all idempotency handling to the durable `FileBus._send_locked` logic. This ensures persistent replay protection across adapter restarts, and returns identical responses for retries without causing conflicts from partial mutations.
5. **Robust Request Parsing**: HTTP payloads are strictly bounded to 10MB to prevent resource exhaustion, and negative content lengths are rejected.
6. **Credential Privacy**: The `/v1/inbox` endpoint supports retrieving credentials (`token` and `identity_id`) from HTTP headers (`X-Bus-Identity`, `X-Bus-Token`, or `Authorization: Bearer <token>`) to avoid leaking credentials in URL access logs, while retaining query-string fallback for backward compatibility.

## API Endpoints

- `POST /v1/register`: Registers a new identity.
- `POST /v1/send`: Sends a message to a recipient. Supports structured data (`data`, `kind`, `reply_to`).
- `POST /v1/inbox` / `GET /v1/inbox`: Retrieves unread messages.
- `POST /v1/ack` / `POST /v1/accept`: Acknowledges or accepts a message.
- `POST /v1/complete`: Completes a message with structured outcome fields (`status`, `artifact`, `digest`, `extra`).

