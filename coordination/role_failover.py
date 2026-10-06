"""Durable project role election authority, called by existing supervisor ticks.

This authority is single-host SQLite. Partitioned clients fail closed; no local
fallback election is permitted. Epochs must be enforced by every launch consumer.
"""
import json
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path


class Fenced(RuntimeError):
    pass


class RoleAuthority:
    def __init__(self, path, clock=time.time, boot_id=None):
        self.path = str(path)
        self.clock = clock
        self.boot_id = boot_id or Path("/proc/sys/kernel/random/boot_id").read_text().strip()
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self._tx() as db:
            db.executescript('''
            CREATE TABLE IF NOT EXISTS authority_meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS projects(id TEXT PRIMARY KEY, parent TEXT REFERENCES projects(id));
            CREATE TABLE IF NOT EXISTS agents(id TEXT PRIMARY KEY, host TEXT NOT NULL,
              generation TEXT NOT NULL, seen REAL NOT NULL, ready INTEGER NOT NULL,
              draft INTEGER NOT NULL, quota INTEGER NOT NULL, priority INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS candidates(project TEXT NOT NULL, role TEXT NOT NULL,
              agent TEXT NOT NULL, PRIMARY KEY(project,role,agent));
            CREATE TABLE IF NOT EXISTS roles(project TEXT NOT NULL, role TEXT NOT NULL,
              holder TEXT, generation TEXT, epoch INTEGER NOT NULL DEFAULT 0,
              expires REAL NOT NULL DEFAULT 0, check_due REAL NOT NULL DEFAULT 0,
              standup_due REAL, suspect_since REAL,
              PRIMARY KEY(project,role));
            CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY AUTOINCREMENT,
              project TEXT NOT NULL, role TEXT NOT NULL, kind TEXT NOT NULL,
              epoch INTEGER NOT NULL, payload TEXT NOT NULL, created REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS activation_receipts(project TEXT NOT NULL, role TEXT NOT NULL,
              epoch INTEGER NOT NULL, role_ack TEXT NOT NULL, first_action TEXT NOT NULL,
              PRIMARY KEY(project,role,epoch));
            CREATE TABLE IF NOT EXISTS startup_plans(project TEXT NOT NULL, role TEXT NOT NULL, task TEXT NOT NULL, PRIMARY KEY(project,role));
            CREATE TABLE IF NOT EXISTS actions(key TEXT PRIMARY KEY, project TEXT NOT NULL,
              role TEXT NOT NULL, epoch INTEGER NOT NULL, payload TEXT NOT NULL);
            ''')
            old = db.execute("SELECT value FROM authority_meta WHERE key='boot'").fetchone()
            if old and old[0] != self.boot_id:
                db.execute('UPDATE roles SET expires=0,suspect_since=NULL')
                db.execute("DELETE FROM authority_meta WHERE key='last_clock'")
            db.execute("INSERT OR REPLACE INTO authority_meta VALUES('boot',?)", (self.boot_id,))
        Path(self.path).chmod(0o600)

    @contextmanager
    def _tx(self):
        db = sqlite3.connect(self.path, timeout=5, isolation_level=None)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        db.execute('BEGIN IMMEDIATE')
        try:
            if db.execute("SELECT 1 FROM sqlite_master WHERE name='authority_meta'").fetchone():
                last = db.execute("SELECT value FROM authority_meta WHERE key='last_clock'").fetchone()
                if last and self.clock() < float(last[0]):
                    raise Fenced('authority clock rollback; leases unavailable until clock catches up')
                db.execute("INSERT OR REPLACE INTO authority_meta VALUES('last_clock',?)", (str(self.clock()),))
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def _event(self, db, project, role, kind, epoch, payload):
        db.execute('INSERT INTO events(project,role,kind,epoch,payload,created) VALUES(?,?,?,?,?,?)',
                   (project, role, kind, epoch, json.dumps(payload), self.clock()))

    def configure(self, project, role, candidates, parent=None, standup_due=None):
        """Explicit project membership is required; no implicit cross-project takeover."""
        with self._tx() as db:
            if parent and not db.execute('SELECT 1 FROM projects WHERE id=?', (parent,)).fetchone():
                raise ValueError('unknown parent project')
            db.execute('INSERT OR IGNORE INTO projects VALUES(?,?)', (project, parent))
            db.execute('INSERT OR IGNORE INTO roles(project,role,standup_due) VALUES(?,?,?)',
                       (project, role, standup_due))
            db.execute('DELETE FROM candidates WHERE project=? AND role=?', (project, role))
            db.executemany('INSERT INTO candidates VALUES(?,?,?)',
                           [(project, role, actor) for actor in candidates])

    def observe(self, actor, host, generation, *, ready, draft, quota_ok, priority=100):
        """Runtime adapter supplies genuine identity/readiness/quota observations.

        Observation alone never renews role liveness or proves useful progress.
        """
        if not actor or not host or not generation:
            raise ValueError('identity, host and execution generation required')
        with self._tx() as db:
            db.execute('INSERT OR REPLACE INTO agents VALUES(?,?,?,?,?,?,?,?)',
                       (actor, host, generation, self.clock(), bool(ready), bool(draft),
                        bool(quota_ok), priority))

    def _get(self, db, project, role):
        row = db.execute('SELECT * FROM roles WHERE project=? AND role=?', (project, role)).fetchone()
        if row is None:
            raise ValueError('unconfigured project role')
        return row

    def _valid(self, db, project, role, actor, generation, epoch):
        row = self._get(db, project, role)
        if (row['holder'], row['generation'], row['epoch']) != (actor, generation, epoch):
            raise Fenced('stale role identity or epoch')
        observed=db.execute('SELECT generation FROM agents WHERE id=?',(actor,)).fetchone()
        if not observed or observed['generation']!=generation:
            raise Fenced('runtime generation has changed')
        if (row['expires'] <= self.clock() or row['check_due']+120 <= self.clock()
                or (row['standup_due'] is not None and row['standup_due']+120 <= self.clock())
                or row['suspect_since'] is not None):
            raise Fenced('expired or suspected lease; diagnose before restoring authority')
        return row

    def renew(self, project, role, actor, generation, epoch, *, ttl=180):
        with self._tx() as db:
            self._valid(db, project, role, actor, generation, epoch)
            db.execute('UPDATE roles SET expires=? WHERE project=? AND role=?',
                       (self.clock()+ttl, project, role))

    def complete_check(self, project, role, actor, generation, epoch, *, evidence,
                       interval=1800, next_standup=None):
        """Only an actual completed periodic/standup check extends check deadline."""
        if not evidence:
            raise ValueError('completed-check evidence required')
        with self._tx() as db:
            self._valid(db, project, role, actor, generation, epoch)
            db.execute('UPDATE roles SET check_due=?,standup_due=? WHERE project=? AND role=?',
                       (self.clock()+interval, next_standup, project, role))
            self._event(db, project, role, 'check_completed', epoch, {'evidence': evidence})

    def tick(self, project, role, *, ttl=180, check_interval=1800,
             observation_ttl=60, diagnosis_grace=120):
        """Deterministic election after missed lease/check, with durable sync probe.

        Every standby calls this against the SAME authority. No clock-only
        role transfer of file/task ownership: request separate fenced recovery.
        """
        now = self.clock()
        with self._tx() as db:
            old = self._get(db, project, role)
            incumbent=db.execute('SELECT generation FROM agents WHERE id=?',(old['holder'],)).fetchone()
            generation_changed=incumbent and incumbent['generation']!=old['generation']
            missed = old['holder'] and (generation_changed or (old['expires'] <= now or old['check_due']+120 <= now
                       or (old['standup_due'] is not None and old['standup_due']+120 <= now)))
            if old['holder'] and not missed:
                return {'state': 'healthy', 'holder': old['holder'], 'generation': old['generation'], 'epoch': old['epoch']}
            if missed and old['suspect_since'] is None:
                db.execute('UPDATE roles SET suspect_since=? WHERE project=? AND role=?', (now, project, role))
                self._event(db, project, role, 'sync_probe', old['epoch'],
                            {'recipient': old['holder'], 'generation': old['generation'],
                             'request': 'Diagnose runtime, busy/draft, quota, service and cursor; preserve tasks'})
                return {'state': 'diagnosing', 'epoch': old['epoch']}
            if missed and now < old['suspect_since']+diagnosis_grace:
                return {'state': 'diagnosing', 'epoch': old['epoch']}
            choices = db.execute('''SELECT a.* FROM agents a JOIN candidates c ON c.agent=a.id
                WHERE c.project=? AND c.role=? AND a.seen>? AND a.ready=1 AND a.draft=0 AND a.quota=1
                AND NOT EXISTS(SELECT 1 FROM roles r WHERE r.holder=a.id AND r.expires>?
                  AND (r.role='principal' OR r.role='coordinator') AND NOT(r.project=? AND r.role=?))
                ORDER BY a.priority,a.id''', (project,role,now-observation_ttl,now,project,role)).fetchall()
            # A suspected generation cannot elect itself through a status heartbeat.
            choices = [a for a in choices if (a['id'],a['generation']) != (old['holder'],old['generation'])]
            if not choices:
                self._event(db, project, role, 'replacement_required', old['epoch'],
                            {'owner_role': 'standby', 'retain_busy_or_draft': True})
                return {'state': 'replacement_required', 'epoch': old['epoch']}
            new = choices[0]
            epoch = old['epoch']+1
            db.execute('''UPDATE roles SET holder=?,generation=?,epoch=?,expires=?,check_due=?,
                suspect_since=NULL,standup_due=? WHERE project=? AND role=?''',
                (new['id'],new['generation'],epoch,now+ttl,now+check_interval,
                 now+diagnosis_grace if old['standup_due'] is not None and old['standup_due']<=now else old['standup_due'],
                 project,role))
            # A promoted head relinquishes role authority, not in-flight file custody.
            if role == 'principal':
                heads = db.execute("SELECT * FROM roles WHERE holder=? AND role LIKE 'head:%'", (new['id'],)).fetchall()
                for head in heads:
                    db.execute('UPDATE roles SET holder=NULL,generation=NULL,epoch=epoch+1,expires=0 WHERE project=? AND role=?',
                               (head['project'],head['role']))
                    self._event(db,head['project'],head['role'],'head_backfill_required',head['epoch']+1,
                                {'promoted':new['id'],'preserve_task_custody':True})
            self._event(db, project, role, 'elected', epoch,
                        {'holder':new['id'],'host':new['host'],'generation':new['generation'],
                         'previous':old['holder'],'reconcile_before_writes':True})
            return {'state':'elected','holder':new['id'],'generation':new['generation'],'epoch':epoch}

    def activation(self, project, role, actor, generation, epoch, *, role_ack=None, first_action=None):
        """Trusted adapter records authenticated semantic ACK + actual first tool.

        These cannot be inferred from PID, queue acceptance, or source tests.
        """
        with self._tx() as db:
            self._valid(db,project,role,actor,generation,epoch)
            if role_ack is not None or first_action is not None:
                if not role_ack or not first_action:
                    raise ValueError('both exact semantic role ACK and first-tool receipt required')
                old=db.execute('SELECT * FROM activation_receipts WHERE project=? AND role=? AND epoch=?',
                               (project,role,epoch)).fetchone()
                if old and (old['role_ack'],old['first_action'])!=(role_ack,first_action):
                    raise Fenced('conflicting activation receipts')
                db.execute('INSERT OR IGNORE INTO activation_receipts VALUES(?,?,?,?,?)',
                           (project,role,epoch,role_ack,first_action))
            row=db.execute('SELECT * FROM activation_receipts WHERE project=? AND role=? AND epoch=?',
                           (project,role,epoch)).fetchone()
            return dict(row) if row else {'state':'pending_role_ack_and_first_action'}

    def startup_plan(self, project, role, task=None):
        """Persist owner-approved recovery task before election for crash retries."""
        with self._tx() as db:
            self._get(db,project,role)
            if task is not None:
                body=json.dumps(task,sort_keys=True)
                old=db.execute('SELECT task FROM startup_plans WHERE project=? AND role=?',(project,role)).fetchone()
                if old and old[0]!=body:
                    raise Fenced('existing startup plan requires explicit ownership reconciliation')
                db.execute('INSERT OR IGNORE INTO startup_plans VALUES(?,?,?)',(project,role,body))
            row=db.execute('SELECT task FROM startup_plans WHERE project=? AND role=?',(project,role)).fetchone()
            return json.loads(row[0]) if row else None

    def sync_response(self, project, role, actor, generation, epoch, *, envelope_id, evidence):
        """Exact semantic sync response can clear suspicion only within live deadlines.

        It cannot renew an expired epoch or stand in for a completed periodic check.
        """
        if not envelope_id or not evidence:
            raise ValueError('exact envelope and semantic runtime evidence required')
        with self._tx() as db:
            row = self._get(db, project, role)
            if (row['holder'],row['generation'],row['epoch']) != (actor,generation,epoch):
                raise Fenced('stale sync response')
            if (row['expires'] <= self.clock() or row['check_due']+120 <= self.clock()
                    or (row['standup_due'] is not None and row['standup_due']+120 <= self.clock())):
                raise Fenced('semantic response cannot waive missed deadlines')
            db.execute('UPDATE roles SET suspect_since=NULL WHERE project=? AND role=?',(project,role))
            self._event(db,project,role,'sync_response',epoch,{'envelope_id':envelope_id,'evidence':evidence})

    def guarded_effect(self, project, role, actor, generation, epoch, key, payload, effect):
        """Serialize control-plane enqueue with election; callback MUST dedup key.

        A crash after callback before commit may retry it. External effects require
        their own durable idempotency key; this is not exactly-once execution.
        """
        with self._tx() as db:
            self._valid(db,project,role,actor,generation,epoch)
            observed = db.execute('SELECT * FROM agents WHERE id=?',(actor,)).fetchone()
            if not observed or observed['seen']<=self.clock()-60 or not observed['quota'] or observed['draft']:
                raise Fenced('fresh quota and safe runtime required')
            body=json.dumps(payload,sort_keys=True)
            old=db.execute('SELECT * FROM actions WHERE key=?',(key,)).fetchone()
            if old:
                if (old['project'],old['role'],old['epoch'],old['payload'])!=(project,role,epoch,body):
                    raise Fenced('conflicting intent')
                return {'state':'already_enqueued'}
            result=effect(key,payload)
            db.execute('INSERT INTO actions VALUES(?,?,?,?,?)',(key,project,role,epoch,body))
            return result

    def submit_action(self, project, role, actor, generation, epoch, key, payload):
        """Durable fenced intent. Consumer must claim with authorize before execution."""
        with self._tx() as db:
            self._valid(db,project,role,actor,generation,epoch)
            observed = db.execute('SELECT * FROM agents WHERE id=?', (actor,)).fetchone()
            if observed is None or observed['seen'] <= self.clock()-60 or not observed['quota'] or observed['draft']:
                raise Fenced('fresh quota and draft-safe runtime required for new dispatch')
            old = db.execute('SELECT * FROM actions WHERE key=?',(key,)).fetchone()
            body = json.dumps(payload,sort_keys=True)
            if old:
                if (old['project'],old['role'],old['epoch'],old['payload']) != (project,role,epoch,body):
                    raise Fenced('idempotency key conflicts with previous intent')
                return False
            db.execute('INSERT INTO actions VALUES(?,?,?,?,?)',(key,project,role,epoch,body))
            return True

    def authorize(self, project, role, actor, generation, epoch):
        """Must be checked at mutation/launcher commit, never cached across outages."""
        with self._tx() as db:
            self._valid(db,project,role,actor,generation,epoch)
            return True

    def events(self):
        with self._tx() as db:
            return [dict(row) for row in db.execute('SELECT * FROM events ORDER BY id')]
