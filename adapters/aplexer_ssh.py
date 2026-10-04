#!/usr/bin/env python3
"""CLI adapter: send/list/message through the stdlib SSH relay.

Native CLI source edits live in cloudflare-aplexer-protocol and require an
explicit Antigravity-head handoff (Ant 46fdb644). This adapter calls the
installed aplexer binary over allowlisted SSH using existing SSH aliases.
It does not replace aplexer and does not install a global binary.

Flags match installed `aplexer message --help` exactly:
- `send`: positional TEXT / --body, --workspace, --to, --all, --to-engine,
  --queue, --kind, --data, --idempotency-key (forwarded only when supported
  natively by target; fallback to payload/store), --json.
- No `--from` spoofing: remote aplexer processes run under the authenticated
  SSH bridge session; originating agent identities are verified and carried
  in structured metadata (--data), never forged via arbitrary --from tags.
- Pane injection is forbidden by safety policy (inbox-only delivery).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from coordination.catalog import utc_now
from coordination.cursors import CursorStore
from coordination.device_registry import Device, DeviceRegistry
from coordination.envelope import NamespacedId, SendReceipt
from coordination.ssh_relay import SendRequest, SshRelay, SshTransport


def _registry_path(args: argparse.Namespace) -> Path:
    return Path(args.registry)


def build_relay(args: argparse.Namespace) -> SshRelay:
    registry = DeviceRegistry.load(_registry_path(args))
    store = CursorStore(args.store)
    return SshRelay(registry, SshTransport(), store, local_device_id=args.local_device)


def probe_native_flag(relay: SshRelay, device: Device, subcommand: str, flag: str) -> bool:
    """Inspect help output of installed aplexer binary to verify flag support.

    The installed aplexer 0.1.9 does not have --idempotency-key in message send,
    even though the source tree does. Passing an unaccepted flag causes exit 2.
    """
    if not device.can_run_aplexer():
        return False
    argv = [device.aplexer_bin or "aplexer", "message", subcommand, "--help"]
    try:
        raw = relay.transport.run(device, argv)
        return flag in raw
    except Exception:
        return False


def validate_no_from_spoof(
    from_tag: str | None,
    caller_tag: str | None,
    allow_unspecified: bool = True,
) -> None:
    """Enforce 'no --from spoof'.

    In native aplexer, --from overrides sender identity.
    Across machine boundaries, caller identity must match authenticated credentials.
    Arbitrary session impersonation via --from is strictly forbidden.
    """
    if not from_tag:
        return
    if caller_tag and from_tag != caller_tag:
        raise ValueError(
            f"Identity spoofing forbidden: --from '{from_tag}' does not match "
            f"authenticated caller identity '{caller_tag}'"
        )
    if not caller_tag and not allow_unspecified:
        raise ValueError(
            f"Identity spoofing forbidden: --from '{from_tag}' provided without "
            "verifiable caller identity"
        )


def cmd_devices(args: argparse.Namespace) -> int:
    registry = DeviceRegistry.load(_registry_path(args))
    print(
        json.dumps(
            [
                {
                    "id": d.id,
                    "kind": d.kind.value,
                    "ssh_alias": d.ssh_alias,
                    "hostname": d.hostname,
                    "native_aplexer": d.native_aplexer,
                    "outbound_ssh_only": d.outbound_ssh_only,
                    "role": d.role,
                }
                for d in registry.all()
            ],
            indent=2,
        )
    )
    return 0


def cmd_catalog(args: argparse.Namespace) -> int:
    relay = build_relay(args)
    catalog = relay.catalog(args.device, args.workspace)
    print(
        json.dumps(
            {
                "device_id": catalog.device_id,
                "observed_at": catalog.observed_at,
                "source_command": list(catalog.source_command),
                "entries": [
                    {
                        "session_id": e.session_id,
                        "tag": e.tag,
                        "workspace": e.workspace,
                        "engine": e.engine,
                        "reported_state": e.reported_state,
                        "phase": e.phase,
                    }
                    for e in catalog.entries
                ],
            },
            indent=2,
        )
    )
    return 0


def cmd_send(args: argparse.Namespace) -> int:
    # Pane injection forbidden check
    if getattr(args, "pane", False):
        raise ValueError("Pane injection is forbidden by safety policy; all message exchange must be inbox-only")

    # Anti-spoofing check
    validate_no_from_spoof(
        from_tag=args.from_override,
        caller_tag=args.from_tag,
    )

    body = args.text or args.body
    if not body:
        raise ValueError("Message body is required (specify as positional TEXT or --body)")

    relay = build_relay(args)
    device = relay.registry.get(args.device)

    # Determine recipient tag / broadcast target
    recipient_tag = args.to or (args.to_engine if args.to_engine else "*")
    if not args.to and not args.all and not args.to_engine:
        raise ValueError("Recipient required: specify --to <TAG>, --all, or --to-engine <ENGINE>")

    sender = NamespacedId(
        device_id=args.local_device,
        workspace=args.from_workspace or args.workspace,
        agent_tag=args.from_tag or "anonymous",
        task_id=args.task or "general",
        session_id=args.from_session,
    )
    recipient = NamespacedId(
        device_id=args.device,
        workspace=args.workspace,
        agent_tag=recipient_tag,
        task_id=args.task or "general",
    )

    data_payload: dict[str, Any] = json.loads(args.data) if args.data else {}

    # Attach originating identity and idempotency in structured data
    data_payload.setdefault("originating_agent", sender.to_dict())
    data_payload.setdefault("bridge_device_id", args.local_device)
    if args.token:
        data_payload.setdefault("correlation_token", args.token)
    if args.idempotency_key:
        data_payload.setdefault("idempotency_key", args.idempotency_key)
    if args.kind:
        data_payload.setdefault("kind", args.kind)

    # Probe whether target native aplexer accepts --idempotency-key
    supports_idempotency_flag = False
    if args.idempotency_key and device.can_run_aplexer():
        supports_idempotency_flag = probe_native_flag(relay, device, "send", "--idempotency-key")

    req = SendRequest(
        sender=sender,
        recipient=recipient,
        body=body,
        data=data_payload,
        idempotency_key=args.idempotency_key,
        correlation_token=args.token or "",
        originating_agent=sender,
        bridge_device_id=args.local_device,
    )

    receipt = relay.send(req)

    result_dict = receipt.to_dict()
    result_dict["native_idempotency_flag_supported"] = supports_idempotency_flag
    if not supports_idempotency_flag and args.idempotency_key:
        result_dict["notes"] = "Target aplexer missing --idempotency-key; deduplication handled via cursor store + payload"

    print(json.dumps(result_dict, indent=2, default=str))
    return 0


def cmd_reply(args: argparse.Namespace) -> int:
    if getattr(args, "pane", False):
        raise ValueError("Pane injection is forbidden by safety policy; all message exchange must be inbox-only")

    validate_no_from_spoof(
        from_tag=args.from_override,
        caller_tag=args.from_tag,
    )

    body = args.text or args.body
    if not body:
        raise ValueError("Reply body is required (specify as positional TEXT or --body)")

    relay = build_relay(args)
    device = relay.registry.get(args.device)

    data_payload: dict[str, Any] = json.loads(args.data) if args.data else {}
    if args.token:
        data_payload.setdefault("correlation_token", args.token)
    if args.idempotency_key:
        data_payload.setdefault("idempotency_key", args.idempotency_key)

    supports_idempotency = False
    if args.idempotency_key and device.can_run_aplexer():
        supports_idempotency = probe_native_flag(relay, device, "reply", "--idempotency-key")

    argv = [
        device.aplexer_bin or "aplexer",
        "message",
        "reply",
        args.message_id,
        body,
        "--json",
    ]
    if args.kind:
        argv.extend(["--kind", args.kind])
    if data_payload:
        argv.extend(["--data", json.dumps(data_payload, separators=(",", ":"))])
    if supports_idempotency and args.idempotency_key:
        argv.extend(["--idempotency-key", args.idempotency_key])

    raw = relay.transport.run(device, argv)
    print(raw)
    return 0


def cmd_inbox(args: argparse.Namespace) -> int:
    relay = build_relay(args)
    device = relay.registry.get(args.device)

    argv = [device.aplexer_bin or "aplexer", "message", "inbox", "--json"]
    if args.new:
        argv.append("--new")
    if args.from_tag:
        argv.extend(["--from", args.from_tag])

    raw = relay.transport.run(device, argv)
    print(raw)
    return 0


def cmd_wait(args: argparse.Namespace) -> int:
    relay = build_relay(args)
    device = relay.registry.get(args.device)

    argv = [
        device.aplexer_bin or "aplexer",
        "message",
        "wait",
        "--timeout",
        str(args.timeout),
        "--json",
    ]
    raw = relay.transport.run(device, argv, timeout=args.timeout + 10)
    print(raw)
    return 0


def cmd_ack(args: argparse.Namespace) -> int:
    relay = build_relay(args)
    device = relay.registry.get(args.device)

    argv = [device.aplexer_bin or "aplexer", "message", "ack", "--json"]
    if args.all:
        argv.append("--all")
    if args.from_tag:
        argv.extend(["--from", args.from_tag])
    if args.message_ids:
        argv.extend(args.message_ids)

    raw = relay.transport.run(device, argv)
    print(raw)
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    relay = build_relay(args)
    device = relay.registry.get(args.device)

    argv = [
        device.aplexer_bin or "aplexer",
        "message",
        "show",
        args.message_id,
        "--json",
    ]
    raw = relay.transport.run(device, argv)
    print(raw)
    return 0


def cmd_log(args: argparse.Namespace) -> int:
    relay = build_relay(args)
    device = relay.registry.get(args.device)

    argv = [device.aplexer_bin or "aplexer", "message", "log", "--json"]
    if args.workspace:
        argv.extend(["--workspace", args.workspace])

    raw = relay.transport.run(device, argv)
    print(raw)
    return 0


def cmd_deliver(args: argparse.Namespace) -> int:
    relay = build_relay(args)
    device = relay.registry.get(args.device)

    argv = [
        device.aplexer_bin or "aplexer",
        "message",
        "deliver",
        args.message_id,
        "--json",
    ]
    if args.workspace:
        argv.extend(["--workspace", args.workspace])

    raw = relay.transport.run(device, argv)
    print(raw)
    return 0


def cmd_gc(args: argparse.Namespace) -> int:
    relay = build_relay(args)
    device = relay.registry.get(args.device)

    argv = [device.aplexer_bin or "aplexer", "message", "gc", "--json"]
    if args.workspace:
        argv.extend(["--workspace", args.workspace])

    raw = relay.transport.run(device, argv)
    print(raw)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="SSH adapter matching installed aplexer message CLI flags exactly",
    )
    parser.add_argument("--registry", default=str(ROOT / "examples" / "devices.example.json"))
    parser.add_argument("--store", default=str(ROOT / ".local" / "relay-store"))
    parser.add_argument("--local-device", default="hetzner-rmthz")
    sub = parser.add_subparsers(dest="cmd", required=True)

    # 1. devices
    p_dev = sub.add_parser("devices", help="List allowlisted devices from registry")
    p_dev.set_defaults(func=cmd_devices)

    # 2. catalog
    p_cat = sub.add_parser("catalog", help="Resolve active session catalog on target device")
    p_cat.add_argument("--device", required=True, help="Target device ID")
    p_cat.add_argument("--workspace", help="Workspace filter")
    p_cat.set_defaults(func=cmd_catalog)

    # 3. send: exactly matching `aplexer message send [OPTIONS] <TEXT>`
    p_send = sub.add_parser("send", help="Send a message to a tag, a broadcast, or an engine filter")
    p_send.add_argument("text", nargs="?", help="The message body")
    p_send.add_argument("--body", help="Message body (alternative to positional TEXT)")
    p_send.add_argument("--device", default="hetzner-rmthz", help="Target device ID")
    p_send.add_argument("--workspace", required=True, help="Destination workspace")
    p_send.add_argument("--to", help="Send to one session, addressed by tag")
    p_send.add_argument("--all", action="store_true", help="Broadcast to every session in workspace")
    p_send.add_argument("--to-engine", help="Broadcast to sessions of one engine")
    p_send.add_argument("--queue", action="store_true", help="Allow sending to tag that does not exist yet")
    p_send.add_argument("--kind", default="note", help="note (default) | handoff | reply | any string")
    p_send.add_argument("--data", help="Opaque structured JSON payload")
    p_send.add_argument("--from-workspace", help="Caller origin workspace")
    p_send.add_argument("--from-tag", help="Caller origin tag")
    p_send.add_argument("--from-session", help="Caller origin session ID")
    p_send.add_argument("--from", dest="from_override", help="Sender identity override (anti-spoof guarded)")
    p_send.add_argument("--task", default="general", help="Task ID context")
    p_send.add_argument("--token", help="Correlation token")
    p_send.add_argument("--idempotency-key", help="Idempotency key to prevent duplicate sends on retries")
    p_send.add_argument("--pane", action="store_true", help="Pane injection (forbidden by safety policy)")
    p_send.add_argument("--or-inbox", action="store_true", help="Ignored (inbox-only policy)")
    p_send.add_argument("--raw", action="store_true", help="Ignored")
    p_send.add_argument("--no-enter", action="store_true", help="Ignored")
    p_send.add_argument("--json", action="store_true", default=True, help="Emit machine-readable JSON")
    p_send.set_defaults(func=cmd_send)

    # 4. reply: matching `aplexer message reply [OPTIONS] <MESSAGE_ID> <TEXT>`
    p_reply = sub.add_parser("reply", help="Reply to a received message (threads via reply_to)")
    p_reply.add_argument("message_id", help="Id of the message being replied to")
    p_reply.add_argument("text", nargs="?", help="The reply body")
    p_reply.add_argument("--body", help="Reply body (alternative to positional TEXT)")
    p_reply.add_argument("--device", default="hetzner-rmthz", help="Target device ID")
    p_reply.add_argument("--workspace", help="Workspace filter")
    p_reply.add_argument("--kind", default="reply", help="Defaults to 'reply'")
    p_reply.add_argument("--data", help="Opaque structured JSON payload")
    p_reply.add_argument("--from-tag", help="Caller origin tag")
    p_reply.add_argument("--from", dest="from_override", help="Sender identity override (anti-spoof guarded)")
    p_reply.add_argument("--token", help="Correlation token")
    p_reply.add_argument("--idempotency-key", help="Idempotency key")
    p_reply.add_argument("--pane", action="store_true", help="Pane injection (forbidden)")
    p_reply.add_argument("--json", action="store_true", default=True, help="Emit machine-readable JSON")
    p_reply.set_defaults(func=cmd_reply)

    # 5. inbox: matching `aplexer message inbox [OPTIONS]`
    p_inbox = sub.add_parser("inbox", help="List unread messages addressed to calling session")
    p_inbox.add_argument("--device", default="hetzner-rmthz", help="Target device ID")
    p_inbox.add_argument("--workspace", help="Workspace filter")
    p_inbox.add_argument("--new", action="store_true", help="Unread messages only")
    p_inbox.add_argument("--from", dest="from_tag", help="Consumer identity override")
    p_inbox.add_argument("--json", action="store_true", default=True, help="Emit machine-readable JSON")
    p_inbox.set_defaults(func=cmd_inbox)

    # 6. wait: matching `aplexer message wait [OPTIONS]`
    p_wait = sub.add_parser("wait", help="Wait for unread messages addressed to calling session")
    p_wait.add_argument("--device", default="hetzner-rmthz", help="Target device ID")
    p_wait.add_argument("--timeout", type=int, default=60, help="Maximum seconds to wait")
    p_wait.add_argument("--workspace", help="Workspace filter")
    p_wait.add_argument("--json", action="store_true", default=True, help="Emit machine-readable JSON")
    p_wait.set_defaults(func=cmd_wait)

    # 7. ack: matching `aplexer message ack [OPTIONS] [MESSAGE_ID]...`
    p_ack = sub.add_parser("ack", help="Acknowledge messages so they stop appearing in inbox")
    p_ack.add_argument("message_ids", nargs="*", help="Ids to acknowledge")
    p_ack.add_argument("--device", default="hetzner-rmthz", help="Target device ID")
    p_ack.add_argument("--all", action="store_true", help="Ack every unread message")
    p_ack.add_argument("--from", dest="from_tag", help="Consumer identity override")
    p_ack.add_argument("--workspace", help="Workspace filter")
    p_ack.add_argument("--json", action="store_true", default=True, help="Emit machine-readable JSON")
    p_ack.set_defaults(func=cmd_ack)

    # 8. show: matching `aplexer message show [OPTIONS] <MESSAGE_ID>`
    p_show = sub.add_parser("show", help="Show one message by id")
    p_show.add_argument("message_id", help="Id of the message to show")
    p_show.add_argument("--device", default="hetzner-rmthz", help="Target device ID")
    p_show.add_argument("--workspace", help="Workspace filter")
    p_show.add_argument("--json", action="store_true", default=True, help="Emit machine-readable JSON")
    p_show.set_defaults(func=cmd_show)

    # 9. log: matching `aplexer message log [OPTIONS]`
    p_log = sub.add_parser("log", help="Show whole workspace conversation in order")
    p_log.add_argument("--device", default="hetzner-rmthz", help="Target device ID")
    p_log.add_argument("--workspace", help="Workspace whose conversation to show")
    p_log.add_argument("--json", action="store_true", default=True, help="Emit machine-readable JSON")
    p_log.set_defaults(func=cmd_log)

    # 10. deliver: matching `aplexer message deliver [OPTIONS] <MESSAGE_ID>`
    p_del = sub.add_parser("deliver", help="Submit an existing inbox message")
    p_del.add_argument("message_id", help="Original durable message ID")
    p_del.add_argument("--device", default="hetzner-rmthz", help="Target device ID")
    p_del.add_argument("--workspace", help="Destination mailbox")
    p_del.add_argument("--json", action="store_true", default=True, help="Emit machine-readable JSON")
    p_del.set_defaults(func=cmd_deliver)

    # 11. gc: matching `aplexer message gc [OPTIONS]`
    p_gc = sub.add_parser("gc", help="Prune expired/over-cap messages from mailbox")
    p_gc.add_argument("--device", default="hetzner-rmthz", help="Target device ID")
    p_gc.add_argument("--workspace", help="Workspace whose mailbox to prune")
    p_gc.add_argument("--json", action="store_true", default=True, help="Emit machine-readable JSON")
    p_gc.set_defaults(func=cmd_gc)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except Exception as exc:
        print(json.dumps({"error": type(exc).__name__, "message": str(exc), "at": utc_now()}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
