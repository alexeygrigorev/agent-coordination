import concurrent.futures
import pytest
from coordination.role_failover import Fenced, RoleAuthority


@pytest.fixture
def authority(tmp_path):
    now = [1000.0]
    return RoleAuthority(tmp_path/'roles.db', lambda:now[0]), now


def enroll(a, actor, generation='g1', priority=1, **extra):
    a.observe(actor,'hetzner',generation,ready=True,draft=False,quota_ok=True,priority=priority,**extra)


def elect(a,role='principal'):
    return a.tick('project',role)


def test_concurrent_candidates_one_epoch(authority):
    a,now=authority
    a.configure('project','principal',['a','b'])
    enroll(a,'b');enroll(a,'a')
    with concurrent.futures.ThreadPoolExecutor(8) as pool:
        results=list(pool.map(lambda _:elect(a),range(8)))
    assert sum(r['state']=='elected' for r in results)==1
    assert {r['epoch'] for r in results}=={1}
    assert {r['holder'] for r in results}=={'a'}


def test_expired_principal_diagnose_promote_backfill_fence(authority):
    a,now=authority
    a.configure('project','principal',['old','head'])
    a.configure('project','head:bus',['head'])
    enroll(a,'old',priority=0);enroll(a,'head')
    assert elect(a)['holder']=='old'
    assert elect(a,'head:bus')['holder']=='head'
    now[0]+=181
    enroll(a,'head')
    assert elect(a)['state']=='diagnosing'
    assert a.events()[-1]['kind']=='sync_probe'
    with pytest.raises(Fenced):a.authorize('project','principal','old','g1',1)
    now[0]+=121;enroll(a,'head')
    assert elect(a)['holder']=='head'
    assert elect(a)['epoch']==2
    assert any(e['kind']=='head_backfill_required' for e in a.events())
    with pytest.raises(Fenced):a.renew('project','principal','old','g1',1)
    with pytest.raises(Fenced):a.authorize('project','head:bus','head','g1',1)


def test_periodic_check_missing_even_with_renewals(authority):
    a,now=authority
    a.configure('project','coordinator',['desktop','remote'])
    enroll(a,'desktop',priority=0);enroll(a,'remote')
    elect(a,'coordinator')
    for _ in range(17):
        now[0]+=100;a.renew('project','coordinator','desktop','g1',1)
    now[0]+=221
    with pytest.raises(Fenced):a.renew('project','coordinator','desktop','g1',1)
    assert elect(a,'coordinator')['state']=='diagnosing'
    now[0]+=121;enroll(a,'remote')
    assert elect(a,'coordinator')['holder']=='remote'


def test_busy_draft_quota_unknown_and_stale_candidates_block(authority):
    a,now=authority
    a.configure('project','principal',['busy','draft','quota','stale'])
    a.observe('busy','hetzner','g1',ready=False,draft=False,quota_ok=True)
    a.observe('draft','hetzner','g1',ready=True,draft=True,quota_ok=True)
    a.observe('quota','hetzner','g1',ready=True,draft=False,quota_ok=False)
    enroll(a,'stale');now[0]+=61
    assert elect(a)['state']=='replacement_required'


def test_generation_rejoin_and_idempotency_conflict(authority):
    a,now=authority
    a.configure('project','principal',['a']);enroll(a,'a');elect(a)
    assert a.submit_action('project','principal','a','g1',1,'launch-task1',{'task':'task1'})
    assert not a.submit_action('project','principal','a','g1',1,'launch-task1',{'task':'task1'})
    with pytest.raises(Fenced):a.submit_action('project','principal','a','g1',1,'launch-task1',{'task':'task2'})
    now[0]+=181;assert elect(a)['state']=='diagnosing'
    now[0]+=121;enroll(a,'a','g2');assert elect(a)['epoch']==2
    with pytest.raises(Fenced):a.authorize('project','principal','a','g1',1)


def test_subprojects_do_not_implicitly_inherit_candidates(authority):
    a,now=authority
    a.configure('project','principal',['a'])
    a.configure('subproject','principal',['b'],parent='project')
    enroll(a,'a');enroll(a,'b');elect(a)
    assert a.tick('subproject','principal')['holder']=='b'


def test_standup_elects_remote_and_requires_new_completed_check(authority):
    a,now=authority
    a.configure('project','coordinator',['a','b'],standup_due=1050)
    enroll(a,'a',priority=0);enroll(a,'b');elect(a,'coordinator')
    now[0]=1171;assert elect(a,'coordinator')['state']=='diagnosing'
    now[0]+=121;enroll(a,'b');elect(a,'coordinator')
    a.complete_check('project','coordinator','b','g1',2,evidence='receipt-standup',next_standup=2000)
    assert elect(a,'coordinator')['state']=='healthy'


def test_partition_unavailable_authority_no_fallback(tmp_path):
    with pytest.raises(Exception):
        RoleAuthority('/dev/null/roles.db')


def test_fresh_quota_dispatch_and_empty_check_rejected(authority):
    a,now=authority
    a.configure('project','principal',['a']);enroll(a,'a');elect(a)
    with pytest.raises(ValueError):a.complete_check('project','principal','a','g1',1,evidence='')
    a.observe('a','hetzner','g1',ready=True,draft=False,quota_ok=False)
    with pytest.raises(Fenced):a.submit_action('project','principal','a','g1',1,'x',{})


def test_scheduled_completion_at_due_and_rollback(authority):
    a,now=authority
    a.configure('project','coordinator',['a']);enroll(a,'a');elect(a,'coordinator')
    now[0]+=100;a.renew('project','coordinator','a','g1',1,ttl=2000)
    now[0]=2800
    a.complete_check('project','coordinator','a','g1',1,evidence='scheduled-receipt')
    now[0]=2799
    with pytest.raises(Fenced):a.authorize('project','coordinator','a','g1',1)


def test_reboot_invalidates_lease(authority):
    a,now=authority
    a.configure('project','principal',['a']);enroll(a,'a');elect(a)
    b=RoleAuthority(a.path,lambda:now[0],boot_id='new-boot')
    with pytest.raises(Fenced):b.authorize('project','principal','a','g1',1)


def test_guarded_effect_race_one_enqueue(authority):
    a,now=authority
    a.configure('project','principal',['a']);enroll(a,'a');elect(a)
    calls=[]
    def invoke(_):
        return a.guarded_effect('project','principal','a','g1',1,'task1',{},lambda key,payload:calls.append(key))
    with concurrent.futures.ThreadPoolExecutor(8) as pool:list(pool.map(invoke,range(8)))
    assert calls==['task1']


def test_old_generation_fenced_before_lease_expiry(authority):
    a,now=authority
    a.configure('project','principal',['a']);enroll(a,'a');elect(a)
    enroll(a,'a','g2')
    with pytest.raises(Fenced):a.submit_action('project','principal','a','g1',1,'oldlaunch',{})
