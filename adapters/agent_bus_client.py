#!/usr/bin/env python3
"""Product 4 (Cross-computer Agent Coordination) standalone AgentBus transport adapter.

Directive C2958 / C2959.
Zero aplexer dependencies or synthetic aplexer sessions. Pure Python 3.10+ standard library
and agent-bus FileBus integration.
"""

from __future__ import annotations

import argparse
import copy
import json
import logging
import os
import sqlite3
import sys
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

# Ensure agent-bus is importable via sys.path
def _ensure_agent_bus_path() -> None:
    bus_roots = [
        os.environ.get("AGENT_BUS_ROOT"),
        "/home/alexey/git/agent-bus",
        str(Path(__file__).resolve().parents[3] / "agent-bus"),
        str(Path(__file__).resolve().parents[2] / "agent-bus"),
    ]
    for root in bus_roots:
        if root and os.path.isdir(root) and str(root) not in sys.path:
            sys.path.insert(0, str(root))
            break

_ensure_agent_bus_path()

try:
    from coordination.bus import BusError, BusIdentity, BusMessage, FileBus
    from coordination.errors import CoordinationError, IdempotencyConflict
except ImportError as err:
    raise ImportError(
        f"Failed to import FileBus from coordination.bus. Please ensure /home/alexey/git/agent-bus is on sys.path or set AGENT_BUS_ROOT: {err}"
    ) from err

# Guarantee sessionless invariant on BusIdentity:
# Non-aplexer (e.g. Windows desktop, standalone headless) agents have session_id=None.
if not hasattr(BusIdentity, "to_dict"):
    def _bus_identity_to_dict(self, *, include_explicit_none: bool = True) -> dict[str, Any]:
        d = asdict(self)
        if include_explicit_none or "session_id" not in d:
            d["session_id"] = None
        return d

    BusIdentity.to_dict = _bus_identity_to_dict  # type: ignore[attr-defined]


def reject_head_cred_inheritance(payload: Any, *, reject: bool = True) -> Any:
    """Inspect payload for head credentials ('head.cred', 'head_token', etc.).

    If reject=True and any head credential material is detected, raises ValueError.
    If reject=False, returns a sanitized copy with head credential keys stripped.
    """
    if payload is None:
        return None

    forbidden_exact_keys = {"head.cred", "head_cred", "head_token", "head.token", "cred"}

    def _contains_head_cred(obj: Any) -> bool:
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k in forbidden_exact_keys:
                    return True
                if k == "head" and isinstance(v, dict):
                    if any(sk in v for sk in ("cred", "token", "head.cred", "head_cred", "head_token", "head.token")):
                        return True
                if k == "token" and isinstance(v, str) and "head" in v.lower():
                    return True
                if isinstance(v, str) and ("head.cred" in v.lower() or "head_token" in v.lower()):
                    return True
                if isinstance(v, (dict, list)) and _contains_head_cred(v):
                    return True
        elif isinstance(obj, list):
            for item in obj:
                if isinstance(item, str) and ("head.cred" in item.lower() or "head_token" in item.lower()):
                    return True
                if isinstance(item, (dict, list)) and _contains_head_cred(item):
                    return True
        elif isinstance(obj, str):
            if "head.cred" in obj.lower() or "head_token" in obj.lower():
                return True
        return False

    if _contains_head_cred(payload) and reject:
        raise ValueError("head_cred_inheritance_rejected: forbidden head credential inheritance in payload")

    def _strip_head_cred(obj: Any) -> Any:
        if isinstance(obj, dict):
            cleaned: dict[str, Any] = {}
            for k, v in obj.items():
                if k in forbidden_exact_keys:
                    continue
                if k == "token" and isinstance(v, str) and "head" in v.lower():
                    continue
                if k == "head" and isinstance(v, dict):
                    cleaned[k] = {
                        sk: sv
                        for sk, sv in v.items()
                        if sk not in ("cred", "token", "head.cred", "head_cred", "head_token", "head.token")
                    }
                elif isinstance(v, (dict, list)):
                    cleaned[k] = _strip_head_cred(v)
                else:
                    cleaned[k] = copy.deepcopy(v) if isinstance(v, list) else v
            return cleaned
        elif isinstance(obj, list):
            return [
                _strip_head_cred(item)
                for item in obj
                if not (isinstance(item, str) and ("head.cred" in item.lower() or "head_token" in item.lower()))
            ]
        return obj

    return _strip_head_cred(payload)


def _resolve_cred_and_store(
    store_path: str | Path | None,
    cred: dict[str, Any] | str | Path,
) -> tuple[str, str, Path]:
    """Extract identity_id, token, and store path from cred input."""
    cred_dict: dict[str, Any] = {}
    if isinstance(cred, str) and cred.strip().startswith("{") and cred.strip().endswith("}"):
        try:
            cred_dict = json.loads(cred)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON in cred string: {exc}") from exc
    elif isinstance(cred, (str, Path)):
        cred_file = Path(cred).resolve()
        if not cred_file.is_file():
            raise FileNotFoundError(f"Credential file not found: {cred_file}")
        with open(cred_file, "r", encoding="utf-8") as f:
            cred_dict = json.load(f)
    elif isinstance(cred, dict):
        cred_dict = cred
    else:
        raise TypeError(f"Invalid cred type: {type(cred).__name__}; expected dict, str, or Path")

    token = cred_dict.get("token")
    if not token or not isinstance(token, str):
        raise ValueError("Credential missing valid 'token'")

    identity = cred_dict.get("identity")
    identity_id: str | None = None
    if isinstance(identity, dict):
        identity_id = identity.get("identity_id")
    elif "identity_id" in cred_dict:
        identity_id = cred_dict["identity_id"]

    if not identity_id or not isinstance(identity_id, str):
        raise ValueError("Credential missing valid 'identity.identity_id' or 'identity_id'")

    actual_store = store_path
    if actual_store is None:
        actual_store = cred_dict.get("store")
    if actual_store is None:
        raise ValueError("store_path is required (neither passed as argument nor found in credential)")

    return identity_id, token, Path(actual_store).resolve()


def enroll_agent(
    store_path: str | Path,
    agent_name: str,
    device_id: str = "windows-desktop",
    project_id: str = "cross-computer-coordination",
    task_id: str | None = None,
    cred_path: str | Path | None = None,
) -> tuple[dict[str, Any], str]:
    """Enroll an agent identity on FileBus and write mode 0600 credentials atomically.

    Returns:
        (cred_dict, cred_path_str)
    """
    store_path = Path(store_path).resolve()
    bus = FileBus(store_path)
    ident, tok = bus.register(
        agent_name=agent_name,
        device_id=device_id,
        project_id=project_id,
        task_id=task_id,
    )

    ident_dict = ident.to_dict() if hasattr(ident, "to_dict") else ident.public()
    if "session_id" not in ident_dict or ident_dict.get("session_id") is not None:
        ident_dict["session_id"] = None

    if cred_path is None:
        cred_dir = store_path / "credentials"
        cred_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        target_cred_file = cred_dir / f"{agent_name}.cred.json"
    else:
        target_cred_file = Path(cred_path).resolve()
        target_cred_file.parent.mkdir(parents=True, exist_ok=True, mode=0o700)

    cred_data = {
        "identity": ident_dict,
        "token": tok,
        "store": str(store_path),
    }

    # Write atomically with mode 0600
    tmp_path = target_cred_file.with_name(f"{target_cred_file.name}.tmp.{uuid.uuid4().hex}")
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
    fd = os.open(str(tmp_path), flags, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(cred_data, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.chmod(str(tmp_path), 0o600)
        os.replace(str(tmp_path), str(target_cred_file))
    except Exception:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass
        raise

    return cred_data, str(target_cred_file)


def send_message(
    store_path: str | Path | None,
    cred: dict[str, Any] | str | Path,
    recipient_id: str,
    body: str,
    data: dict[str, Any] | None = None,
    kind: str = "note",
    idempotency_key: str | None = None,
    *,
    reject_head_cred: bool = True,
) -> dict[str, Any]:
    """Send a message over AgentBus enforcing head credential protection."""
    if data is not None:
        data = reject_head_cred_inheritance(data, reject=reject_head_cred)
    if reject_head_cred and body:
        reject_head_cred_inheritance({"body": body}, reject=True)

    identity_id, token, actual_store = _resolve_cred_and_store(store_path, cred)
    bus = FileBus(actual_store)
    msg = bus.send(
        sender_id=identity_id,
        token=token,
        recipient_id=recipient_id,
        body=body,
        data=data,
        idempotency_key=idempotency_key,
        kind=kind,
    )
    return msg.to_public()


def poll_messages(
    store_path: str | Path | None,
    cred: dict[str, Any] | str | Path,
    unread_only: bool = True,
) -> list[dict[str, Any]]:
    """Poll inbox messages from AgentBus."""
    identity_id, token, actual_store = _resolve_cred_and_store(store_path, cred)
    bus = FileBus(actual_store)
    messages = bus.inbox(identity_id, token, unread_only=unread_only)
    return [m.to_public() for m in messages]


def reply_message(
    store_path: str | Path | None,
    cred: dict[str, Any] | str | Path,
    message_id: str,
    body: str,
    data: dict[str, Any] | None = None,
    idempotency_key: str | None = None,
    *,
    reject_head_cred: bool = True,
) -> dict[str, Any]:
    """Reply to an existing message over AgentBus."""
    if data is not None:
        data = reject_head_cred_inheritance(data, reject=reject_head_cred)
    if reject_head_cred and body:
        reject_head_cred_inheritance({"body": body}, reject=True)

    identity_id, token, actual_store = _resolve_cred_and_store(store_path, cred)
    bus = FileBus(actual_store)
    msg = bus.reply(
        sender_id=identity_id,
        token=token,
        message_id=message_id,
        body=body,
        data=data,
        idempotency_key=idempotency_key,
    )
    return msg.to_public()


def ack_message(
    store_path: str | Path | None,
    cred: dict[str, Any] | str | Path,
    message_id: str,
) -> bool:
    """Acknowledge (read ACK) a message on AgentBus."""
    identity_id, token, actual_store = _resolve_cred_and_store(store_path, cred)
    bus = FileBus(actual_store)
    msg = bus.ack(identity_id, token, message_id=message_id)
    return bool(msg and msg.acked_at is not None)


class OfflineSpool:
    """SQLite-backed message spool for offline queueing, durable retry, and FIFO dispatch."""

    def __init__(self, db_path: str | Path | None = None) -> None:
        if db_path is None:
            self.db_path = Path(".local/spool.db").resolve()
        else:
            self.db_path = Path(db_path).resolve()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=30.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        conn = self._connect()
        try:
            with conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS spooled_messages (
                        spool_id TEXT PRIMARY KEY,
                        recipient_id TEXT NOT NULL,
                        body TEXT NOT NULL,
                        data TEXT,
                        idempotency_key TEXT,
                        kind TEXT NOT NULL DEFAULT 'note',
                        status TEXT NOT NULL DEFAULT 'pending',
                        created_at TEXT NOT NULL,
                        delivered_at TEXT,
                        message_id TEXT
                    )
                """)
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_spool_status_created ON spooled_messages(status, created_at)"
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_spool_idempotency ON spooled_messages(idempotency_key)"
                )
        finally:
            conn.close()

    def spool_message(
        self,
        recipient_id: str,
        body: str,
        data: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
        kind: str = "note",
    ) -> dict[str, Any]:
        """Spool a message locally for offline queueing with fail-closed credential protection."""
        if data is not None:
            data = reject_head_cred_inheritance(data, reject=True)
        if body:
            reject_head_cred_inheritance({"body": body}, reject=True)

        conn = self._connect()
        try:
            with conn:
                if idempotency_key is not None:
                    cur = conn.execute(
                        """
                        SELECT spool_id, recipient_id, body, data, idempotency_key, kind, status, created_at, delivered_at, message_id
                        FROM spooled_messages
                        WHERE idempotency_key = ?
                        """,
                        (idempotency_key,),
                    )
                    row = cur.fetchone()
                    if row is not None:
                        existing_data = json.loads(row["data"]) if row["data"] is not None else None
                        if (
                            row["recipient_id"] == recipient_id
                            and row["body"] == body
                            and existing_data == data
                            and row["kind"] == kind
                        ):
                            return {
                                "spool_id": row["spool_id"],
                                "recipient_id": row["recipient_id"],
                                "body": row["body"],
                                "data": existing_data,
                                "idempotency_key": row["idempotency_key"],
                                "kind": row["kind"],
                                "status": row["status"],
                                "created_at": row["created_at"],
                                "delivered_at": row["delivered_at"],
                                "message_id": row["message_id"],
                            }
                        raise IdempotencyConflict(idempotency_key)

                spool_id = str(uuid.uuid4())
                created_at = datetime.now(timezone.utc).isoformat()
                data_json = json.dumps(data) if data is not None else None
                conn.execute(
                    """
                    INSERT INTO spooled_messages (
                        spool_id, recipient_id, body, data, idempotency_key, kind, status, created_at, delivered_at, message_id
                    ) VALUES (?, ?, ?, ?, ?, ?, 'pending', ?, NULL, NULL)
                    """,
                    (spool_id, recipient_id, body, data_json, idempotency_key, kind, created_at),
                )
                return {
                    "spool_id": spool_id,
                    "recipient_id": recipient_id,
                    "body": body,
                    "data": data,
                    "idempotency_key": idempotency_key,
                    "kind": kind,
                    "status": "pending",
                    "created_at": created_at,
                    "delivered_at": None,
                    "message_id": None,
                }
        finally:
            conn.close()

    def list_pending(self) -> list[dict[str, Any]]:
        """Return pending messages sorted chronologically (FIFO)."""
        conn = self._connect()
        try:
            cur = conn.execute(
                """
                SELECT spool_id, recipient_id, body, data, idempotency_key, kind, status, created_at, delivered_at, message_id
                FROM spooled_messages
                WHERE status = 'pending'
                ORDER BY created_at ASC, rowid ASC
                """
            )
            rows = cur.fetchall()
            messages: list[dict[str, Any]] = []
            for r in rows:
                row_data = json.loads(r["data"]) if r["data"] is not None else None
                messages.append({
                    "spool_id": r["spool_id"],
                    "recipient_id": r["recipient_id"],
                    "body": r["body"],
                    "data": row_data,
                    "idempotency_key": r["idempotency_key"],
                    "kind": r["kind"],
                    "status": r["status"],
                    "created_at": r["created_at"],
                    "delivered_at": r["delivered_at"],
                    "message_id": r["message_id"],
                })
            return messages
        finally:
            conn.close()

    def mark_delivered(self, spool_id: str, message_id: str) -> None:
        """Mark a spooled message as delivered."""
        now = datetime.now(timezone.utc).isoformat()
        conn = self._connect()
        try:
            with conn:
                conn.execute(
                    """
                    UPDATE spooled_messages
                    SET status = 'delivered', delivered_at = ?, message_id = ?
                    WHERE spool_id = ?
                    """,
                    (now, message_id, spool_id),
                )
        finally:
            conn.close()

    def flush(
        self,
        store_path: str | Path | None,
        cred: dict[str, Any] | str | Path,
        transport_fn: Callable[..., Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Flush pending spooled messages in FIFO order.

        Fails closed on error without dropping pending messages.
        """
        pending = self.list_pending()
        delivered: list[dict[str, Any]] = []

        for item in pending:
            try:
                if transport_fn is not None:
                    try:
                        receipt = transport_fn(
                            store_path,
                            cred,
                            recipient_id=item["recipient_id"],
                            body=item["body"],
                            data=item["data"],
                            kind=item["kind"],
                            idempotency_key=item["idempotency_key"],
                        )
                    except TypeError:
                        try:
                            receipt = transport_fn(
                                store_path=store_path,
                                cred=cred,
                                recipient_id=item["recipient_id"],
                                body=item["body"],
                                data=item["data"],
                                kind=item["kind"],
                                idempotency_key=item["idempotency_key"],
                            )
                        except TypeError:
                            receipt = transport_fn(item)
                else:
                    receipt = send_message(
                        store_path=store_path,
                        cred=cred,
                        recipient_id=item["recipient_id"],
                        body=item["body"],
                        data=item["data"],
                        kind=item["kind"],
                        idempotency_key=item["idempotency_key"],
                    )

                msg_id = ""
                if isinstance(receipt, dict):
                    msg_id = receipt.get("message_id") or receipt.get("id") or ""
                elif hasattr(receipt, "message_id"):
                    msg_id = getattr(receipt, "message_id")
                elif isinstance(receipt, str):
                    msg_id = receipt

                self.mark_delivered(item["spool_id"], msg_id)
                if isinstance(receipt, dict):
                    receipt_copy = dict(receipt)
                    receipt_copy["spool_id"] = item["spool_id"]
                    delivered.append(receipt_copy)
                else:
                    delivered.append({
                        "spool_id": item["spool_id"],
                        "message_id": msg_id,
                        "recipient_id": item["recipient_id"],
                        "status": "delivered",
                    })
            except Exception as exc:
                logging.getLogger(__name__).error(
                    "OfflineSpool flush error on %s: %s", item.get("spool_id"), exc
                )
                break

        return delivered


def build_typed_ssh_command(
    host: str,
    store_path: str,
    cred_path: str,
    method: str = "poll",
    params: dict[str, Any] | None = None,
    python_bin: str = "python3",
) -> tuple[list[str], str]:
    """Generate typed SSH command and stdin JSON payload avoiding shell quoting issues."""
    cmd_args = [
        "ssh",
        host,
        python_bin,
        "-m",
        "adapters.agent_bus_client",
        "rpc",
        "--store",
        str(store_path),
        "--cred",
        str(cred_path),
        "--stdin",
    ]
    payload = {
        "method": method,
        "params": params if params is not None else {},
    }
    json_stdin_payload = json.dumps(payload)
    return cmd_args, json_stdin_payload


_RPC_HANDLERS: dict[str, Callable[..., Any]] = {}


def register_rpc_handler(method: str, handler: Callable[..., Any]) -> None:
    """Register a custom RPC method handler."""
    _RPC_HANDLERS[method] = handler


def rpc_dispatch(
    store_path: str | Path | None,
    cred: dict[str, Any] | str | Path,
    method: str,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Dispatch an RPC request to registered or built-in handlers."""
    if params is None:
        params = {}
    elif not isinstance(params, dict):
        raise TypeError(f"params must be a dict, got {type(params).__name__}")

    if method in _RPC_HANDLERS:
        res = _RPC_HANDLERS[method](store_path, cred, params)
        if isinstance(res, dict) and "status" in res:
            return res
        return {"status": "ok", "method": method, "result": res}

    if method == "send":
        recipient_id = params.get("recipient_id") or params.get("recipient") or params.get("to")
        if not recipient_id:
            raise ValueError("Missing 'recipient_id' in params for send")
        body = params.get("body", "")
        data = params.get("data")
        kind = params.get("kind", "note")
        idempotency_key = params.get("idempotency_key")
        result = send_message(
            store_path,
            cred,
            recipient_id=recipient_id,
            body=body,
            data=data,
            kind=kind,
            idempotency_key=idempotency_key,
        )
        return {"status": "ok", "method": "send", "result": result, **result}

    elif method in ("poll", "inbox"):
        unread_only = params.get("unread_only", True)
        result = poll_messages(store_path, cred, unread_only=unread_only)
        return {"status": "ok", "method": method, "result": result, "messages": result}

    elif method == "reply":
        message_id = params.get("message_id") or params.get("reply_to")
        if not message_id:
            raise ValueError("Missing 'message_id' in params for reply")
        body = params.get("body", "")
        data = params.get("data")
        idempotency_key = params.get("idempotency_key")
        result = reply_message(
            store_path,
            cred,
            message_id=message_id,
            body=body,
            data=data,
            idempotency_key=idempotency_key,
        )
        return {"status": "ok", "method": "reply", "result": result, **result}

    elif method == "ack":
        message_id = params.get("message_id")
        if not message_id:
            raise ValueError("Missing 'message_id' in params for ack")
        result = ack_message(store_path, cred, message_id=message_id)
        return {"status": "ok", "method": "ack", "result": result, "acked": result, "message_id": message_id}

    elif method == "enroll":
        agent_name = params.get("agent_name") or params.get("name")
        if not agent_name:
            raise ValueError("Missing 'agent_name' in params for enroll")
        device_id = params.get("device_id", "windows-desktop")
        project_id = params.get("project_id", "cross-computer-coordination")
        task_id = params.get("task_id")
        cred_path = params.get("cred_path")
        target_store = store_path or params.get("store") or params.get("store_path")
        if not target_store:
            raise ValueError("Missing 'store_path' for enroll")
        cred_data, saved_path = enroll_agent(
            store_path=target_store,
            agent_name=agent_name,
            device_id=device_id,
            project_id=project_id,
            task_id=task_id,
            cred_path=cred_path,
        )
        return {"status": "ok", "method": "enroll", "result": cred_data, "cred_path": saved_path, **cred_data}

    elif method == "ping":
        return {"status": "ok", "method": "ping", "pong": True, "params": params}

    elif method == "echo":
        return {"status": "ok", "method": "echo", "result": params, "params": params}

    elif method == "spool":
        db_path = params.get("spool_db") or params.get("db_path")
        spool = OfflineSpool(db_path=db_path)
        data = params.get("data")
        res = spool.spool_message(
            recipient_id=params["recipient_id"],
            body=params["body"],
            data=data,
            idempotency_key=params.get("idempotency_key"),
            kind=params.get("kind", "note"),
        )
        return {"status": "ok", "method": "spool", "result": res, **res}

    elif method == "flush":
        db_path = params.get("spool_db") or params.get("db_path")
        spool = OfflineSpool(db_path=db_path)
        delivered = spool.flush(store_path=store_path, cred=cred)
        return {
            "status": "ok",
            "method": "flush",
            "count": len(delivered),
            "delivered": delivered,
            "pending_remaining": len(spool.list_pending()),
        }

    else:
        raise ValueError(f"Unknown RPC method: '{method}'")


def build_cli_parser() -> argparse.ArgumentParser:
    """Construct CLI argument parser for AgentBus transport."""
    parser = argparse.ArgumentParser(
        prog="agent_bus_transport",
        description="Product 4 AgentBus transport adapter for cross-computer agent coordination",
    )
    parser.add_argument("--json", action="store_true", default=True, help="Output formatted JSON (default True)")
    subparsers = parser.add_subparsers(dest="subcommand", required=True, help="Subcommand to execute")

    # enroll
    enroll_p = subparsers.add_parser("enroll", help="Enroll an agent identity")
    enroll_p.add_argument("--store", "-s", required=True, help="Path to FileBus store directory")
    enroll_p.add_argument("--name", "-n", "--agent-name", required=True, dest="agent_name", help="Agent name")
    enroll_p.add_argument(
        "--device", "--device-id", default="windows-desktop", dest="device_id", help="Device ID (default: windows-desktop)"
    )
    enroll_p.add_argument(
        "--project",
        "--project-id",
        default="cross-computer-coordination",
        dest="project_id",
        help="Project ID (default: cross-computer-coordination)",
    )
    enroll_p.add_argument("--task", "--task-id", default=None, dest="task_id", help="Task ID (optional)")
    enroll_p.add_argument("--cred", "--cred-path", default=None, dest="cred_path", help="Path to save credentials file")

    # send
    send_p = subparsers.add_parser("send", help="Send a message over AgentBus")
    send_p.add_argument("--store", "-s", default=None, help="Path to FileBus store directory (optional if in cred)")
    send_p.add_argument("--cred", "-c", required=True, help="Path to credentials file or JSON string")
    send_p.add_argument("--recipient", "-r", "--to", required=True, dest="recipient_id", help="Recipient identity ID")
    send_p.add_argument("--body", "-b", required=True, help="Message body")
    send_p.add_argument("--data", "-d", default=None, help="JSON-encoded data payload")
    send_p.add_argument("--kind", "-k", default="note", help="Message kind (default: note)")
    send_p.add_argument("--key", "--idempotency-key", default=None, dest="idempotency_key", help="Idempotency key")

    # poll
    poll_p = subparsers.add_parser("poll", help="Poll inbox for messages")
    poll_p.add_argument("--store", "-s", default=None, help="Path to FileBus store directory (optional if in cred)")
    poll_p.add_argument("--cred", "-c", required=True, help="Path to credentials file or JSON string")
    poll_p.add_argument(
        "--unread", action="store_true", default=True, help="Only return unread messages (default: True)"
    )
    poll_p.add_argument("--all", action="store_false", dest="unread", help="Return all messages including read")

    # reply
    reply_p = subparsers.add_parser("reply", help="Reply to an existing message")
    reply_p.add_argument("--store", "-s", default=None, help="Path to FileBus store directory (optional if in cred)")
    reply_p.add_argument("--cred", "-c", required=True, help="Path to credentials file or JSON string")
    reply_p.add_argument(
        "--message-id", "-m", "--msg-id", required=True, dest="message_id", help="Message ID to reply to"
    )
    reply_p.add_argument("--body", "-b", required=True, help="Reply message body")
    reply_p.add_argument("--data", "-d", default=None, help="JSON-encoded data payload")
    reply_p.add_argument("--key", "--idempotency-key", default=None, dest="idempotency_key", help="Idempotency key")

    # ack
    ack_p = subparsers.add_parser("ack", help="Acknowledge (read ACK) a message")
    ack_p.add_argument("--store", "-s", default=None, help="Path to FileBus store directory (optional if in cred)")
    ack_p.add_argument("--cred", "-c", required=True, help="Path to credentials file or JSON string")
    ack_p.add_argument(
        "--message-id", "-m", "--msg-id", required=True, dest="message_id", help="Message ID to acknowledge"
    )

    # rpc
    rpc_p = subparsers.add_parser("rpc", help="Dispatch an RPC call")
    rpc_p.add_argument("--store", "-s", default=None, help="Path to FileBus store directory (optional if in cred)")
    rpc_p.add_argument("--cred", "-c", required=True, help="Path to credentials file or JSON string")
    rpc_p.add_argument("--method", "-m", default=None, help="RPC method name")
    rpc_p.add_argument("--params", "-p", default="{}", help="JSON string of parameters")
    rpc_p.add_argument("--stdin", action="store_true", default=False, help="Read JSON RPC request from stdin")

    # spool
    spool_p = subparsers.add_parser("spool", help="Enroll/spool a message locally in SQLite outbox spool")
    spool_p.add_argument("--recipient", "-r", "--to", required=True, dest="recipient_id", help="Recipient identity ID")
    spool_p.add_argument("--body", "-b", required=True, help="Message body")
    spool_p.add_argument("--data", "-d", default=None, help="JSON-encoded data payload")
    spool_p.add_argument("--kind", "-k", default="note", help="Message kind (default: note)")
    spool_p.add_argument("--key", "--idempotency-key", default=None, dest="idempotency_key", help="Idempotency key")
    spool_p.add_argument("--spool-db", "--db", default=None, dest="db_path", help="Path to spool SQLite database (default: .local/spool.db)")

    # flush
    flush_p = subparsers.add_parser("flush", help="Flush local spool outbox to destination AgentBus store")
    flush_p.add_argument("--store", "-s", default=None, help="Path to FileBus store directory (optional if in cred)")
    flush_p.add_argument("--cred", "-c", required=True, help="Path to credentials file or JSON string")
    flush_p.add_argument("--spool-db", "--db", default=None, dest="db_path", help="Path to spool SQLite database (default: .local/spool.db)")

    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for agent_bus_transport."""
    parser = build_cli_parser()
    args = parser.parse_args(argv)

    try:
        if args.subcommand == "enroll":
            cred_data, cred_file = enroll_agent(
                store_path=args.store,
                agent_name=args.agent_name,
                device_id=args.device_id,
                project_id=args.project_id,
                task_id=args.task_id,
                cred_path=args.cred_path,
            )
            output = {
                "status": "ok",
                "action": "enroll",
                "cred_path": cred_file,
                **cred_data,
            }
            print(json.dumps(output, indent=2))
            return 0

        elif args.subcommand == "send":
            data = json.loads(args.data) if args.data else None
            result = send_message(
                store_path=args.store,
                cred=args.cred,
                recipient_id=args.recipient_id,
                body=args.body,
                data=data,
                kind=args.kind,
                idempotency_key=args.idempotency_key,
            )
            output = {
                "status": "ok",
                "action": "send",
                "message": result,
                **result,
            }
            print(json.dumps(output, indent=2))
            return 0

        elif args.subcommand == "poll":
            messages = poll_messages(
                store_path=args.store,
                cred=args.cred,
                unread_only=args.unread,
            )
            output = {
                "status": "ok",
                "action": "poll",
                "count": len(messages),
                "messages": messages,
            }
            print(json.dumps(output, indent=2))
            return 0

        elif args.subcommand == "reply":
            data = json.loads(args.data) if args.data else None
            result = reply_message(
                store_path=args.store,
                cred=args.cred,
                message_id=args.message_id,
                body=args.body,
                data=data,
                idempotency_key=args.idempotency_key,
            )
            output = {
                "status": "ok",
                "action": "reply",
                "message": result,
                **result,
            }
            print(json.dumps(output, indent=2))
            return 0

        elif args.subcommand == "ack":
            acked = ack_message(
                store_path=args.store,
                cred=args.cred,
                message_id=args.message_id,
            )
            output = {
                "status": "ok",
                "action": "ack",
                "message_id": args.message_id,
                "acked": acked,
            }
            print(json.dumps(output, indent=2))
            return 0

        elif args.subcommand == "spool":
            data = json.loads(args.data) if args.data else None
            spool = OfflineSpool(db_path=args.db_path)
            spooled = spool.spool_message(
                recipient_id=args.recipient_id,
                body=args.body,
                data=data,
                idempotency_key=args.idempotency_key,
                kind=args.kind,
            )
            output = {
                "status": "ok",
                "action": "spool",
                "spool_id": spooled["spool_id"],
                "recipient_id": spooled["recipient_id"],
                "body": spooled["body"],
                "data": spooled["data"],
                "idempotency_key": spooled["idempotency_key"],
                "kind": spooled["kind"],
                "created_at": spooled["created_at"],
                "spool_status": spooled["status"],
                "message": spooled,
            }
            print(json.dumps(output, indent=2))
            return 0

        elif args.subcommand == "flush":
            spool = OfflineSpool(db_path=args.db_path)
            delivered = spool.flush(
                store_path=args.store,
                cred=args.cred,
            )
            output = {
                "status": "ok",
                "action": "flush",
                "count": len(delivered),
                "delivered": delivered,
                "pending_remaining": len(spool.list_pending()),
            }
            print(json.dumps(output, indent=2))
            return 0

        elif args.subcommand == "rpc":
            if args.stdin:
                stdin_text = sys.stdin.read().strip()
                if not stdin_text:
                    raise ValueError("Empty stdin provided for RPC --stdin")
                payload = json.loads(stdin_text)
                method = payload.get("method") or args.method
                if not method:
                    raise ValueError("RPC method missing from stdin JSON payload and --method argument")
                params = payload.get("params", {})
            else:
                if not args.method:
                    raise ValueError("Missing required --method argument")
                method = args.method
                params = json.loads(args.params) if isinstance(args.params, str) else args.params

            result = rpc_dispatch(
                store_path=args.store,
                cred=args.cred,
                method=method,
                params=params,
            )
            print(json.dumps(result, indent=2))
            return 0

        else:
            parser.print_help(sys.stderr)
            return 1

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
