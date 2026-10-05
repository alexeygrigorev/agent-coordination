"""Explicit device registration. Hostnames and SSH aliases must be allowlisted.

A hostname supplied by a task is never enough. Existing SSH config aliases
are eligible only after they appear in this registry.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from .errors import UnknownDevice, UnregisteredAlias


class DeviceKind(str, Enum):
    APLEXER_HOST = "aplexer-host"
    SSH_CLIENT_HOST = "ssh-client-host"


@dataclass(frozen=True)
class Device:
    id: str
    kind: DeviceKind
    ssh_alias: str | None
    hostname: str
    ssh_user: str | None
    aplexer_bin: str | None
    workspace_roots: tuple[str, ...]
    role: str
    native_aplexer: bool
    outbound_ssh_only: bool
    notes: str = ""

    def can_run_aplexer(self) -> bool:
        return self.kind is DeviceKind.APLEXER_HOST and bool(self.aplexer_bin) and self.native_aplexer


class DeviceRegistry:
    def __init__(self, devices: list[Device]):
        self._by_id = {}
        self._by_alias = {}
        for d in devices:
            if d.id in self._by_id:
                raise ValueError(f"Duplicate device ID: {d.id}")
            self._by_id[d.id] = d
            
            if d.ssh_alias:
                if d.ssh_alias in self._by_alias:
                    raise ValueError(f"Duplicate SSH alias: {d.ssh_alias}")
                self._by_alias[d.ssh_alias] = d

    @classmethod
    def load(cls, path: str | Path) -> DeviceRegistry:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DeviceRegistry:
        devices = []
        for raw in data.get("devices", []):
            devices.append(
                Device(
                    id=raw["id"],
                    kind=DeviceKind(raw["kind"]),
                    ssh_alias=raw.get("ssh_alias"),
                    hostname=raw["hostname"],
                    ssh_user=raw.get("ssh_user"),
                    aplexer_bin=raw.get("aplexer_bin"),
                    workspace_roots=tuple(raw.get("workspace_roots") or ()),
                    role=raw["role"],
                    native_aplexer=bool(raw.get("native_aplexer", False)),
                    outbound_ssh_only=bool(raw.get("outbound_ssh_only", False)),
                    notes=raw.get("notes") or "",
                )
            )
        return cls(devices)

    def get(self, device_id: str) -> Device:
        try:
            return self._by_id[device_id]
        except KeyError as exc:
            raise UnknownDevice(device_id) from exc

    def require_alias(self, alias: str) -> Device:
        try:
            return self._by_alias[alias]
        except KeyError as exc:
            raise UnregisteredAlias(alias) from exc

    def all(self) -> list[Device]:
        return list(self._by_id.values())

    def aplexer_hosts(self) -> list[Device]:
        return [d for d in self.all() if d.can_run_aplexer()]
