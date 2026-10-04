# Computer topology

Topology is documented in `examples/devices.example.json` and loaded at
runtime. It is not hardcoded to two hosts.

| Device ID | Kind | Native aplexer | SSH | Role |
| --- | --- | --- | --- | --- |
| `hetzner-rmthz` | aplexer-host | yes, installed CLI 0.1.9 | existing alias `hetzner` | remote execution |
| `windows-desktop` | ssh-client-host | no | outbound `ssh.exe` only | user desktop |
| future hosts | registered first | only if an installed aplexer exists | allowlisted alias | add via registry |

Adding a third computer requires an explicit registry entry: device ID,
kind, SSH alias or outbound-only flag, hostname, whether native aplexer
exists, and workspace roots. Unregistered hostnames are rejected.

## Directions

Windows-initiated authenticated SSH carries both directions. The desktop
has no inbound SSH server and no local aplexer. Hetzner cannot open a
connection to Windows. A Windows client invokes `aplexer` on Hetzner and
polls a namespaced mailbox. The SSH bridge identity is not the originating
Windows agent. Do not invent a native Windows aplexer session ID.

## What is not acceptance

`cloudflare-agent-git/scripts/orchestrator-channel.py` is a root SSH
mailbox wrapper. It is the baseline the desktop already uses. A successful
wrapper poll is not native cross-host routing, not catalog-at-send-time
resolution, and not this product's acceptance test.

Localhost and fake-transport unit tests in `tests/` prove protocol
separation and guards. They are not two-computer proof.
