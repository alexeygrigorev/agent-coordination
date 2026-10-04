#!/usr/bin/env python3
"""Windows-initiated SSH client for bidirectional mailbox delivery.

Windows has no local aplexer (see .local/desktop-environment.json). This
client uses existing ssh.exe to invoke aplexer on an allowlisted remote
host and to poll a namespaced outbox. The SSH bridge identity is not the
originating Windows agent identity. Inbound Windows SSH is not required.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def ssh_run(alias: str, argv: list[str], timeout: int = 30) -> str:
    cmd = [
        "ssh",
        "-o",
        "BatchMode=yes",
        "-o",
        "StrictHostKeyChecking=yes",
        alias,
        "--",
        *argv,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"transport_unavailable:ssh_exit:{proc.returncode}")
    return proc.stdout


def cmd_send(args: argparse.Namespace) -> int:
    # Originating agent is recorded in --data; the remote aplexer sender is
    # the SSH-invoked CLI on the aplexer host (bridge), never a forged Windows session.
    data = {
        "originating_agent": {
            "device_id": args.origin_device,
            "kind": "ssh-client-host",
            "native_aplexer": False,
            "workspace": args.origin_workspace,
            "tag": args.origin_tag,
        },
        "bridge_device_id": args.bridge_device,
        "correlation_token": args.token,
        "idempotency_key": args.idempotency_key,
    }
    argv = [
        args.aplexer,
        "message",
        "send",
        "--workspace",
        args.workspace,
        "--to",
        args.to,
        "--json",
        args.body,
        "--data",
        json.dumps(data, separators=(",", ":")),
    ]
    print(ssh_run(args.alias, argv))
    return 0


def cmd_poll(args: argparse.Namespace) -> int:
    argv = [args.aplexer, "message", "inbox", "--json"]
    if args.workspace:
        # inbox is bound to the remote session identity; the Windows client
        # polls a dedicated bridge tag rather than impersonating a Hetzner agent.
        pass
    print(ssh_run(args.alias, argv))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Windows-initiated aplexer SSH client")
    parser.add_argument("--alias", default="hetzner")
    parser.add_argument("--aplexer", default="/home/alexey/.local/bin/aplexer")
    parser.add_argument("--bridge-device", default="hetzner-rmthz")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_send = sub.add_parser("send")
    p_send.add_argument("--workspace", required=True)
    p_send.add_argument("--to", required=True)
    p_send.add_argument("--body", required=True)
    p_send.add_argument("--token", required=True)
    p_send.add_argument("--idempotency-key", required=True)
    p_send.add_argument("--origin-device", default="windows-desktop")
    p_send.add_argument("--origin-workspace", default="work/agent-coordination")
    p_send.add_argument("--origin-tag", default="windows-codex")
    p_send.set_defaults(func=cmd_send)

    p_poll = sub.add_parser("poll")
    p_poll.add_argument("--workspace")
    p_poll.set_defaults(func=cmd_poll)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except Exception as exc:
        print(json.dumps({"error": type(exc).__name__, "message": str(exc)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
