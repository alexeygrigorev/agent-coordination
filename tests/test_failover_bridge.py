from coordination.bus import FileBus
from coordination.failover_bridge import FailoverBridge, LauncherQueue
from coordination.role_failover import RoleAuthority,Fenced
import pytest


def test_real_bus_durable_sync_and_replay(tmp_path):
    now=[1000]
    a=RoleAuthority(tmp_path/'roles.db',lambda:now[0])
    bus=FileBus(tmp_path/'bus')
    watcher,token=bus.register(agent_name='standby',device_id='hetzner',project_id='p')
    old,_=bus.register(agent_name='old',device_id='desktop',project_id='p')
    backup,_=bus.register(agent_name='backup',device_id='hetzner',project_id='p')
    a.configure('p','coordinator',['old','backup'])
    a.observe('old','desktop','g1',ready=True,draft=False,quota_ok=True,priority=0)
    a.observe('backup','hetzner','g1',ready=True,draft=False,quota_ok=True)
    bridge=FailoverBridge(a,bus,sender_id=watcher.identity_id,token=token,
        recipients={'old':old.identity_id,'backup':backup.identity_id,watcher.identity_id:watcher.identity_id},
        launcher_queue=lambda key,task:{'key':key})
    assert bridge.tick('p','coordinator')['holder']=='old'
    now[0]+=181
    result=bridge.tick('p','coordinator')
    sync=[r for r in result['receipts'] if r['event_id']==2][0]
    assert result['state']=='diagnosing'
    assert bridge.publish_events()[1]['envelope_id']==sync['envelope_id']
    now[0]+=121
    a.observe('backup','hetzner','g1',ready=True,draft=False,quota_ok=True)
    result=bridge.tick('p','coordinator',replacement_task={'id':'restore-coordinator','payload':{}})
    assert result['holder']=='backup'
    assert result['launch']['key']=='role-start:p:coordinator:2'
    with pytest.raises(Fenced):a.authorize('p','coordinator','old','g1',1)


def test_no_guessed_recipient_or_raw_launch(tmp_path):
    a=RoleAuthority(tmp_path/'roles.db')
    a.configure('p','principal',['a'])
    a.observe('a','hetzner','g1',ready=True,draft=False,quota_ok=True)
    bus=FileBus(tmp_path/'bus');who,token=bus.register(agent_name='standby',device_id='hetzner',project_id='p')
    bridge=FailoverBridge(a,bus,sender_id=who.identity_id,token=token,recipients={},launcher_queue=lambda *_:pytest.fail('no launch'))
    result=bridge.tick('p','principal',replacement_task={'id':'planned','payload':{}})
    assert result['receipts'][0]['state']=='pending_delivery'
    assert 'launch' not in result


def test_launcher_cli_validates_route_and_dedup_contract(tmp_path,monkeypatch):
    calls=[]
    class Result:stdout='{"id":"restore"}'
    def run(args,**kwargs):calls.append(args);return Result()
    monkeypatch.setattr('coordination.failover_bridge.subprocess.run',run)
    queue=LauncherQueue(['python3','-m','launcher.cli','--config-dir',str(tmp_path)],tmp_path)
    with pytest.raises(ValueError):queue('key',{'id':'restore','payload':{}})
    task={'id':'restore','payload':{'owner':'backup','cwd':str(tmp_path),'timeout':300,'goal':'recover periodic coordinator',
                                  'model_requirements':{'model':'authorized-route'}}}
    assert queue('key',task)['state']=='queued'
    assert calls[0][calls[0].index('--key')+1]=='key'
    assert 'submit' in calls[0] and 'run' not in calls[0]


def test_startup_retry_survives_election_and_queue_failure(tmp_path):
    now=[1000];a=RoleAuthority(tmp_path/'roles.db',lambda:now[0])
    a.configure('p','principal',['a']);a.observe('a','hetzner','g1',ready=True,draft=False,quota_ok=True)
    bus=FileBus(tmp_path/'bus');who,token=bus.register(agent_name='a',device_id='hetzner',project_id='p')
    calls=[]
    def flaky(key,task):
        calls.append(key)
        if len(calls)==1:raise RuntimeError('lost before queue receipt')
        return {'state':'queued'}
    bridge=FailoverBridge(a,bus,sender_id=who.identity_id,token=token,
                         recipients={'a':who.identity_id},launcher_queue=flaky)
    with pytest.raises(RuntimeError):bridge.tick('p','principal',replacement_task={'id':'replacement','payload':{}})
    assert bridge.tick('p','principal')['launch']['state']=='queued'
    assert calls==['role-start:p:principal:1']*2
    result=bridge.tick('p','principal')
    assert result['launch']['state']=='already_enqueued'
    assert result['activation']['state']=='pending_role_ack_and_first_action'
    a.activation('p','principal','a','g1',1,role_ack='envelope-semantic-ack',first_action='model-tool-receipt')
    assert bridge.tick('p','principal')['activation']['first_action']=='model-tool-receipt'
