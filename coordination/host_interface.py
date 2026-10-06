"""Multi-host admission and event logging interface.

Admit host tasks across heterogeneous topologies (e.g. Hetzner aplexer-host vs
Windows outbound-ssh-only clients) with strict validation, credential isolation,
and atomic JSONL event emission.
"""

from __future__ import annotations

import copy
import fcntl
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .device_registry import DeviceKind, DeviceRegistry
from .errors import GuardRejected, UnknownDevice

__all__ = [
    "MultiHostAdmission",
    "admit_host_task",
    "emit_host_event",
    "query_host_events",
    "reject_head_cred_inheritance",
    "load_device_registry",
    "UnknownDevice",
    "GuardRejected",
]

MAX_MEMORY_MB = 1500
DEFAULT_EVENTS_DIR = (
    Path(os.environ.get("AGENT_COORDINATION_EVENTS_DIR", ""))
    if os.environ.get("AGENT_COORDINATION_EVENTS_DIR")
    else Path(__file__).resolve().parents[1] / ".local" / "events"
)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_memory_mb(val: Any, default: int = MAX_MEMORY_MB) -> int:
    """Parse memory string (e.g. '1500M', '2G', 1024) into integer MB."""
    if val is None:
        return default
    if isinstance(val, (int, float)):
        return int(val)
    if isinstance(val, str):
        v = val.strip().upper()
        if v.endswith("G") or v.endswith("GB") or v.endswith("GIB"):
            num = float(v.rstrip("GIB").strip())
            return int(num * 1024)
        if v.endswith("M") or v.endswith("MB") or v.endswith("MIB"):
            num = float(v.rstrip("MIB").strip())
            return int(num)
        try:
            return int(v)
        except ValueError:
            return default
    return default


def load_device_registry(path: Path | str | None = None) -> DeviceRegistry:
    """Load DeviceRegistry from explicit path, env var, or default examples/devices.example.json."""
    if path is not None:
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Device registry not found at: {path}")
        return DeviceRegistry.load(p)

    env_path = (
        os.environ.get("AGENT_DEVICE_REGISTRY")
        or os.environ.get("COORDINATION_DEVICE_REGISTRY")
        or os.environ.get("DEVICE_REGISTRY_PATH")
    )
    if env_path:
        p = Path(env_path)
        if not p.exists():
            raise FileNotFoundError(f"Device registry not found at env path: {env_path}")
        return DeviceRegistry.load(p)

    repo_default = Path(__file__).resolve().parents[1] / "examples" / "devices.example.json"
    if repo_default.exists():
        return DeviceRegistry.load(repo_default)

    cwd_default = Path.cwd() / "examples" / "devices.example.json"
    if cwd_default.exists():
        return DeviceRegistry.load(cwd_default)

    raise FileNotFoundError("Could not find default examples/devices.example.json")


def reject_head_cred_inheritance(
    payload: dict[str, Any],
    *,
    reject: bool = False,
) -> dict[str, Any]:
    """Strip or reject head credential material from payload.

    If reject is True and head credentials exist, raises GuardRejected.
    Otherwise returns a cleaned copy with head credentials stripped.
    """
    has_head_cred = (
        "head.cred" in payload
        or "head_cred" in payload
        or "cred" in payload
        or (isinstance(payload.get("head"), dict) and "cred" in payload["head"])
    )
    if has_head_cred and reject:
        raise GuardRejected("head_cred_inheritance_rejected: forbidden credential inheritance")

    cleaned: dict[str, Any] = {}
    for k, v in payload.items():
        if k in ("head.cred", "head_cred", "cred"):
            continue
        if k == "head" and isinstance(v, dict):
            cleaned[k] = {sk: sv for sk, sv in v.items() if sk != "cred"}
        elif isinstance(v, dict):
            cleaned[k] = reject_head_cred_inheritance(v, reject=False)
        else:
            cleaned[k] = copy.deepcopy(v) if isinstance(v, list) else v
    return cleaned


def emit_host_event(
    event_type: str,
    device_id: str,
    task_id: str,
    details: dict[str, Any],
    events_dir: Path | str | None = None,
) -> dict[str, Any]:
    """Record a structured JSON line into host_events.jsonl atomically under events_dir."""
    target_dir = Path(events_dir) if events_dir is not None else DEFAULT_EVENTS_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    events_file = target_dir / "host_events.jsonl"

    ts = _utc()
    record = {
        "event_id": str(uuid.uuid4()),
        "event_type": event_type,
        "device_id": device_id,
        "task_id": task_id,
        "details": details,
        "timestamp": ts,
        "recorded_at": ts,
    }

    line = json.dumps(record, sort_keys=True) + "\n"
    with events_file.open("a", encoding="utf-8") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        try:
            f.write(line)
            f.flush()
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    return record


def query_host_events(
    events_dir: Path | str | None = None,
    *,
    event_type: str | None = None,
    device_id: str | None = None,
    task_id: str | None = None,
) -> list[dict[str, Any]]:
    """Query recorded host events from host_events.jsonl under events_dir."""
    target_dir = Path(events_dir) if events_dir is not None else DEFAULT_EVENTS_DIR
    events_file = target_dir / "host_events.jsonl"
    if not events_file.exists():
        return []

    events = []
    with events_file.open("r", encoding="utf-8") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_SH)
        try:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                evt = json.loads(line)
                if event_type and evt.get("event_type") != event_type:
                    continue
                if device_id and evt.get("device_id") != device_id:
                    continue
                if task_id and evt.get("task_id") != task_id:
                    continue
                events.append(evt)
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    return events


class MultiHostAdmission:
    """Validates and admits tasks across allowlisted multi-host topology."""

    def __init__(
        self,
        registry: DeviceRegistry | None = None,
        registry_path: Path | str | None = None,
        events_dir: Path | str | None = None,
    ):
        if registry is not None:
            self.registry = registry
        else:
            self.registry = load_device_registry(registry_path)

        if events_dir is not None:
            self.events_dir = Path(events_dir)
        else:
            self.events_dir = DEFAULT_EVENTS_DIR

    def _admit_host_task_impl(
        self,
        device_id: str,
        task_id: str,
        payload: dict[str, Any] | None = None,
        *,
        reject_on_cred: bool = False,
        enforce_memory_limit: bool = False,
    ) -> dict[str, Any]:
        device = self.registry.get(device_id)

        raw_payload = payload if payload is not None else {}
        sanitized_payload = copy.deepcopy(raw_payload)

        is_outbound = bool(getattr(device, "outbound_ssh_only", False))
        is_aplexer = (
            device.kind == DeviceKind.APLEXER_HOST
            or bool(getattr(device, "native_aplexer", False))
            or device.can_run_aplexer()
        )

        requested_mem = (
            sanitized_payload.get("memory_mb")
            or sanitized_payload.get("memory_limit")
            or sanitized_payload.get("memory")
        )
        parsed_mem = parse_memory_mb(requested_mem, default=MAX_MEMORY_MB)

        if is_outbound:
            # Enforces that session_id is None (never invent a Windows aplexer session).
            session_id = None
            if "session_id" in sanitized_payload:
                sanitized_payload["session_id"] = None

            # Enforces reject_head_cred_inheritance (strip or reject head.cred).
            sanitized_payload = reject_head_cred_inheritance(
                sanitized_payload, reject=reject_on_cred
            )

            # Sets execution_target to 'hetzner-rmthz' and delivery mode to 'sessionless_worker_bus'.
            execution_target = "hetzner-rmthz"
            delivery = "sessionless_worker_bus"
            memory_mb = min(parsed_mem, MAX_MEMORY_MB)

        elif is_aplexer:
            # For aplexer-host devices (e.g. hetzner-rmthz):
            # Verifies memory limit does not exceed 1500M (caps or enforces <= 1500M).
            if enforce_memory_limit and parsed_mem > MAX_MEMORY_MB:
                raise GuardRejected(
                    f"memory_limit_exceeded: {parsed_mem}MB exceeds {MAX_MEMORY_MB}MB"
                )
            memory_mb = min(parsed_mem, MAX_MEMORY_MB)

            # Sets delivery mode to 'local_task_unit'.
            delivery = "local_task_unit"
            execution_target = device.id
            session_id = sanitized_payload.get("session_id")
        else:
            memory_mb = min(parsed_mem, MAX_MEMORY_MB)
            delivery = "local_task_unit"
            execution_target = device.id
            session_id = sanitized_payload.get("session_id")

        return {
            "admitted": True,
            "device_id": device.id,
            "task_id": task_id,
            "execution_target": execution_target,
            "delivery": delivery,
            "session_id": session_id,
            "memory_mb": memory_mb,
            "payload": sanitized_payload,
        }

    def admit_host_task(
        self_or_cls,
        device_id: str,
        task_id: str,
        payload: dict[str, Any] | None = None,
        *,
        reject_on_cred: bool = False,
        enforce_memory_limit: bool = False,
    ) -> dict[str, Any]:
        """Admit task for host, validating topology, memory limits, and credentials."""
        if isinstance(self_or_cls, MultiHostAdmission):
            adm = self_or_cls
        else:
            adm = get_default_admission()
        return adm._admit_host_task_impl(
            device_id=device_id,
            task_id=task_id,
            payload=payload,
            reject_on_cred=reject_on_cred,
            enforce_memory_limit=enforce_memory_limit,
        )

    def emit_host_event(
        self_or_cls,
        event_type: str,
        device_id: str,
        task_id: str,
        details: dict[str, Any],
        events_dir: Path | str | None = None,
    ) -> dict[str, Any]:
        """Emit host event using configured or provided events directory."""
        if isinstance(self_or_cls, MultiHostAdmission):
            target_dir = events_dir or self_or_cls.events_dir
        else:
            target_dir = events_dir or DEFAULT_EVENTS_DIR
        return emit_host_event(
            event_type=event_type,
            device_id=device_id,
            task_id=task_id,
            details=details,
            events_dir=target_dir,
        )

    def query_host_events(
        self_or_cls,
        events_dir: Path | str | None = None,
        *,
        event_type: str | None = None,
        device_id: str | None = None,
        task_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Query host events using configured or provided events directory."""
        if isinstance(self_or_cls, MultiHostAdmission):
            target_dir = events_dir or self_or_cls.events_dir
        else:
            target_dir = events_dir or DEFAULT_EVENTS_DIR
        return query_host_events(
            events_dir=target_dir,
            event_type=event_type,
            device_id=device_id,
            task_id=task_id,
        )


_default_admission: MultiHostAdmission | None = None


def get_default_admission() -> MultiHostAdmission:
    global _default_admission
    if _default_admission is None:
        _default_admission = MultiHostAdmission()
    return _default_admission


def admit_host_task(
    device_id: str,
    task_id: str,
    payload: dict[str, Any] | None = None,
    *,
    admission: MultiHostAdmission | None = None,
    reject_on_cred: bool = False,
    enforce_memory_limit: bool = False,
) -> dict[str, Any]:
    """Module-level admission helper."""
    adm = admission or get_default_admission()
    return adm._admit_host_task_impl(
        device_id=device_id,
        task_id=task_id,
        payload=payload,
        reject_on_cred=reject_on_cred,
        enforce_memory_limit=enforce_memory_limit,
    )
