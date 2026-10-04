"""Authenticated SSH transport for native aplexer mailboxes.

This is not a rival broker. It runs the current aplexer CLI on an
allowlisted host using existing SSH aliases. Baseline root mailbox
wrappers (orchestrator-channel.py) are a different, weaker path and
must not be treated as native cross-host acceptance.

Windows currently has no local aplexer. Bidirectional delivery uses
Windows-initiated SSH: the desktop client invokes aplexer on the
Hetzner host and polls a namespaced outbox. The SSH bridge identity
is distinct from the originating agent identity.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from typing import Any, Protocol

from .catalog import Catalog, resolve_catalog
from .cursors import CursorStore, payload_digest
from .device_registry import Device, DeviceRegistry
from .envelope import (
    NamespacedId,
    SendReceipt,
    TransportState,
    new_idempotency_key,
    new_message_id,
)
from .errors import GuardRejected, NativeBindingMissing, TransportUnavailable
from .guards import DeliveryMode, inspect_delivery_guard


class Transport(Protocol):
    def run(self, device: Device, argv: list[str], timeout: int = 30) -> str: ...


class SshTransport:
    """Existing authenticated SSH only. No new keys, no secret copy."""

    def run(self, device: Device, argv: list[str], timeout: int = 30) -> str:
        if not device.ssh_alias:
            raise TransportUnavailable(f"no_ssh_alias:{device.id}")
        cmd = [
            "ssh",
            "-o",
            "BatchMode=yes",
            "-o",
            "StrictHostKeyChecking=yes",
            "-o",
            "IdentitiesOnly=yes",
            device.ssh_alias,
            "--",
            *argv,
        ]
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise TransportUnavailable(type(exc).__name__) from exc
        if proc.returncode != 0:
            raise TransportUnavailable(f"ssh_exit:{proc.returncode}")
        return proc.stdout


@dataclass
class SendRequest:
    sender: NamespacedId
    recipient: NamespacedId
    body: str
    data: dict[str, Any] | None
    idempotency_key: str | None
    correlation_token: str
    delivery: DeliveryMode = DeliveryMode.INBOX
    originating_agent: NamespacedId | None = None
    bridge_device_id: str | None = None


class SshRelay:
    def __init__(
        self,
        registry: DeviceRegistry,
        transport: Transport,
        store: CursorStore,
        *,
        local_device_id: str,
    ):
        self.registry = registry
        self.transport = transport
        self.store = store
        self.local_device_id = local_device_id

    def _runner(self, device: Device, argv: list[str]) -> str:
        return self.transport.run(device, argv)

    def catalog(self, device_id: str, workspace: str | None = None) -> Catalog:
        device = self.registry.get(device_id)
        return resolve_catalog(device, self._runner, workspace)

    def send(self, request: SendRequest) -> SendReceipt:
        target = self.registry.get(request.recipient.device_id)
        origin = request.originating_agent or request.sender
        bridge = request.bridge_device_id or self.local_device_id
        key = request.idempotency_key or new_idempotency_key()
        digest = payload_digest(request.body, request.data)
        existing = self.store.lookup_send(
            key,
            sender=request.sender.render(),
            recipient=request.recipient.render(),
            digest=digest,
        )
        if existing:
            return SendReceipt(
                message_id=existing,
                idempotency_key=key,
                sender=request.sender,
                recipient=request.recipient,
                delivery="inbox",
                recorded_at="",
                catalog_resolved_session_id=request.recipient.session_id,
                catalog_observed_at="",
                bridge_device_id=bridge,
                originating_agent=origin,
                state=TransportState.SEND_RECEIPT,
                payload_sha256=digest,
            )

        if not target.can_run_aplexer():
            # SSH-client hosts (Windows) have no native aplexer. Queue on an
            # aplexer host for the client to poll. This is recorded, not a
            # native Windows-bound send.
            message_id = new_message_id()
            self.store.queue_offline(
                {
                    "idempotency_key": key,
                    "message_id": message_id,
                    "sender": request.sender.render(),
                    "recipient": request.recipient.render(),
                    "body": request.body,
                    "data": request.data,
                    "correlation_token": request.correlation_token,
                    "bridge_device_id": bridge,
                    "originating_agent": origin.render(),
                    "queued_for_client_poll": True,
                }
            )
            self.store.remember_send(
                key,
                sender=request.sender.render(),
                recipient=request.recipient.render(),
                digest=digest,
                message_id=message_id,
            )
            return SendReceipt(
                message_id=message_id,
                idempotency_key=key,
                sender=request.sender,
                recipient=request.recipient,
                delivery="queued_client_poll",
                recorded_at="",
                catalog_resolved_session_id=None,
                catalog_observed_at="",
                bridge_device_id=bridge,
                originating_agent=origin,
                payload_sha256=digest,
            )

        catalog = self.catalog(target.id, request.recipient.workspace)
        entry = catalog.resolve_tag(request.recipient.workspace, request.recipient.agent_tag)
        inspect_delivery_guard(entry, request.delivery)

        argv = [
            target.aplexer_bin or "aplexer",
            "message",
            "send",
            "--workspace",
            request.recipient.workspace,
            "--to",
            request.recipient.agent_tag,
            "--json",
            request.body,
        ]
        if request.data is not None:
            argv.extend(["--data", json.dumps(request.data, separators=(",", ":"))])
        raw = self.transport.run(target, argv)
        payload = json.loads(raw) if raw.strip() else {}
        message_id = payload.get("id") or new_message_id()
        self.store.remember_send(
            key,
            sender=request.sender.render(),
            recipient=request.recipient.render(),
            digest=digest,
            message_id=message_id,
        )
        self.store.mark_sent(key, message_id)
        return SendReceipt(
            message_id=message_id,
            idempotency_key=key,
            sender=request.sender,
            recipient=request.recipient,
            delivery=payload.get("delivery", "inbox"),
            recorded_at=str(payload.get("created_at", "")),
            catalog_resolved_session_id=entry.session_id,
            catalog_observed_at=catalog.observed_at,
            bridge_device_id=bridge,
            originating_agent=origin,
            payload_sha256=digest,
        )

    def retry_offline(self) -> list[SendReceipt]:
        receipts = []
        for row in self.store.pending_outbox():
            if row.get("queued_for_client_poll"):
                continue
            sender_parts = row["sender"].split("/")
            recipient_parts = row["recipient"].split("/")
            req = SendRequest(
                sender=NamespacedId(*_pad(sender_parts)),
                recipient=NamespacedId(*_pad(recipient_parts)),
                body=row["body"],
                data=row.get("data"),
                idempotency_key=row["idempotency_key"],
                correlation_token=row.get("correlation_token") or "",
            )
            try:
                receipts.append(self.send(req))
            except (TransportUnavailable, GuardRejected, NativeBindingMissing):
                continue
        return receipts


def _pad(parts: list[str]) -> tuple[str, str, str, str, str | None]:
    while len(parts) < 5:
        parts.append("-")
    device, workspace, tag, session, task = parts[:5]
    return device, workspace, tag, task, None if session == "-" else session
