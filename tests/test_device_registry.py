from pathlib import Path

import pytest

from coordination.device_registry import DeviceKind, DeviceRegistry
from coordination.errors import UnknownDevice, UnregisteredAlias

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "devices.example.json"


def test_loads_more_than_two_host_slots():
    registry = DeviceRegistry.load(EXAMPLE)
    ids = {d.id for d in registry.all()}
    assert "hetzner-rmthz" in ids
    assert "windows-desktop" in ids
    assert registry.get("hetzner-rmthz").kind is DeviceKind.APLEXER_HOST
    assert registry.get("windows-desktop").native_aplexer is False
    assert registry.get("windows-desktop").outbound_ssh_only is True


def test_unknown_device_and_alias():
    registry = DeviceRegistry.load(EXAMPLE)
    with pytest.raises(UnknownDevice) as unknown:
        registry.get("laptop-unregistered")
    assert unknown.value.code == "unknown_device"
    with pytest.raises(UnregisteredAlias) as alias:
        registry.require_alias("not-in-ssh-config")
    assert alias.value.code == "unregistered_alias"


def test_existing_ssh_alias_is_allowlisted():
    registry = DeviceRegistry.load(EXAMPLE)
    device = registry.require_alias("hetzner")
    assert device.id == "hetzner-rmthz"
    assert device.can_run_aplexer() is True

def test_duplicate_device_id_raises():
    registry = DeviceRegistry.load(EXAMPLE)
    device = registry.get("hetzner-rmthz")
    with pytest.raises(ValueError, match="Duplicate device ID: hetzner-rmthz"):
        DeviceRegistry([device, device])

def test_duplicate_ssh_alias_raises():
    registry = DeviceRegistry.load(EXAMPLE)
    device1 = registry.get("hetzner-rmthz")
    from coordination.device_registry import Device, DeviceKind
    device2 = Device(
        id="some-other-id",
        kind=DeviceKind.APLEXER_HOST,
        ssh_alias=device1.ssh_alias,
        hostname="other",
        ssh_user="user",
        aplexer_bin=None,
        workspace_roots=(),
        role="worker",
        native_aplexer=False,
        outbound_ssh_only=False,
    )
    with pytest.raises(ValueError, match=f"Duplicate SSH alias: {device1.ssh_alias}"):
        DeviceRegistry([device1, device2])
