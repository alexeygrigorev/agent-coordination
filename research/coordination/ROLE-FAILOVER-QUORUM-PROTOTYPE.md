# Cross-host majority consensus authority and fenced restore prototype

## Architecture

This prototype implements a basic Quorum-based lease authority over standard SQLite files using an approach inspired by Paxos. It assumes an odd number of hosts (e.g. 3).

`QuorumNode` handles the single-host SQLite persistence of terms and leases. It supports `prepare` (Phase 1) and `propose` (Phase 2).
`QuorumClient` acts as the candidate, trying to acquire a lease.

## Features demonstrated:

- **Majority votes for granting roles:** The client requires a majority (e.g. 2 out of 3) `prepare` and `propose` responses to successfully acquire a lease.
- **Partitioned minorities cannot grant roles:** A candidate communicating with only 1 out of 3 nodes will fail to acquire the lease.
- **Majority can recover one failed authority host:** If 1 host is down or lost, the remaining 2 hosts are sufficient to grant and renew leases.
- **Consumer fencing:** `fenced_operation` checks that the client's lease is still active and recognized by a majority before executing side effects.
- **Fenced restore rejects old authority:** If a node is restored from a backup (e.g. an empty or older term state), a client cannot use it to re-acquire an old lease because the other nodes remember that the term has advanced. The consumer term protects against regression.

## Files
- Implementation: `coordination/quorum_authority.py`
- Tests: `tests/test_quorum_authority.py` (Passes 5/5)
