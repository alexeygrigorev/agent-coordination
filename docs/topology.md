# Multi-Computer Topology and Device Admission Registry

Topology in `agent-coordination` is driven dynamically by an explicit **Device Registry** (loaded from `examples/devices.example.json` or a custom configuration file). It is designed for an arbitrary number of interconnected computers ($N \ge 1$), and is explicitly **not hardcoded to two hosts**.

## Device Registry Model

Every participating computer must be explicitly registered before participating in the coordination fabric. Unregistered device IDs and unregistered SSH aliases are rejected fail-closed at admission time (`UnknownDevice` / `UnregisteredAlias`).

### Registered Device Schema

| Field | Type | Description |
| --- | --- | --- |
| `id` | string (opaque) | Unique logical device identifier (e.g. `hetzner-rmthz`, `windows-desktop`, `mac-laptop`, `cluster-worker-01`). Never a raw IP. |
| `kind` | string enum | `aplexer-host` (runs native daemon/CLI) or `ssh-client-host` (outbound SSH client only, e.g. desktop). |
| `ssh_alias` | string \| null | Allowlisted host alias defined in `~/.ssh/config`. Must match existing authenticated config. `null` for outbound-only hosts. |
| `hostname` | string | Verified system hostname. |
| `ssh_user` | string | User account on the SSH target. |
| `aplexer_bin` | string \| null | Absolute path to installed `aplexer` binary (e.g. `/home/alexey/.local/bin/aplexer`). `null` if host has no local aplexer. |
| `workspace_roots` | list[string] | Confined file workspace prefixes permitted for cross-computer execution. |
| `native_aplexer` | boolean | Indicates whether the node runs a native `aplexer` session manager. |
| `outbound_ssh_only` | boolean | `true` if the node is behind NAT/firewall and cannot accept incoming connections. |
| `role` | string | Functional description (`remote-execution-host`, `user-desktop`, etc.). |

### Current Enrolled Topology (N=2 baseline in example, extensible to N hosts)

```json
{
  "devices": [
    {
      "id": "hetzner-rmthz",
      "kind": "aplexer-host",
      "ssh_alias": "hetzner",
      "hostname": "RMTHZ",
      "ssh_user": "alexey",
      "aplexer_bin": "/home/alexey/.local/bin/aplexer",
      "workspace_roots": ["/home/alexey/git"],
      "role": "remote-execution-host",
      "native_aplexer": true,
      "outbound_ssh_only": false
    },
    {
      "id": "windows-desktop",
      "kind": "ssh-client-host",
      "ssh_alias": null,
      "hostname": "windows-desktop",
      "ssh_user": "alexey",
      "aplexer_bin": null,
      "workspace_roots": ["work/agent-coordination"],
      "role": "user-desktop",
      "native_aplexer": false,
      "outbound_ssh_only": true
    }
  ]
}
```

## Scaling to N Computers

Enrolling a 3rd, 4th, or N-th computer (such as a MacBook Pro, secondary server, or Raspberry Pi) requires adding an entry to the registry JSON:
1. Define a unique `id` and appropriate `kind`.
2. Configure SSH alias in `~/.ssh/config` on the calling machines (if the machine accepts inbound SSH).
3. If the new machine runs native `aplexer`, specify `aplexer_bin` and `native_aplexer: true`.
4. If the new machine is an outbound-only desktop/laptop, set `native_aplexer: false` and `outbound_ssh_only: true`.

No code changes or database migrations are required to add hosts.

## Communication Directions and Routing Mechanics

Across the N-computer network:

1. **Host-to-Host (both native aplexer hosts)**:
   - Direct point-to-point dispatch over SSH.
   - Calling host uses `SshRelay` to execute `aplexer message send` on target host.
   - Catalog resolved dynamically at send time on the target host.

2. **Client-to-Host (Client has outbound SSH only, e.g. Windows desktop)**:
   - The client invokes remote `aplexer` commands on the allowlisted target host using `ssh.exe`.
   - The remote execution process runs under the SSH user's session (`bridge_device_id`).
   - The true author identity on the client is preserved as `originating_agent` in structured `--data`.
   - **Crucial Rule**: NEVER invent a native `aplexer` session UUID for client-only hosts (`session_id: null`).
   - **Crucial Rule**: The client never opens inbound ports and requires no inbound SSH server.

3. **Host-to-Client**:
   - Host nodes cannot initiate network connections into outbound-only client nodes.
   - Messages targeted at an `ssh-client-host` are placed into a durable outbox queue on the bridge host.
   - The client polls the bridge host periodically via `adapters/windows_client.py poll` or typed RPC.
   - Receipts, read ACKs, and semantic responses are sent as separate confirmed steps.

## What is NOT Acceptance

1. **Legacy Root Mailbox Wrapper**:
   - `cloudflare-agent-git/scripts/orchestrator-channel.py` is a baseline root SSH mailbox wrapper.
   - A successful poll of `orchestrator-channel.py` does not prove native aplexer catalog resolution, multi-computer namespacing, or two-computer acceptance.
2. **Localhost Pytest Execution**:
   - Pytest execution in `tests/` with `FakeTransport` verifies envelope formatting, cursor deduplication, and guard rejections.
   - Local unit tests do NOT count as cross-computer acceptance proof between distinct machines.
