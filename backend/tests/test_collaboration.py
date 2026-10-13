import io
from dataclasses import replace
from datetime import date
from workbench.extensions import db
from workbench.models import Account, PermissionGrant
from workbench.collab.models import WorkWorkspace, WorkAccessGrant, WorkItem
from conftest import login, ORIGIN


def prepare(app, client):
    app.config.update(COLLAB_ENABLED=True)
    snapshot = {
        'users': [{'id': i, 'username': '成员' + str(i), 'person_id': i, 'status': 'active',
                   'lifecycle': 'active', 'verification_status': 'verified'} for i in (1, 2, 3)],
        'groups': [{'id': i, 'name': '小组' + str(i), 'status': 'active'} for i in (1, 2)],
        'positions': [{'id': 1, 'name': '组长', 'org_slot': 'group', 'sort_rank': 10}],
        'officers': [{'id': 11, 'user_id': 1, 'title_id': 1, 'group_id': 1, 'title': '组长',
                      'term_start': '2020-01-01', 'status': 'active'}],
        'memberships': [{'id': 20 + i, 'user_id': i, 'group_id': 1 if i < 3 else 2,
                         'slot': 'primary', 'joined_at': '2020-01-01'} for i in (1, 2, 3)],
    }
    provider = app.extensions['identity_provider']
    provider.identity = replace(provider.identity, subject='1', person_id='1', directory=snapshot)
    assert login(client).status_code == 302
    me = client.get('/api/auth/me')
    assert me.status_code == 200, me.json
    with app.app_context():
        db.session.add_all([WorkWorkspace(id=i, club_group_id=i, auto_grant=False) for i in (1, 2)])
        db.session.flush()
        db.session.add_all([WorkAccessGrant(user_id=i, workspace_id=1 if i < 3 else 2,
            role='coordinator' if i == 1 else 'member', source_type='membership', source_id=20+i,
            group_id_snapshot=1 if i < 3 else 2, granted_by=1, grant_reason='隔离测试') for i in (1, 2, 3)])
        db.session.commit()
    return {'Origin': ORIGIN, 'X-CSRF-Token': me.json['csrf_token']}


def create(client, headers, **fields):
    response = client.post('/api/work/items', json={'workspace_id': 1, 'kind': 'topic', 'title': '协作测试', **fields}, headers=headers)
    assert response.status_code == 200, response.json
    return response.json['data']


def command(client, headers, item, cmd, **fields):
    current = client.get('/api/work/items/' + str(item['id'])).json['data']
    response = client.post(f"/api/work/items/{item['id']}/commands", json={'command': cmd, 'expected_version': current['version'], **fields}, headers=headers)
    assert response.status_code == 200, response.json
    return response


def test_topic_reply_file_and_private_download(app, client, tmp_path):
    app.config['WORK_FILE_ROOT'] = str(tmp_path / 'files')
    headers = prepare(app, client)
    item = create(client, headers)
    command(client, headers, item, 'publish')
    response = client.post(f"/api/work/items/{item['id']}/replies", json={'body': '测试回复', 'client_request_id': 'test-reply'}, headers=headers)
    assert response.status_code == 200, response.json
    uploaded = client.post(f"/api/work/items/{item['id']}/files", data={'file': (io.BytesIO(b'hello work'), 'notes.txt')}, headers=headers)
    assert uploaded.status_code == 200, uploaded.json
    detail = client.get(f"/api/work/items/{item['id']}")
    assert detail.status_code == 200
    assert client.post('/api/work/items', json={'title': 'bad'}, headers={'Origin': ORIGIN}).status_code == 403
    assert client.get('/api/notifications').status_code == 200


def test_task_execution_and_optimistic_lock(app, client):
    headers = prepare(app, client)
    item = create(client, headers, kind='task', task={'assignee_user_id': 1, 'due_at': '2030-01-01'})
    command(client, headers, item, 'publish')
    command(client, headers, item, 'start')
    stale = client.patch(f"/api/work/items/{item['id']}", json={'title': 'stale', 'expected_version': 1}, headers=headers)
    assert stale.status_code == 409
    command(client, headers, item, 'complete', completion_note='完成说明')
    assert client.get(f"/api/work/items/{item['id']}").json['data']['status'] == 'done'


def test_governance_is_local_and_not_content_access(app, client):
    headers = prepare(app, client)
    assert client.get('/api/work/governance/workspaces').status_code == 403
    with app.app_context():
        actor = Account.query.filter_by(subject='1').one()
        db.session.add(PermissionGrant(account_id=actor.id, permission='governance:manage'))
        db.session.add(WorkItem(workspace_id=2, created_by=3, title='私密事项', kind='topic', visibility='participants', status='open'))
        db.session.commit()
        private_id = WorkItem.query.filter_by(created_by=3).one().id
    assert client.get('/api/work/governance/workspaces').status_code == 200
    assert client.get('/api/work/items/' + str(private_id)).status_code == 404
    assert client.get('/api/admin/club/groups').status_code == 200
    assert client.get('/api/user/user_list').json[0]['User_Id'] == 1


def test_current_organization_change_revokes_access(app, client):
    headers = prepare(app, client)
    item = create(client, headers)
    command(client, headers, item, 'publish')
    provider = app.extensions['identity_provider']
    provider.identity.directory['memberships'][0]['group_id'] = 2
    assert client.get(f"/api/work/items/{item['id']}").status_code == 404


def test_private_item_title_never_leaks_to_same_group_coordinator(app, client):
    headers = prepare(app, client)
    with app.app_context():
        row = WorkItem(workspace_id=1, created_by=2, title='private-title', kind='topic', visibility='participants', status='open')
        db.session.add(row);db.session.commit();item_id=row.id
    response=client.get('/api/work/items')
    assert response.status_code==200
    assert all(row['id']!=item_id for row in response.json['data']['items'])
    assert client.get('/api/work/items/'+str(item_id)).status_code==404


def test_merge_scan_includes_person_restrictions_for_another_empty_account(app,client):
    import base64
    from workbench.collab.models import PersonWorkspaceRestrictionModel
    prepare(app,client)
    app.config.update(IDENTITY_CLIENT_ID='integration',IDENTITY_CLIENT_SECRET='test-integration-key')
    with app.app_context():
        db.session.add(PersonWorkspaceRestrictionModel(person_id=3,workspace_id=1,state='vetoed',reason='test'))
        db.session.commit()
    header='Basic '+base64.b64encode(b'integration:test-integration-key').decode()
    response=client.post('/api/integrations/account-usage',headers={'Authorization':header},json={
        'issuer':app.config['IDENTITY_ISSUER'],'subject':'999','person_id':'3'})
    assert response.status_code==200 and response.json['has_business_data']
    assert response.json['counts']['person_restrictions']==1
    assert client.post('/api/integrations/account-usage',json={'subject':'1'}).status_code==401
