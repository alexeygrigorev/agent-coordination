"""Resolve native aplexer catalogs at send time. Never cache as authority."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable

from .device_registry import Device
from .errors import CatalogStale, NativeBindingMissing


@dataclass(frozen=True)
class CatalogEntry:
    session_id: str
    tag: str
    workspace: str
    engine: str | None
    reported_state: str | None
    phase: str | None


@dataclass(frozen=True)
class Catalog:
    device_id: str
    observed_at: str
    entries: tuple[CatalogEntry, ...]
    source_command: tuple[str, ...]

    def resolve_tag(self, workspace: str, tag: str) -> CatalogEntry:
        matches = [
            e
            for e in self.entries
            if e.workspace == workspace and e.tag == tag
        ]
        if not matches:
            raise CatalogStale(f"tag_unresolved:{workspace}:{tag}")
        live = [e for e in matches if e.phase == "running"]
        chosen = live[0] if live else matches[0]
        return chosen


Runner = Callable[[Device, list[str]], str]


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def resolve_catalog(device: Device, runner: Runner, workspace: str | None = None) -> Catalog:
    if not device.can_run_aplexer():
        raise NativeBindingMissing(device.id)
    argv = [device.aplexer_bin or "aplexer", "list", "--json"]
    raw = runner(device, argv)
    parsed = json.loads(raw)
    items = parsed if isinstance(parsed, list) else parsed.get("sessions", parsed.get("items", []))
    entries = []
    for item in items:
        ws = item.get("workspace") or ""
        if workspace and ws != workspace:
            continue
        entries.append(
            CatalogEntry(
                session_id=item["id"],
                tag=item["tag"],
                workspace=ws,
                engine=item.get("engine"),
                reported_state=item.get("reported_state"),
                phase=item.get("phase"),
            )
        )
    return Catalog(
        device_id=device.id,
        observed_at=utc_now(),
        entries=tuple(entries),
        source_command=tuple(argv),
    )
