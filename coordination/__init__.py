"""Stdlib authenticated SSH relay for native aplexer cross-computer coordination."""

from .bus import BusIdentity, BusMessage, FileBus
from .catalog import Catalog, CatalogEntry, resolve_catalog
from .cursors import CursorStore
from .device_registry import Device, DeviceRegistry, DeviceKind
from .envelope import (
    ActionOutcome,
    NamespacedId,
    ReadAck,
    SendReceipt,
    TransportState,
)
from .errors import CoordinationError, GuardRejected, UnknownDevice, UnregisteredAlias
from .guards import DeliveryMode, GuardDecision, inspect_delivery_guard
from .ssh_relay import SshRelay, SshTransport
from .worker_bus import ReceiptStore, SessionlessWorkerBus, WorkerSendOutcome

__all__ = [
    "BusIdentity",
    "BusMessage",
    "FileBus",
    "ActionOutcome",
    "Catalog",
    "CatalogEntry",
    "CoordinationError",
    "CursorStore",
    "DeliveryMode",
    "Device",
    "DeviceKind",
    "DeviceRegistry",
    "GuardDecision",
    "GuardRejected",
    "NamespacedId",
    "ReadAck",
    "ReceiptStore",
    "SendReceipt",
    "SessionlessWorkerBus",
    "SshRelay",
    "SshTransport",
    "TransportState",
    "UnknownDevice",
    "UnregisteredAlias",
    "WorkerSendOutcome",
    "inspect_delivery_guard",
    "resolve_catalog",
]
