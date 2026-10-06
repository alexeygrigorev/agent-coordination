import json
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path

class Fenced(RuntimeError):
    pass

class QuorumNode:
    """A single node in a majority consensus authority."""
    def __init__(self, path, node_id, clock=time.time):
        self.path = str(path)
        self.node_id = node_id
        self.clock = clock
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self._tx() as db:
            db.executescript('''
            CREATE TABLE IF NOT EXISTS state(
                id INTEGER PRIMARY KEY,
                current_term INTEGER NOT NULL DEFAULT 0,
                voted_for TEXT,
                lease_holder TEXT,
                lease_expires REAL NOT NULL DEFAULT 0
            );
            INSERT OR IGNORE INTO state(id) VALUES(1);
            ''')
        Path(self.path).chmod(0o600)

    @contextmanager
    def _tx(self):
        db = sqlite3.connect(self.path, timeout=5, isolation_level=None)
        db.row_factory = sqlite3.Row
        db.execute('BEGIN IMMEDIATE')
        try:
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def _get_state(self, db):
        return dict(db.execute('SELECT * FROM state WHERE id=1').fetchone())

    def prepare(self, term):
        """Phase 1: Promise not to accept requests with term < proposed term."""
        with self._tx() as db:
            state = self._get_state(db)
            if term <= state['current_term']:
                return {'granted': False, 'term': state['current_term'], 'lease_holder': state['lease_holder'], 'lease_expires': state['lease_expires']}
            
            db.execute('UPDATE state SET current_term=?, voted_for=NULL WHERE id=1', (term,))
            return {'granted': True, 'term': term, 'lease_holder': state['lease_holder'], 'lease_expires': state['lease_expires']}

    def propose(self, term, candidate, lease_duration):
        """Phase 2: Accept the lease if term matches current_term."""
        now = self.clock()
        with self._tx() as db:
            state = self._get_state(db)
            if term < state['current_term']:
                return {'granted': False, 'term': state['current_term']}
            
            # If there is a valid lease for someone else, reject
            if state['lease_holder'] and state['lease_holder'] != candidate and state['lease_expires'] > now:
                return {'granted': False, 'term': state['current_term'], 'conflict': 'active_lease'}
            
            db.execute('UPDATE state SET current_term=?, voted_for=?, lease_holder=?, lease_expires=? WHERE id=1',
                       (term, candidate, candidate, now + lease_duration))
            return {'granted': True, 'term': term}
            
    def get_lease(self):
        with self._tx() as db:
            state = self._get_state(db)
            return {'lease_holder': state['lease_holder'], 'lease_expires': state['lease_expires'], 'term': state['current_term']}

class QuorumClient:
    """Client that coordinates with a majority of nodes to acquire/renew a lease."""
    def __init__(self, nodes, candidate_id, clock=time.time):
        self.nodes = nodes
        self.candidate_id = candidate_id
        self.clock = clock
        self.majority = (len(nodes) // 2) + 1
        self.current_term = 0

    def acquire_lease(self, lease_duration=180, retries=3):
        for attempt in range(retries):
            self.current_term += 1
            term = self.current_term
            
            # Phase 1: Prepare
            prepare_granted = 0
            active_leases = []
            max_learned_term = self.current_term
            
            for node in self.nodes:
                try:
                    res = node.prepare(term)
                    if res['granted']:
                        prepare_granted += 1
                        if res['lease_holder'] and res['lease_expires'] > self.clock() and res['lease_holder'] != self.candidate_id:
                            active_leases.append(res)
                    else:
                        if res['term'] > max_learned_term:
                            max_learned_term = res['term']
                except Exception:
                    pass # network/partition failure simulation
            
            if prepare_granted < self.majority:
                if max_learned_term >= self.current_term:
                    self.current_term = max_learned_term
                    continue # Retry with higher term
                raise Fenced('Failed to acquire majority for prepare phase')
                
            if active_leases:
                raise Fenced('Another candidate holds an active lease')
                
            # Phase 2: Propose
            propose_granted = 0
            for node in self.nodes:
                try:
                    res = node.propose(term, self.candidate_id, lease_duration)
                    if res['granted']:
                        propose_granted += 1
                except Exception:
                    pass
                    
            if propose_granted < self.majority:
                raise Fenced('Failed to acquire majority for propose phase')
                
            return {'status': 'acquired', 'term': term, 'candidate': self.candidate_id}
            
        raise Fenced('Failed to acquire lease after retries')

    def fenced_operation(self, operation_fn):
        """Consumer fencing: ensures we still hold the lease on a majority before doing side-effects."""
        now = self.clock()
        valid_leases = 0
        for node in self.nodes:
            try:
                res = node.get_lease()
                if res['lease_holder'] == self.candidate_id and res['term'] == self.current_term and res['lease_expires'] > now:
                    valid_leases += 1
            except Exception:
                pass
                
        if valid_leases < self.majority:
            raise Fenced('Lost majority lease, operation fenced')
            
        return operation_fn()

