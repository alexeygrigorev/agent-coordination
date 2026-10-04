#!/usr/bin/env python3
"""Windows-initiated SSH client for bidirectional mailbox delivery.

Windows desktop environment (.local/desktop-environment.json):
- Operating System: Windows
- Local aplexer: NONE (no native binary or daemon on Windows)
- Inbound SSH: NONE (no inbound SSH server, behind NAT/firewall)
- Outbound transport: existing Windows ssh.exe (or ssh) with configured aliases
- Workspace root: work/agent-coordination

Identity Separation:
- `originating_agent`: The actual Windows agent author (device_id="windows-desktop",
  workspace="work/agent-coordination", tag="windows-codex", native_aplexer=False).
  RULE: NEVER invent a native Windows aplexer session ID (session_id is always None).
- `bridge_device_id`: The allowlisted execution host (e.g. "hetzner-rmthz") where
  SSH invokes remote commands. The remote aplexer runs under the SSH user's session.
  RULE: Never pass --from to spoof an existing Hetzner session.

Desktop Gaps Addressed:
1. Typed SSH stdin RPC: Pipes structured JSON-RPC requests over SSH stdin to
   avoid Windows shell quoting, escaping corruption, and argument length limits.
2. Fail-closed missing native receipt: If the remote transport does not return a
   durable message ID, the client fails closed immediately.
3. No forged Windows aplexer origin: session_id is enforced to be None/omitted.
4. Bidirectional delivery: Outbound send + outbound polled inbox + ACK + typed replies.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TextIO


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _new_id() -> str:
    return str(uuid.uuid4())


class WindowsClientError(Exception):
    """Base exception for Windows SSH client errors."""


class TransportUnavailable(WindowsClientError):
    """SSH transport failure or non-zero exit code."""


class ReceiptMissingError(WindowsClientError):
    """Remote host failed to return a valid durable message ID receipt."""


class IdentitySpoofError(WindowsClientError):
    """Attempted to forge or spoof an unauthorized agent session."""


@dataclass
class OriginatingAgent:
    device_id: str = "windows-desktop"
    kind: str = "ssh-client-host"
    native_aplexer: bool = False
    workspace: str = "work/agent-coordination"
    tag: str = "windows-codex"
    session_id: str | None = None  # MUST STAY NONE: No invented Windows aplexer session

    def validate(self) -> None:
        if self.session_id is not None:
            raise IdentitySpoofError(
                f"Invented Windows aplexer session ID forbidden: '{self.session_id}'. "
                "Windows has no local aplexer binary."
            )

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "device_id": self.device_id,
            "kind": self.kind,
            "native_aplexer": self.native_aplexer,
            "workspace": self.workspace,
            "tag": self.tag,
        }


@dataclass
class SendReceipt:
    message_id: str
    idempotency_key: str
    correlation_token: str
    bridge_device_id: str
    originating_agent: dict[str, Any]
    delivery: str = "inbox"
    recorded_at: str = ""
    raw_response: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PollMessage:
    message_id: str
    created_at: int | str
    from_agent: dict[str, Any] | str
    to_tag: str
    body: str
    kind: str = "note"
    data: dict[str, Any] | None = None
    correlation_token: str | None = None
    reply_to: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TypedRpcRequest:
    method: str  # "send" | "poll" | "reply" | "ack" | "status"
    params: dict[str, Any]
    request_id: str = field(default_factory=_new_id)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TypedRpcResponse:
    request_id: str
    success: bool
    result: Any | None = None
    error: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def ssh_run(
    alias: str,
    argv: list[str],
    stdin_data: str | None = None,
    timeout: int = 30,
) -> str:
    """Execute command over existing SSH alias with strict host checking."""
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
    try:
        proc = subprocess.run(
            cmd,
            input=stdin_data,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise TransportUnavailable(f"ssh_error:{type(exc).__name__}:{exc}") from exc

    if proc.returncode != 0:
        err = proc.stderr.strip() or f"exit code {proc.returncode}"
        raise TransportUnavailable(f"ssh_exit:{proc.returncode}:{err}")
    return proc.stdout


def send_message(
    alias: str,
    workspace: str,
    to: str,
    body: str,
    token: str,
    idempotency_key: str,
    origin: OriginatingAgent,
    bridge_device: str = "hetzner-rmthz",
    aplexer_bin: str = "/home/alexey/.local/bin/aplexer",
    use_stdin_rpc: bool = False,
    timeout: int = 30,
) -> SendReceipt:
    """Send a typed message from Windows to a remote aplexer recipient.

    Fails closed if the remote host does not return a durable message ID.
    Enforces separation of originating_agent vs bridge_device_id.
    """
    origin.validate()

    data_payload = {
        "originating_agent": origin.to_dict(),
        "bridge_device_id": bridge_device,
        "correlation_token": token,
        "idempotency_key": idempotency_key,
    }

    if use_stdin_rpc:
        req = TypedRpcRequest(
            method="send",
            params={
                "workspace": workspace,
                "to": to,
                "body": body,
                "token": token,
                "idempotency_key": idempotency_key,
                "originating_agent": origin.to_dict(),
                "bridge_device_id": bridge_device,
                "aplexer_bin": aplexer_bin,
            },
        )
        rpc_resp = execute_stdin_rpc(alias, req, timeout=timeout)
        if not rpc_resp.success:
            err_msg = rpc_resp.error.get("message", "unknown_error") if rpc_resp.error else "failed"
            raise ReceiptMissingError(f"RPC send failed: {err_msg}")
        raw_receipt = rpc_resp.result
    else:
        argv = [
            aplexer_bin,
            "message",
            "send",
            "--workspace",
            workspace,
            "--to",
            to,
            "--json",
            body,
            "--data",
            json.dumps(data_payload, separators=(",", ":")),
        ]
        raw_out = ssh_run(alias, argv, timeout=timeout)
        try:
            raw_receipt = json.loads(raw_out.strip())
        except json.JSONDecodeError as exc:
            raise ReceiptMissingError(
                f"Remote host returned invalid JSON receipt: '{raw_out.strip()}': {exc}"
            ) from exc

    # Fail-closed receipt validation
    message_id = raw_receipt.get("id") or raw_receipt.get("message_id")
    if not message_id:
        raise ReceiptMissingError(
            f"Fail-closed: remote response missing durable message ID. Payload: {raw_receipt}"
        )

    return SendReceipt(
        message_id=str(message_id),
        idempotency_key=idempotency_key,
        correlation_token=token,
        bridge_device_id=bridge_device,
        originating_agent=origin.to_dict(),
        delivery=raw_receipt.get("delivery", "inbox"),
        recorded_at=str(raw_receipt.get("created_at", _utc_now())),
        raw_response=raw_receipt,
    )


def poll_messages(
    alias: str,
    workspace: str | None = None,
    tag: str | None = None,
    aplexer_bin: str = "/home/alexey/.local/bin/aplexer",
    timeout: int = 30,
) -> list[PollMessage]:
    """Poll unread messages from remote mailbox via SSH."""
    argv = [aplexer_bin, "message", "inbox", "--json"]
    if tag:
        argv.extend(["--from", tag])

    raw_out = ssh_run(alias, argv, timeout=timeout)
    if not raw_out.strip():
        return []

    try:
        items = json.loads(raw_out.strip())
    except json.JSONDecodeError as exc:
        raise TransportUnavailable(f"Malformed JSON from remote inbox: {exc}") from exc

    if not isinstance(items, list):
        return []

    results: list[PollMessage] = []
    for item in items:
        data_block = item.get("data")
        parsed_data = None
        corr_token = None
        if isinstance(data_block, str):
            try:
                parsed_data = json.loads(data_block)
            except Exception:
                parsed_data = {"raw": data_block}
        elif isinstance(data_block, dict):
            parsed_data = data_block

        if parsed_data and isinstance(parsed_data, dict):
            corr_token = parsed_data.get("correlation_token")

        msg = PollMessage(
            message_id=item.get("id", ""),
            created_at=item.get("created_at", ""),
            from_agent=item.get("from", {}),
            to_tag=item.get("to", {}).get("tag", "") if isinstance(item.get("to"), dict) else str(item.get("to", "")),
            body=item.get("body", ""),
            kind=item.get("kind", "note"),
            data=parsed_data,
            correlation_token=corr_token,
            reply_to=item.get("reply_to"),
        )
        # Optional workspace filter
        if workspace and item.get("workspace") and item.get("workspace") != workspace:
            continue
        results.append(msg)
    return results


def reply_message(
    alias: str,
    message_id: str,
    body: str,
    token: str,
    idempotency_key: str,
    origin: OriginatingAgent,
    bridge_device: str = "hetzner-rmthz",
    aplexer_bin: str = "/home/alexey/.local/bin/aplexer",
    timeout: int = 30,
) -> SendReceipt:
    """Reply to an existing inbox message ID over SSH."""
    origin.validate()
    data_payload = {
        "originating_agent": origin.to_dict(),
        "bridge_device_id": bridge_device,
        "correlation_token": token,
        "idempotency_key": idempotency_key,
    }
    argv = [
        aplexer_bin,
        "message",
        "reply",
        message_id,
        body,
        "--json",
        "--data",
        json.dumps(data_payload, separators=(",", ":")),
    ]
    raw_out = ssh_run(alias, argv, timeout=timeout)
    try:
        raw_receipt = json.loads(raw_out.strip())
    except json.JSONDecodeError as exc:
        raise ReceiptMissingError(f"Remote reply returned non-JSON: '{raw_out.strip()}': {exc}") from exc

    reply_id = raw_receipt.get("id") or raw_receipt.get("message_id")
    if not reply_id:
        raise ReceiptMissingError(f"Fail-closed: remote reply missing message ID. Payload: {raw_receipt}")

    return SendReceipt(
        message_id=str(reply_id),
        idempotency_key=idempotency_key,
        correlation_token=token,
        bridge_device_id=bridge_device,
        originating_agent=origin.to_dict(),
        delivery=raw_receipt.get("delivery", "inbox"),
        recorded_at=str(raw_receipt.get("created_at", _utc_now())),
        raw_response=raw_receipt,
    )


def ack_messages(
    alias: str,
    message_ids: list[str],
    all_unread: bool = False,
    tag: str | None = None,
    aplexer_bin: str = "/home/alexey/.local/bin/aplexer",
    timeout: int = 30,
) -> dict[str, Any]:
    """Acknowledge one or more message IDs so they stop appearing in unread inbox."""
    argv = [aplexer_bin, "message", "ack", "--json"]
    if all_unread:
        argv.append("--all")
    if tag:
        argv.extend(["--from", tag])
    if message_ids:
        argv.extend(message_ids)

    raw_out = ssh_run(alias, argv, timeout=timeout)
    return {"status": "acked", "raw": raw_out.strip(), "ids": message_ids}


def execute_stdin_rpc(
    alias: str,
    request: TypedRpcRequest,
    python_bin: str = "python3",
    timeout: int = 30,
) -> TypedRpcResponse:
    """Execute typed RPC by streaming JSON-RPC request over SSH stdin."""
    stdin_payload = json.dumps(request.to_dict()) + "\n"
    # Remote server dispatcher
    remote_script = (
        "import json, sys\n"
        "from adapters.windows_client import handle_rpc_line\n"
        "for line in sys.stdin:\n"
        "    if line.strip():\n"
        "        sys.stdout.write(handle_rpc_line(line) + '\\n')\n"
        "        sys.stdout.flush()\n"
    )
    argv = [python_bin, "-c", remote_script]
    raw_out = ssh_run(alias, argv, stdin_data=stdin_payload, timeout=timeout)
    try:
        resp_dict = json.loads(raw_out.strip())
        return TypedRpcResponse(
            request_id=resp_dict.get("request_id", request.request_id),
            success=resp_dict.get("success", False),
            result=resp_dict.get("result"),
            error=resp_dict.get("error"),
        )
    except Exception as exc:
        return TypedRpcResponse(
            request_id=request.request_id,
            success=False,
            error={"code": "malformed_rpc_response", "message": f"{exc}: {raw_out}"},
        )


def handle_rpc_line(line: str) -> str:
    """Process a single JSON-RPC line on the server side."""
    try:
        data = json.loads(line)
        method = data.get("method")
        params = data.get("params", {})
        req_id = data.get("request_id", _new_id())

        if method == "send":
            aplexer_bin = params.get("aplexer_bin", "aplexer")
            data_payload = {
                "originating_agent": params.get("originating_agent"),
                "bridge_device_id": params.get("bridge_device_id"),
                "correlation_token": params.get("token"),
                "idempotency_key": params.get("idempotency_key"),
            }
            argv = [
                aplexer_bin,
                "message",
                "send",
                "--workspace",
                params["workspace"],
                "--to",
                params["to"],
                "--json",
                params["body"],
                "--data",
                json.dumps(data_payload, separators=(",", ":")),
            ]
            proc = subprocess.run(argv, capture_output=True, text=True, check=False)
            if proc.returncode != 0:
                return json.dumps(
                    {
                        "request_id": req_id,
                        "success": False,
                        "error": {"code": "aplexer_exit", "message": proc.stderr.strip()},
                    }
                )
            result = json.loads(proc.stdout.strip())
            return json.dumps({"request_id": req_id, "success": True, "result": result})

        if method == "poll":
            aplexer_bin = params.get("aplexer_bin", "aplexer")
            argv = [aplexer_bin, "message", "inbox", "--json"]
            if params.get("tag"):
                argv.extend(["--from", params["tag"]])
            proc = subprocess.run(argv, capture_output=True, text=True, check=False)
            items = json.loads(proc.stdout.strip()) if proc.stdout.strip() else []
            return json.dumps({"request_id": req_id, "success": True, "result": items})

        return json.dumps(
            {
                "request_id": req_id,
                "success": False,
                "error": {"code": "unknown_method", "message": f"Method '{method}' not implemented"},
            }
        )
    except Exception as exc:
        return json.dumps(
            {
                "request_id": _new_id(),
                "success": False,
                "error": {"code": type(exc).__name__, "message": str(exc)},
            }
        )


def cmd_send(args: argparse.Namespace) -> int:
    origin = OriginatingAgent(
        device_id=args.origin_device,
        workspace=args.origin_workspace,
        tag=args.origin_tag,
    )
    receipt = send_message(
        alias=args.alias,
        workspace=args.workspace,
        to=args.to,
        body=args.body,
        token=args.token,
        idempotency_key=args.idempotency_key,
        origin=origin,
        bridge_device=args.bridge_device,
        aplexer_bin=args.aplexer,
        use_stdin_rpc=args.stdin_rpc,
    )
    print(json.dumps(receipt.to_dict(), indent=2))
    return 0


def cmd_poll(args: argparse.Namespace) -> int:
    messages = poll_messages(
        alias=args.alias,
        workspace=args.workspace,
        tag=args.tag,
        aplexer_bin=args.aplexer,
    )
    print(json.dumps([m.to_dict() for m in messages], indent=2))
    return 0


def cmd_reply(args: argparse.Namespace) -> int:
    origin = OriginatingAgent(
        device_id=args.origin_device,
        workspace=args.origin_workspace,
        tag=args.origin_tag,
    )
    receipt = reply_message(
        alias=args.alias,
        message_id=args.message_id,
        body=args.body,
        token=args.token,
        idempotency_key=args.idempotency_key,
        origin=origin,
        bridge_device=args.bridge_device,
        aplexer_bin=args.aplexer,
    )
    print(json.dumps(receipt.to_dict(), indent=2))
    return 0


def cmd_ack(args: argparse.Namespace) -> int:
    result = ack_messages(
        alias=args.alias,
        message_ids=args.message_ids,
        all_unread=args.all,
        tag=args.tag,
        aplexer_bin=args.aplexer,
    )
    print(json.dumps(result, indent=2))
    return 0


def cmd_rpc(args: argparse.Namespace) -> int:
    params = json.loads(args.params) if args.params else {}
    req = TypedRpcRequest(method=args.method, params=params)
    resp = execute_stdin_rpc(alias=args.alias, request=req)
    print(json.dumps(resp.to_dict(), indent=2))
    return 0 if resp.success else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Windows-initiated authenticated SSH client for typed mailbox delivery"
    )
    parser.add_argument("--alias", default="hetzner", help="SSH alias in ~/.ssh/config")
    parser.add_argument("--aplexer", default="/home/alexey/.local/bin/aplexer", help="Remote aplexer binary path")
    parser.add_argument("--bridge-device", default="hetzner-rmthz", help="Remote execution bridge device ID")

    sub = parser.add_subparsers(dest="cmd", required=True)

    # send
    p_send = sub.add_parser("send", help="Send typed message to remote agent")
    p_send.add_argument("--workspace", required=True, help="Destination workspace on remote host")
    p_send.add_argument("--to", required=True, help="Recipient agent tag")
    p_send.add_argument("--body", required=True, help="Message body text")
    p_send.add_argument("--token", required=True, help="Correlation token")
    p_send.add_argument("--idempotency-key", required=True, help="Unique idempotency key")
    p_send.add_argument("--origin-device", default="windows-desktop", help="Originating device ID")
    p_send.add_argument("--origin-workspace", default="work/agent-coordination", help="Originating workspace")
    p_send.add_argument("--origin-tag", default="windows-codex", help="Originating agent tag")
    p_send.add_argument("--stdin-rpc", action="store_true", help="Use SSH stdin RPC instead of command line args")
    p_send.set_defaults(func=cmd_send)

    # poll
    p_poll = sub.add_parser("poll", help="Poll unread messages addressed to Windows client")
    p_poll.add_argument("--workspace", help="Workspace filter")
    p_poll.add_argument("--tag", default="windows-codex", help="Client tag to query")
    p_poll.set_defaults(func=cmd_poll)

    # reply
    p_reply = sub.add_parser("reply", help="Reply to a received message ID")
    p_reply.add_argument("message_id", help="Message ID being replied to")
    p_reply.add_argument("--body", required=True, help="Reply body text")
    p_reply.add_argument("--token", required=True, help="Correlation token")
    p_reply.add_argument("--idempotency-key", required=True, help="Idempotency key")
    p_reply.add_argument("--origin-device", default="windows-desktop")
    p_reply.add_argument("--origin-workspace", default="work/agent-coordination")
    p_reply.add_argument("--origin-tag", default="windows-codex")
    p_reply.set_defaults(func=cmd_reply)

    # ack
    p_ack = sub.add_parser("ack", help="Acknowledge message IDs")
    p_ack.add_argument("message_ids", nargs="*", help="Message IDs to acknowledge")
    p_ack.add_argument("--all", action="store_true", help="Ack all unread messages")
    p_ack.add_argument("--tag", help="Tag override")
    p_ack.set_defaults(func=cmd_ack)

    # rpc
    p_rpc = sub.add_parser("rpc", help="Execute typed RPC over SSH stdin")
    p_rpc.add_argument("--method", required=True, help="RPC method name (send, poll, etc.)")
    p_rpc.add_argument("--params", help="JSON parameters object")
    p_rpc.set_defaults(func=cmd_rpc)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except Exception as exc:
        print(json.dumps({"error": type(exc).__name__, "message": str(exc), "at": _utc_now()}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
