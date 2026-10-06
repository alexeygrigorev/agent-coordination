#!/usr/bin/env python3
"""Autonomous Sink Dispatcher Service for Product 4 (Cross-computer Agent Coordination).

Directive C3012:
Polls inbound FileBus messages for coord-primary-sink, validates multi-host admission
via MultiHostAdmission, emits structured host events to host_events.jsonl, and sends
correlated replies.
Zero aplexer dependencies or synthetic aplexer sessions.
"""

from __future__ import annotations

import argparse
import copy
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any

# Ensure agent-coordination is at index 0 of sys.path
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) in sys.path:
    sys.path.remove(str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT))


def _ensure_agent_bus_path() -> None:
    bus_roots = [
        os.environ.get("AGENT_BUS_ROOT"),
        "/home/alexey/git/agent-bus",
        str(Path(__file__).resolve().parents[3] / "agent-bus"),
        str(Path(__file__).resolve().parents[2] / "agent-bus"),
    ]
    for root in bus_roots:
        if root and os.path.isdir(root) and str(root) not in sys.path:
            sys.path.append(str(root))
            break


_ensure_agent_bus_path()

from adapters.agent_bus_client import (
    ack_message,
    poll_messages,
    reject_head_cred_inheritance,
    reply_message,
)
from coordination.host_interface import (
    GuardRejected,
    MultiHostAdmission,
    UnknownDevice,
    emit_host_event,
    load_device_registry,
    query_host_events,
)

__all__ = [
    "SinkDispatcher",
    "main",
    "build_cli_parser",
]


class SinkDispatcher:
    """Autonomous Sink Dispatcher Service for coord-primary-sink."""

    def __init__(
        self,
        store_path: Path | str | None,
        cred: dict[str, Any] | str | Path,
        admission: MultiHostAdmission | None = None,
        events_dir: Path | str | None = None,
    ) -> None:
        """Initialize SinkDispatcher with store path, sink credential, and admission validator."""
        if isinstance(cred, (str, Path)):
            cred_str = str(cred).strip()
            if cred_str.startswith("{") and cred_str.endswith("}"):
                self.cred = json.loads(cred_str)
            else:
                cred_path = Path(cred).resolve()
                if not cred_path.is_file():
                    raise FileNotFoundError(f"Credential file not found: {cred_path}")
                with open(cred_path, "r", encoding="utf-8") as f:
                    self.cred = json.load(f)
        elif isinstance(cred, dict):
            self.cred = cred
        else:
            raise TypeError(f"Invalid cred type: {type(cred).__name__}; expected dict, str, or Path")

        if store_path is not None:
            self.store_path = Path(store_path).resolve()
        elif "store" in self.cred:
            self.store_path = Path(self.cred["store"]).resolve()
        else:
            raise ValueError("store_path is required (neither passed as argument nor found in credential)")

        if events_dir is not None:
            self.events_dir = Path(events_dir).resolve()
        elif admission is not None and getattr(admission, "events_dir", None) is not None:
            self.events_dir = Path(admission.events_dir).resolve()
        else:
            self.events_dir = None

        if admission is not None:
            self.admission = admission
        else:
            self.admission = MultiHostAdmission(events_dir=self.events_dir)

        if self.events_dir is None and getattr(self.admission, "events_dir", None) is not None:
            self.events_dir = Path(self.admission.events_dir).resolve()

    def dispatch_message(self, msg: dict[str, Any]) -> dict[str, Any]:
        """Dispatch a single FileBus message.

        Extracts message_id, sender_id, body, and data payload.
        Validates task admission via MultiHostAdmission._admit_host_task_impl.
        On error (UnknownDevice, GuardRejected, ValueError):
            Emits rejection event to host_events.jsonl.
            Acknowledges message in FileBus to avoid poison-pill loops.
            Returns {'status': 'rejected', 'reason': str(err), 'message_id': message_id, 'device_id': device_id}.
        On success:
            Emits 'task_admitted' event to host_events.jsonl.
            If reply_requested or kind in ('command', 'handshake'), constructs and sends correlated reply.
            Acknowledges message in FileBus to advance cursor.
            Returns {'status': 'admitted', 'message_id': message_id, 'device_id': device_id, 'reply_sent': bool, 'event_id': ...}.
        """
        message_id = msg.get("message_id") or msg.get("id") or ""
        sender_id = msg.get("sender_id") or ""
        body = msg.get("body", "")
        raw_data = msg.get("data")
        if raw_data is None:
            data: dict[str, Any] = {}
        elif isinstance(raw_data, dict):
            data = copy.deepcopy(raw_data)
        elif isinstance(raw_data, str):
            try:
                parsed = json.loads(raw_data)
                data = parsed if isinstance(parsed, dict) else {"raw": parsed}
            except Exception:
                data = {"raw": raw_data}
        else:
            data = {"raw": raw_data}

        device_id = data.get("device_id") or data.get("origin_device") or "unknown"
        task_id = data.get("task_id") or f"msg:{message_id}"

        try:
            # Enforce head credential rejection fail-closed
            if data:
                try:
                    reject_head_cred_inheritance(data, reject=True)
                except ValueError as exc:
                    raise GuardRejected(str(exc)) from exc
            if body:
                try:
                    reject_head_cred_inheritance({"body": body}, reject=True)
                except ValueError as exc:
                    raise GuardRejected(str(exc)) from exc

            admit_res = self.admission._admit_host_task_impl(
                device_id, task_id, data, reject_on_cred=True
            )
        except (UnknownDevice, GuardRejected, ValueError) as err:
            event_type = (
                "guard_rejected"
                if isinstance(err, (GuardRejected, ValueError))
                else "admission_rejected"
            )
            emit_host_event(
                event_type=event_type,
                device_id=device_id,
                task_id=task_id,
                details={
                    "reason": str(err),
                    "error_type": type(err).__name__,
                    "message_id": message_id,
                    "sender_id": sender_id,
                },
                events_dir=self.events_dir,
            )
            if message_id:
                try:
                    ack_message(self.store_path, self.cred, message_id=message_id)
                except Exception as ack_err:
                    logging.getLogger(__name__).warning(
                        "Failed to ACK poison pill message %s: %s", message_id, ack_err
                    )
            return {
                "status": "rejected",
                "reason": str(err),
                "message_id": message_id,
                "device_id": device_id,
            }

        # On successful admission:
        event = emit_host_event(
            event_type="task_admitted",
            device_id=device_id,
            task_id=task_id,
            details={
                "device_id": admit_res.get("device_id", device_id),
                "task_id": admit_res.get("task_id", task_id),
                "delivery": admit_res.get("delivery"),
                "execution_target": admit_res.get("execution_target"),
                "session_id": admit_res.get("session_id"),
                "message_id": message_id,
                "sender_id": sender_id,
            },
            events_dir=self.events_dir,
        )

        reply_sent = False
        if data.get("reply_requested") or msg.get("kind") in ("command", "handshake"):
            sink_id = (
                self.cred.get("identity", {}).get("identity_id")
                if isinstance(self.cred.get("identity"), dict)
                else self.cred.get("identity_id")
            )
            reply_body = f"{msg.get('body', '')}-ACK"
            reply_data = {
                "handshake": data.get("handshake"),
                "status": "admitted",
                "sink_id": sink_id,
                "reply_to_message_id": message_id,
                "session_id": None,
                "execution_target": "hetzner-rmthz",
            }
            reply_message(
                store_path=self.store_path,
                cred=self.cred,
                message_id=message_id,
                body=reply_body,
                data=reply_data,
                idempotency_key=f"reply:{message_id}",
            )
            reply_sent = True

        if message_id:
            ack_message(self.store_path, self.cred, message_id=message_id)

        return {
            "status": "admitted",
            "message_id": message_id,
            "device_id": device_id,
            "reply_sent": reply_sent,
            "event_id": event.get("event_id"),
        }

    def poll_and_dispatch(
        self,
        max_messages: int = 20,
        unread_only: bool = True,
    ) -> list[dict[str, Any]]:
        """Poll FileBus inbox for sink and dispatch messages in FIFO order."""
        messages = poll_messages(self.store_path, self.cred, unread_only=unread_only)
        sorted_messages = sorted(
            messages,
            key=lambda m: (m.get("created_at") or "", m.get("seq", 0)),
        )
        if max_messages and max_messages > 0:
            batch = sorted_messages[:max_messages]
        else:
            batch = sorted_messages

        outcomes: list[dict[str, Any]] = []
        for msg in batch:
            outcome = self.dispatch_message(msg)
            outcomes.append(outcome)
        return outcomes


def build_cli_parser() -> argparse.ArgumentParser:
    """Build CLI argument parser for sink dispatcher."""
    parser = argparse.ArgumentParser(
        prog="sink_dispatcher",
        description="Autonomous Sink Dispatcher Service for coord-primary-sink (Product 4)",
    )
    parser.add_argument(
        "command", nargs="?", default=None, help="Optional subcommand (e.g. 'once', 'run')"
    )
    parser.add_argument("--store", "-s", default=None, help="Path to FileBus store directory")
    parser.add_argument(
        "--cred", "-c", required=True, help="Path to credentials file or JSON string"
    )
    parser.add_argument(
        "--registry", "-r", default=None, help="Path to device registry JSON file"
    )
    parser.add_argument("--events-dir", "-e", default=None, help="Path to events directory")
    parser.add_argument(
        "--once", action="store_true", default=False, help="Run single poll-dispatch cycle and exit"
    )
    parser.add_argument(
        "--max-messages",
        "-m",
        type=int,
        default=20,
        help="Max messages to dispatch per poll (default: 20)",
    )
    parser.add_argument(
        "--json", action="store_true", default=True, help="Output formatted JSON (default: True)"
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=1.0,
        help="Poll interval in continuous loop mode (default: 1.0s)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for sink dispatcher."""
    parser = build_cli_parser()
    args = parser.parse_args(argv)

    try:
        registry = load_device_registry(args.registry) if args.registry else None
        admission = MultiHostAdmission(registry=registry, events_dir=args.events_dir)
        dispatcher = SinkDispatcher(
            store_path=args.store,
            cred=args.cred,
            admission=admission,
            events_dir=args.events_dir,
        )

        is_once = args.once or (args.command in ("once", "poll"))

        if is_once:
            outcomes = dispatcher.poll_and_dispatch(max_messages=args.max_messages)
            output = {
                "status": "ok",
                "count": len(outcomes),
                "dispatched_count": len(outcomes),
                "outcomes": outcomes,
            }
            if args.json:
                print(json.dumps(output, indent=2))
            return 0
        else:
            # Continuous loop mode
            while True:
                outcomes = dispatcher.poll_and_dispatch(max_messages=args.max_messages)
                if outcomes and args.json:
                    output = {
                        "status": "ok",
                        "count": len(outcomes),
                        "dispatched_count": len(outcomes),
                        "outcomes": outcomes,
                    }
                    print(json.dumps(output, indent=2))
                time.sleep(args.interval)

    except KeyboardInterrupt:
        return 0
    except Exception as exc:
        err_output = {
            "status": "error",
            "error": str(exc),
            "error_type": type(exc).__name__,
        }
        print(json.dumps(err_output, indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
