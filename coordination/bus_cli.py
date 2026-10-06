#!/usr/bin/env python3
"""Headless bus CLI. No aplexer executable, PID, or env required.

Supports explicit host/device addressing, registry validation, and JSON output.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from coordination.bus import FileBus
from coordination.device_registry import DeviceRegistry
from coordination.envelope import NamespacedId
from coordination.errors import CoordinationError, UnknownDevice
from coordination.worker_bus import SessionlessWorkerBus


def _bus(args: argparse.Namespace) -> FileBus:
    return FileBus(args.store)


def _load_registry(args: argparse.Namespace) -> DeviceRegistry | None:
    reg_path = getattr(args, "registry", None)
    if reg_path:
        p = Path(reg_path)
        if not p.exists():
            raise FileNotFoundError(f"Registry file not found: {reg_path}")
        return DeviceRegistry.load(p)
    env_path = os.environ.get("AGENT_DEVICE_REGISTRY")
    if env_path and Path(env_path).exists():
        return DeviceRegistry.load(env_path)
    default_p = ROOT / "examples" / "devices.example.json"
    if default_p.exists():
        return DeviceRegistry.load(default_p)
    return None


def cmd_register(args: argparse.Namespace) -> int:
    device = getattr(args, "device", None) or getattr(args, "target_device", None)
    if not device:
        print("Error: --device or --target-device is required", file=sys.stderr)
        return 2

    if getattr(args, "registry", None):
        reg = _load_registry(args)
        if reg:
            reg.get(device)

    ident, token = _bus(args).register(
        agent_name=args.agent,
        device_id=device,
        project_id=args.project,
        task_id=args.task,
    )
    out = ident.public()
    out["token"] = token
    Path(args.cred).write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps({
        "identity_id": ident.identity_id,
        "agent_name": ident.agent_name,
        "device_id": ident.device_id,
        "cred": args.cred,
    }))
    return 0


def _cred(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def cmd_send(args: argparse.Namespace) -> int:
    cred = _cred(args.cred)
    target_device = getattr(args, "target_device", None) or getattr(args, "device", None)

    reg = _load_registry(args)
    if target_device:
        if reg is not None:
            reg.get(target_device)
        else:
            raise UnknownDevice(target_device)

    data = json.loads(args.data) if args.data else {}
    sender_device = cred.get("device_id")

    if target_device:
        data.setdefault("target_device", target_device)
        data.setdefault("bridge_device_id", sender_device or target_device)
        dest_namespaced = NamespacedId(
            device_id=target_device,
            workspace=cred.get("project_id", "agent-coordination"),
            agent_tag=args.to,
            task_id=cred.get("task_id") or "default",
            session_id=None,  # MUST STAY NONE: No invented synthetic session
        )
        data.setdefault("destination", dest_namespaced.render())
        data.setdefault("destination_namespaced", dest_namespaced.to_dict())

    if sender_device:
        orig_namespaced = NamespacedId(
            device_id=sender_device,
            workspace=cred.get("project_id", "agent-coordination"),
            agent_tag=cred.get("agent_name", "sender"),
            task_id=cred.get("task_id") or "default",
            session_id=None,
        )
        data.setdefault("originating_agent", orig_namespaced.to_dict())

    bus = _bus(args)
    identities = bus._read(bus._identities, {})
    recipient_id = args.to

    if recipient_id in identities:
        recip_ident = identities[recipient_id]
        if target_device and recip_ident.get("device_id") and recip_ident.get("device_id") != target_device:
            raise CoordinationError(
                f"Target device mismatch: recipient {recipient_id} is enrolled on {recip_ident.get('device_id')}, expected {target_device}"
            )
    else:
        matching = [
            i_id for i_id, ident in identities.items()
            if ident.get("agent_name") == args.to and (not target_device or ident.get("device_id") == target_device)
        ]
        if len(matching) == 1:
            recipient_id = matching[0]

    msg = bus.send(
        sender_id=cred["identity_id"],
        token=cred["token"],
        recipient_id=recipient_id,
        body=args.body,
        data=data if data else None,
        idempotency_key=args.idempotency_key,
    )
    print(json.dumps(msg.to_public(), indent=2))
    return 0


def cmd_inbox(args: argparse.Namespace) -> int:
    cred = _cred(args.cred)
    target_device = getattr(args, "target_device", None) or getattr(args, "device", None)
    if target_device:
        reg = _load_registry(args)
        if reg is not None:
            reg.get(target_device)
        else:
            raise UnknownDevice(target_device)
    bus = _bus(args)
    items = bus.inbox(cred["identity_id"], cred["token"], unread_only=not args.all)
    if target_device:
        identities = bus._read(bus._identities, {})
        filtered = []
        for m in items:
            s_ident = identities.get(m.sender_id, {})
            r_ident = identities.get(m.recipient_id, {})
            m_data = m.data or {}
            dest_ns = m_data.get("destination_namespaced")
            if (
                s_ident.get("device_id") == target_device
                or r_ident.get("device_id") == target_device
                or m_data.get("target_device") == target_device
                or (isinstance(dest_ns, dict) and dest_ns.get("device_id") == target_device)
            ):
                filtered.append(m)
        items = filtered
    print(json.dumps([m.to_public() for m in items], indent=2))
    return 0


def cmd_wait(args: argparse.Namespace) -> int:
    cred = _cred(args.cred)
    target_device = getattr(args, "target_device", None) or getattr(args, "device", None)
    if target_device:
        reg = _load_registry(args)
        if reg is not None:
            reg.get(target_device)
        else:
            raise UnknownDevice(target_device)
    bus = _bus(args)
    items = bus.wait(cred["identity_id"], cred["token"], timeout=args.timeout)
    if target_device:
        identities = bus._read(bus._identities, {})
        filtered = []
        for m in items:
            s_ident = identities.get(m.sender_id, {})
            r_ident = identities.get(m.recipient_id, {})
            m_data = m.data or {}
            dest_ns = m_data.get("destination_namespaced")
            if (
                s_ident.get("device_id") == target_device
                or r_ident.get("device_id") == target_device
                or m_data.get("target_device") == target_device
                or (isinstance(dest_ns, dict) and dest_ns.get("device_id") == target_device)
            ):
                filtered.append(m)
        items = filtered
    print(json.dumps([m.to_public() for m in items], indent=2))
    return 0 if items else 2


def cmd_ack(args: argparse.Namespace) -> int:
    cred = _cred(args.cred)
    msg = _bus(args).ack(cred["identity_id"], cred["token"], args.message_id)
    print(json.dumps(msg.to_public(), indent=2))
    return 0


def cmd_reply(args: argparse.Namespace) -> int:
    cred = _cred(args.cred)
    msg = _bus(args).reply(
        sender_id=cred["identity_id"],
        token=cred["token"],
        message_id=args.message_id,
        body=args.body,
        idempotency_key=args.idempotency_key,
    )
    print(json.dumps(msg.to_public(), indent=2))
    return 0


def cmd_worker_register(args: argparse.Namespace) -> int:
    device = getattr(args, "device", None) or getattr(args, "target_device", None)
    if not device:
        print("Error: --device or --target-device is required", file=sys.stderr)
        return 2

    if getattr(args, "registry", None):
        reg = _load_registry(args)
        if reg:
            reg.get(device)

    worker = SessionlessWorkerBus.register(
        store=args.store,
        agent_name=args.agent,
        device_id=device,
        project_id=args.project,
        task_id=args.task,
        workspace=args.workspace,
    )
    worker.save_credentials(args.cred)
    print(json.dumps({
        "identity_id": worker.identity_id,
        "agent_name": worker.agent_name,
        "cred": args.cred,
        "namespaced_id": worker.namespaced_id.to_dict()
    }))
    return 0


def _worker(args: argparse.Namespace) -> SessionlessWorkerBus:
    return SessionlessWorkerBus.from_credentials(args.store, args.cred)


def cmd_worker_send(args: argparse.Namespace) -> int:
    worker = _worker(args)
    target_device = getattr(args, "target_device", None) or getattr(args, "device", None)
    if target_device:
        reg = _load_registry(args)
        if reg is not None:
            reg.get(target_device)
        else:
            raise UnknownDevice(target_device)

    data = json.loads(args.data) if args.data else {}
    if target_device:
        data.setdefault("target_device", target_device)
        data.setdefault("bridge_device_id", worker.device_id)
        dest_namespaced = NamespacedId(
            device_id=target_device,
            workspace=worker.workspace,
            agent_tag=args.to,
            task_id=worker.task_id or "default",
            session_id=None,
        )
        data.setdefault("destination", dest_namespaced.render())
        data.setdefault("destination_namespaced", dest_namespaced.to_dict())

    recipient_id = args.to
    identities = worker.bus._read(worker.bus._identities, {})
    if recipient_id in identities:
        recip_ident = identities[recipient_id]
        if target_device and recip_ident.get("device_id") and recip_ident.get("device_id") != target_device:
            raise CoordinationError(
                f"Target device mismatch: recipient {recipient_id} is on {recip_ident.get('device_id')}, expected {target_device}"
            )
    else:
        matching = [
            i_id for i_id, ident in identities.items()
            if ident.get("agent_name") == args.to and (not target_device or ident.get("device_id") == target_device)
        ]
        if len(matching) == 1:
            recipient_id = matching[0]

    outcome = worker.send(
        recipient_id=recipient_id,
        body=args.body,
        data=data if data else None,
        idempotency_key=args.idempotency_key,
    )
    print(json.dumps(outcome.to_dict(), indent=2))
    return 0


def cmd_worker_receive(args: argparse.Namespace) -> int:
    worker = _worker(args)
    target_device = getattr(args, "target_device", None) or getattr(args, "device", None)
    if target_device:
        reg = _load_registry(args)
        if reg is not None:
            reg.get(target_device)
        else:
            raise UnknownDevice(target_device)

    msgs = worker.receive(limit=args.limit, timeout=args.timeout, unread_only=not args.all)
    if target_device:
        identities = worker.bus._read(worker.bus._identities, {})
        filtered = []
        for m in msgs:
            s_ident = identities.get(m.sender_id, {})
            r_ident = identities.get(m.recipient_id, {})
            m_data = m.data or {}
            dest_ns = m_data.get("destination_namespaced")
            if (
                s_ident.get("device_id") == target_device
                or r_ident.get("device_id") == target_device
                or m_data.get("target_device") == target_device
                or (isinstance(dest_ns, dict) and dest_ns.get("device_id") == target_device)
            ):
                filtered.append(m)
        msgs = filtered
    print(json.dumps([m.to_public() for m in msgs], indent=2))
    return 0


def cmd_worker_ack(args: argparse.Namespace) -> int:
    worker = _worker(args)
    ack = worker.ack(args.message_id)
    print(json.dumps(ack.to_dict(), indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Agent Bus CLI (no aplexer dependency)")
    parser.add_argument("--store", required=True)
    parser.add_argument("--registry", default=None, help="Path to device registry JSON file")
    parser.add_argument("--json", action="store_true", default=False, help="Emit JSON output")

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--registry", default=argparse.SUPPRESS, help="Path to device registry JSON file")
    common.add_argument("--json", action="store_true", default=argparse.SUPPRESS, help="Emit JSON output")

    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("register", parents=[common])
    p.add_argument("--agent", required=True)
    p.add_argument("--device")
    p.add_argument("--target-device")
    p.add_argument("--project", default="agent-coordination")
    p.add_argument("--task")
    p.add_argument("--cred", required=True)
    p.set_defaults(func=cmd_register)

    p = sub.add_parser("send", parents=[common])
    p.add_argument("--cred", required=True)
    p.add_argument("--to", required=True)
    p.add_argument("--body", required=True)
    p.add_argument("--device")
    p.add_argument("--target-device")
    p.add_argument("--data")
    p.add_argument("--idempotency-key")
    p.set_defaults(func=cmd_send)

    p = sub.add_parser("inbox", parents=[common])
    p.add_argument("--cred", required=True)
    p.add_argument("--device")
    p.add_argument("--target-device")
    p.add_argument("--all", action="store_true")
    p.set_defaults(func=cmd_inbox)

    p = sub.add_parser("wait", parents=[common])
    p.add_argument("--cred", required=True)
    p.add_argument("--device")
    p.add_argument("--target-device")
    p.add_argument("--timeout", type=float, default=5.0)
    p.set_defaults(func=cmd_wait)

    p = sub.add_parser("ack", parents=[common])
    p.add_argument("--cred", required=True)
    p.add_argument("--message-id", required=True)
    p.set_defaults(func=cmd_ack)

    p = sub.add_parser("reply", parents=[common])
    p.add_argument("--cred", required=True)
    p.add_argument("--message-id", required=True)
    p.add_argument("--body", required=True)
    p.add_argument("--idempotency-key")
    p.set_defaults(func=cmd_reply)

    p = sub.add_parser("worker-register", parents=[common])
    p.add_argument("--agent", required=True)
    p.add_argument("--device")
    p.add_argument("--target-device")
    p.add_argument("--project", default="agent-coordination")
    p.add_argument("--task")
    p.add_argument("--workspace")
    p.add_argument("--cred", required=True)
    p.set_defaults(func=cmd_worker_register)

    p = sub.add_parser("worker-send", parents=[common])
    p.add_argument("--cred", required=True)
    p.add_argument("--to", required=True)
    p.add_argument("--body", required=True)
    p.add_argument("--device")
    p.add_argument("--target-device")
    p.add_argument("--data")
    p.add_argument("--idempotency-key")
    p.set_defaults(func=cmd_worker_send)

    p = sub.add_parser("worker-receive", parents=[common])
    p.add_argument("--cred", required=True)
    p.add_argument("--device")
    p.add_argument("--target-device")
    p.add_argument("--all", action="store_true")
    p.add_argument("--limit", type=int)
    p.add_argument("--timeout", type=float)
    p.set_defaults(func=cmd_worker_receive)

    p = sub.add_parser("worker-ack", parents=[common])
    p.add_argument("--cred", required=True)
    p.add_argument("--message-id", required=True)
    p.set_defaults(func=cmd_worker_ack)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except UnknownDevice as exc:
        if getattr(args, "json", False):
            print(json.dumps({"error": "UnknownDevice", "code": exc.code, "message": str(exc), "device_id": exc.device_id}))
        else:
            print(f"Error: {exc}", file=sys.stderr)
        return 1
    except CoordinationError as exc:
        if getattr(args, "json", False):
            print(json.dumps({"error": type(exc).__name__, "code": getattr(exc, "code", "coordination_error"), "message": str(exc)}))
        else:
            print(f"Error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        if getattr(args, "json", False):
            print(json.dumps({"error": type(exc).__name__, "message": str(exc)}))
        else:
            print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
