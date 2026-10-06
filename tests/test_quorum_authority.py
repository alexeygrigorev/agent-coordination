import pytest
import time
import shutil
from pathlib import Path
from coordination.quorum_authority import QuorumNode, QuorumClient, Fenced

@pytest.fixture
def nodes(tmp_path):
    n1 = QuorumNode(tmp_path / 'node1.db', 'node1')
    n2 = QuorumNode(tmp_path / 'node2.db', 'node2')
    n3 = QuorumNode(tmp_path / 'node3.db', 'node3')
    return [n1, n2, n3]

def test_majority_grants_lease(nodes):
    client = QuorumClient(nodes, 'candidateA')
    res = client.acquire_lease()
    assert res['status'] == 'acquired'
    assert res['term'] == 1
    
    # Verify we can execute a fenced operation
    result = client.fenced_operation(lambda: "success")
    assert result == "success"

def test_partitioned_minority_cannot_grant_role(nodes):
    # Simulate partition: Candidate B can only talk to node 1
    # Note that a single node is 1 out of 3, so majority (2) is not met
    client = QuorumClient([nodes[0]], 'candidateB')
    # Because client knows there are 3 nodes?
    # Wait, QuorumClient takes `nodes` as the list of known nodes, so if we pass [nodes[0]], it thinks majority is 1.
    # We should instantiate client with all nodes, but let's mock network failure for n2 and n3.
    client = QuorumClient(nodes, 'candidateB')
    
    # Hack to simulate partition: remove nodes 1 and 2 from client's access
    client.nodes = [nodes[0]]
    # we need to keep majority expectation to 2.
    client.majority = 2
    
    with pytest.raises(Fenced):
        client.acquire_lease()

def test_majority_can_recover_failed_host(nodes):
    client = QuorumClient(nodes, 'candidateA')
    client.acquire_lease()
    
    # Simulate node3 dying and node1/node2 still alive
    active_nodes = [nodes[0], nodes[1]]
    client2 = QuorumClient(nodes, 'candidateA') # same candidate can renew
    client2.nodes = active_nodes
    client2.majority = 2
    
    # Advance clock to expire previous lease
    client2.clock = lambda: time.time() + 200
    for n in active_nodes:
        n.clock = client2.clock
        
    res = client2.acquire_lease()
    assert res['status'] == 'acquired'

def test_fenced_restore_rejects_old_authority(tmp_path):
    n1_path = tmp_path / 'n1.db'
    n2_path = tmp_path / 'n2.db'
    n3_path = tmp_path / 'n3.db'
    
    n1 = QuorumNode(n1_path, 'node1')
    n2 = QuorumNode(n2_path, 'node2')
    n3 = QuorumNode(n3_path, 'node3')
    
    clientA = QuorumClient([n1, n2, n3], 'candidateA')
    clientA.acquire_lease(lease_duration=10)
    
    # Candidate B acquires lease after A expires
    clock_fn = lambda: time.time() + 20
    n1.clock = n2.clock = n3.clock = clientA.clock = clock_fn
    
    clientB = QuorumClient([n1, n2, n3], 'candidateB', clock=clock_fn)
    clientB.acquire_lease(lease_duration=10)
    
    # Now restore node 1 from a backup (simulated by re-initializing)
    n1_restored = QuorumNode(tmp_path / 'n1_restored.db', 'node1') 
    
    # A tries to use n1_restored and n2 to get a lease.
    # n2 knows the term is at least 2.
    clientA2 = QuorumClient([n1_restored, n2, n3], 'candidateA', clock=clock_fn)
    clientA2.nodes = [n1_restored, n2] # n3 partitioned
    clientA2.majority = 2
    
    with pytest.raises(Fenced):
        clientA2.acquire_lease()

def test_consumer_term_rejection(nodes):
    clientA = QuorumClient(nodes, 'candidateA')
    clientA.acquire_lease()
    
    # A does operation
    assert clientA.fenced_operation(lambda: True)
    
    # B takes over
    clientB = QuorumClient(nodes, 'candidateB')
    clock_fn = lambda: time.time() + 200
    for n in nodes: n.clock = clock_fn
    clientB.clock = clock_fn
    clientB.acquire_lease()
    
    # A tries to do fenced operation without renewing
    clientA.clock = clock_fn
    with pytest.raises(Fenced, match="Lost majority lease"):
        clientA.fenced_operation(lambda: True)
