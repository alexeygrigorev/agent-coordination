#!/usr/bin/env python3
"""CLI adapter: send/list through the stdlib SSH relay.

Native CLI source edits live in cloudflare-aplexer-protocol and require an
explicit Antigravity-head handoff. This adapter calls the installed aplexer
binary over allowlisted SSH. It does not replace aplexer and does not
install a global binary.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from coordination.catalog import utc_now
from coordination.cursors import CursorStore
from coordination.device_registry import DeviceRegistry
from coordination.envelope import NamespacedId
from coordination.ssh_relay import SendRequest, SshRelay, SshTransport


def _registry_path(args: argparse.Namespace) -> Path:
    return Path(args.registry)


def build_relay(args: argparse.Namespace) -> SshRelay:
    registry = DeviceRegistry.load(_registry_path(args))
    store = CursorStore(args.store)
    return SshRelay(registry, SshTransport(), store, local_device_id=args.local_device)


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
    relay = build_relay(args)
    sender = NamespacedId(
        device_id=args.local_device,
        workspace=args.from_workspace,
        agent_tag=args.from_tag,
        task_id=args.task,
        session_id=args.from_session,
    )
    recipient = NamespacedId(
        device_id=args.device,
        workspace=args.workspace,
        agent_tag=args.to,
        task_id=args.task,
    )
    receipt = relay.send(
        SendRequest(
            sender=sender,
            recipient=recipient,
            body=args.body,
            data=json.loads(args.data) if args.data else None,
            idempotency_key=args.idempotency_key,
            correlation_token=args.token,
            originating_agent=sender,
            bridge_device_id=args.local_device,
        )
    )
    print(json.dumps(receipt.to_dict(), indent=2, default=str))
    return 0


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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="SSH adapter for native aplexer catalogs")
    parser.add_argument("--registry", default=str(ROOT / "examples" / "devices.example.json"))
    parser.add_argument("--store", default=str(ROOT / ".local" / "relay-store"))
    parser.add_argument("--local-device", default="hetzner-rmthz")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_dev = sub.add_parser("devices")
    p_dev.set_defaults(func=cmd_devices)

    p_cat = sub.add_parser("catalog")
    p_cat.add_argument("--device", required=True)
    p_cat.add_argument("--workspace")
    p_cat.set_defaults(func=cmd_catalog)

    p_send = sub.add_parser("send")
    p_send.add_argument("--device", required=True)
    p_send.add_argument("--workspace", required=True)
    p_send.add_argument("--to", required=True)
    p_send.add_argument("--from-workspace", required=True)
    p_send.add_argument("--from-tag", required=True)
    p_send.add_argument("--from-session")
    p_send.add_argument("--task", required=True)
    p_send.add_argument("--token", required=True)
    p_send.add_argument("--body", required=True)
    p_send.add_argument("--data")
    p_send.add_argument("--idempotency-key")
    p_send.set_defaults(func=cmd_send)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except Exception as exc:
        print(json.dumps({"error": type(exc).__name__, "message": str(exc), "at": utc_now()}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
