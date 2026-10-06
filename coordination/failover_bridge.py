"""AgentBus/supervisor integration adapter. No timer/service is started here.

An existing supervisor calls tick, using authenticated bus credentials and fresh
runtime observations. The existing launcher owns admission, run, review/refill.
"""
import json
import subprocess
from pathlib import Path


class LauncherQueue:
    """Use maintained launcher CLI; never raw provider calls or nested launchers."""
    def __init__(self, command, cwd):
        self.command=list(command)
        self.cwd=str(cwd)

    def __call__(self, key, task):
        payload=dict(task['payload'])
        if not all(payload.get(k) for k in ('owner','cwd','timeout','goal')):
            raise ValueError('replacement task needs actual owner, cwd, timeout and useful role goal')
        if not payload.get('model_requirements'):
            raise ValueError('actual eligible model route requirements required')
        args=self.command+['submit','--id',task['id'],'--key',key,'--payload',json.dumps(payload)]
        for path in task.get('paths',[]):args+=['--paths',str(path)]
        result=subprocess.run(args,cwd=self.cwd,check=True,capture_output=True,text=True,timeout=20)
        return {'state':'queued','task_id':task['id'],'receipt':result.stdout.strip()}


class FailoverBridge:
    def __init__(self, authority, bus, *, sender_id, token, recipients, launcher_queue):
        self.authority=authority
        self.bus=bus
        self.sender_id=sender_id
        self.token=token
        self.recipients=dict(recipients)
        self.launcher_queue=launcher_queue

    def publish_events(self):
        """Bus dedup key handles replay/crash without replacing envelope identity.

        Local event != sent envelope != semantic ACK. Unknown recipient fails
        closed and retains event for next supervisor tick.
        """
        receipts=[]
        for event in self.authority.events():
            if event['kind'] not in ('sync_probe','elected','head_backfill_required','replacement_required'):
                continue
            payload=json.loads(event['payload'])
            recipient=payload.get('recipient') or payload.get('holder') or self.sender_id
            bus_recipient=self.recipients.get(recipient)
            try:
                if bus_recipient is None:
                    raise ValueError('missing enrolled bus recipient: '+recipient)
                message=self.bus.send(sender_id=self.sender_id,token=self.token,recipient_id=bus_recipient,
                    body='Role failover event '+event['kind']+'. Inspect exact runtime and task custody; reply semantically.',
                    data={'project':event['project'],'role':event['role'],'epoch':event['epoch'],
                          'event_id':event['id'],'details':payload},
                    idempotency_key='role-event:'+self.authority.path+':'+str(event['id']),kind='role-control')
                receipts.append({'event_id':event['id'],'envelope_id':message.message_id,'state':'recorded',
                                 'project':event['project'],'role':event['role'],'epoch':event['epoch'],'kind':event['kind']})
            except Exception as error:
                receipts.append({'event_id':event['id'],'state':'pending_delivery','error':str(error),
                                 'project':event['project'],'role':event['role'],'epoch':event['epoch'],'kind':event['kind']})
        return receipts

    def tick(self, project, role, *, replacement_task=None):
        plan=self.authority.startup_plan(project,role,replacement_task)
        result=self.authority.tick(project,role)
        receipts=self.publish_events()
        # Only a fenced elected owner may reserve a role startup/control task.
        # A no-candidate event requires a healthy enrolled standby to provide
        # recovery ownership; this adapter does not fabricate a principal.
        own_delivery_pending=any(r['state']=='pending_delivery' and r['kind']=='elected'
            and (r['project'],r['role'],r['epoch'])==(project,role,result['epoch']) for r in receipts)
        if result['state'] in ('elected','healthy') and plan and not own_delivery_pending:
            plan=dict(plan)
            plan['id']=plan['id']+'-epoch-'+str(result['epoch'])
            plan['payload']=dict(plan['payload'])
            plan['payload']['role_context']={'project':project,'role':role,'holder':result['holder'],
                'generation':result['generation'],'epoch':result['epoch']}
            result['launch']=self.authority.guarded_effect(project,role,result['holder'],
                result['generation'],result['epoch'],
                'role-start:'+project+':'+role+':'+str(result['epoch']),plan,self.launcher_queue)
        if result['state'] in ('elected','healthy'):
            if role=='principal':
                result['head_backfills']=self.reconcile_head_backfills(project,role,result)
            result['activation']=self.authority.activation(project,role,result['holder'],result['generation'],result['epoch'])
        result['receipts']=receipts
        return result

    def reconcile_head_backfills(self, project, role, leader):
        """Use owner-approved head templates, preserve child writers, retry exact key."""
        outcomes=[]
        for event in self.authority.events():
            if event['kind']!='head_backfill_required':
                continue
            details=json.loads(event['payload'])
            if details.get('promoted')!=leader['holder']:
                continue
            head=self.authority.role_state(event['project'],event['role'])
            if head['epoch']!=event['epoch'] or head['holder'] is not None:
                continue
            plan=self.authority.startup_plan(event['project'],event['role'])
            if plan is None:
                outcomes.append({'role':event['role'],'state':'pending_owned_head_startup_plan'})
                continue
            plan=dict(plan);plan['id']=plan['id']+'-backfill-epoch-'+str(event['epoch'])
            plan['payload']=dict(plan['payload'])
            plan['payload']['role_context']={'project':event['project'],'role':event['role'],
                'epoch':event['epoch'],'requested_by':leader['holder'],'preserve_task_custody':True}
            outcome=self.authority.guarded_effect(project,role,leader['holder'],leader['generation'],leader['epoch'],
                'head-backfill:'+event['project']+':'+event['role']+':'+str(event['epoch']),plan,self.launcher_queue)
            outcomes.append({'role':event['role'],'epoch':event['epoch'],'queue':outcome,
                             'activation':'pending_enrolled_head_role_ack_and_first_action'})
        return outcomes
