"""Cross-group packages expose explicit notes without granting source/target access."""
from dataclasses import replace
import io

import pytest

from workbench.extensions import db
from workbench.collab.models import WorkAccessGrant, WorkHandoff, WorkWorkspace
from conftest import login, ORIGIN
from test_collaboration import prepare, create, command
from test_internal_organization import manager, add, entry


def switch_user(app, client, uid):
    provider = app.extensions['identity_provider']
    provider.identity = replace(provider.identity, subject=str(uid), person_id=str(uid))
    assert login(client).status_code == 302
    return {'Origin': ORIGIN, 'X-CSRF-Token': client.get('/api/auth/me').json['csrf_token']}


def prepare_handoff(app, client):
    headers = prepare(app, client)
    with app.app_context():
        WorkAccessGrant.query.filter_by(user_id=3, workspace_id=2).one().role = 'coordinator'
        db.session.commit()
    source = create(client, headers, kind='task', body='源组内部正文不能共享',
                    task={'assignee_user_id': 1, 'due_at': '2030-01-01'})
    command(client, headers, source, 'publish')
    response = client.post(f"/api/work/items/{source['id']}/handoffs", headers=headers,
                           json={'to_workspace_id': 2, 'kind': '文案支持', 'note': '仅共享的交付要求'})
    assert response.status_code == 200, response.json
    return headers, source, response.json['data']['handoff_id']


def test_handoff_accept_complete_and_safe_package_tracking(app, client):
    headers, source, handoff_id = prepare_handoff(app, client)
    endpoint = f"/api/work/items/{source['id']}/handoffs"
    outgoing = client.get(endpoint).json['data']['outgoing'][0]
    assert outgoing['status'] == 'offered' and outgoing['can_withdraw']
    assert outgoing['can_read_source'] and not outgoing['can_read_target']

    target_headers = switch_user(app, client, 3)
    assert client.get(endpoint).status_code == 404
    response = client.post(f'/api/work/handoffs/{handoff_id}/accept', headers=target_headers, json={})
    assert response.status_code == 200, response.json
    target_id = response.json['data']['accepted_item_id']
    target = {'id': target_id}
    incoming_response = client.get(f'/api/work/items/{target_id}/handoffs')
    incoming = incoming_response.json['data']['incoming'][0]
    assert incoming['note'] == '仅共享的交付要求'
    assert not incoming['can_read_source'] and incoming['can_read_target']
    assert not incoming['can_withdraw']
    assert '源组内部正文不能共享' not in incoming_response.get_data(as_text=True)
    assert client.get(f"/api/work/items/{source['id']}").status_code == 404
    assert client.get(f'/api/work/items/{target_id}').json['data']['body'] is None
    command(client, target_headers, target, 'start')
    command(client, target_headers, target, 'complete', completion_note='已完成对外文案')
    assert client.get(f'/api/work/items/{target_id}/handoffs').json['data']['incoming'][0]['result_note'] == '已完成对外文案'

    switch_user(app, client, 1)
    outgoing = client.get(endpoint).json['data']['outgoing'][0]
    assert outgoing['status'] == 'done' and outgoing['result_note'] == '已完成对外文案'
    assert not outgoing['can_withdraw'] and not outgoing['can_read_target']
    assert client.get(f'/api/work/items/{target_id}').status_code == 404
    assert client.get(f'/api/work/items/{target_id}/handoffs').status_code == 404


def test_handoff_withdraw_requires_initiator_or_readable_source_coordinator(app, client):
    _, source, handoff_id = prepare_handoff(app, client)
    headers = switch_user(app, client, 2)
    endpoint = f"/api/work/items/{source['id']}/handoffs"
    assert not client.get(endpoint).json['data']['outgoing'][0]['can_withdraw']
    response = client.post(f'/api/work/handoffs/{handoff_id}/withdraw', headers=headers, json={})
    assert response.status_code == 403
    headers = switch_user(app, client, 1)
    assert client.post(f'/api/work/handoffs/{handoff_id}/withdraw', headers=headers, json={}).status_code == 200
    outgoing = client.get(endpoint).json['data']['outgoing'][0]
    assert outgoing['status'] == 'withdrawn' and not outgoing['can_withdraw']
    with app.app_context():
        assert WorkHandoff.query.get(handoff_id).accepted_item_id is None


def test_finished_task_and_inactive_group_cannot_receive_handoff(app, client):
    headers, source, _ = prepare_handoff(app, client)
    command(client, headers, source, 'start')
    command(client, headers, source, 'complete', completion_note='源任务完成')
    response = client.post(f"/api/work/items/{source['id']}/handoffs", headers=headers,
                           json={'to_workspace_id': 2, 'kind': '其他支持', 'note': '请求'})
    assert response.status_code == 409
    active = create(client, headers, kind='task', task={'assignee_user_id': 1, 'due_at': '2030-01-01'})
    command(client, headers, active, 'publish')
    app.extensions['identity_provider'].identity.directory['groups'][1]['status'] = 'archived'
    response = client.post(f"/api/work/items/{active['id']}/handoffs", headers=headers,
                           json={'to_workspace_id': 2, 'kind': '支持', 'note': '请求'})
    assert response.status_code == 404


def test_target_directory_includes_other_active_groups_without_read_access(app, client):
    prepare(app, client)
    provider = app.extensions['identity_provider']
    provider.identity.directory['groups'].append({'id': 3, 'name': '归档组', 'status': 'archived'})
    assert client.get('/api/auth/me').status_code == 200
    with app.app_context():
        db.session.add(WorkWorkspace(id=3, club_group_id=3, status='active', auto_grant=False))
        db.session.add(WorkWorkspace(id=4, scope='club', status='active', auto_grant=False))
        db.session.commit()
    data = client.get('/api/work/me').json['data']
    assert {w['id'] for w in data['workspaces']} == {1}
    assert {w['ws_id'] for w in data['available_targets']} == {1, 2}


def test_candidate_groups_include_all_active_local_and_source_memberships(app, client):
    headers = manager(app, client)
    assert add(client, headers, [entry(group_id=2), entry(group_id=3)]).status_code == 200
    candidates = client.get('/api/work/candidates').json['data']['candidates']
    person = next(row for row in candidates if row['user_id'] == 2)
    assert person['groups'] == [{'id': 1, 'name': '小组1'}, {'id': 2, 'name': '小组2'}, {'id': 3, 'name': '第三组'}]
    assert person['group_name'] == '小组1'

    from workbench.collab.models import InternalGroupMember
    with app.app_context():
        membership = InternalGroupMember.query.filter_by(user_id=2, group_id=3).one()
        membership.status = 'ended'
        db.session.commit()
    person = next(row for row in client.get('/api/work/candidates').json['data']['candidates'] if row['user_id'] == 2)
    assert {group['id'] for group in person['groups']} == {1, 2}


def prepare_attachment_handoff(app, client, tmp_path):
    app.config['WORK_FILE_ROOT'] = str(tmp_path / 'files')
    headers, source, _ = prepare_handoff(app, client)
    endpoint = f"/api/work/items/{source['id']}"
    uploaded = client.post(endpoint + '/files', headers=headers,
                           data={'file': (io.BytesIO(b'fixed shared version'), 'shared.txt')})
    assert uploaded.status_code == 200, uploaded.json
    file_data = uploaded.json['data']
    # A later upload must not silently replace the version explicitly sent to the other group.
    assert client.post(endpoint + '/files', headers=headers,
                       data={'file': (io.BytesIO(b'new internal revision'), 'shared.txt'),
                             'file_id': str(file_data['file_id'])}).status_code == 200
    other = client.post(endpoint + '/files', headers=headers,
                        data={'file': (io.BytesIO(b'other private file'), 'private.txt')}).json['data']
    response = client.post(endpoint + '/handoffs', headers=headers,
                           json={'to_workspace_id': 2, 'kind': '附件支持', 'note': '共享固定文件',
                                 'file_version_ids': [file_data['version_id']]})
    assert response.status_code == 200, response.json
    handoff_id = response.json['data']['handoff_id']
    packet = next(row for row in client.get(endpoint + '/handoffs').json['data']['outgoing']
                  if row['id'] == handoff_id)
    assert len(packet['files']) == 1
    attachment = packet['files'][0]
    assert attachment == {'id': file_data['file_id'], 'link_id': attachment['link_id'],
                          'display_name': 'shared.txt', 'version_no': 1, 'can_download': False}
    download_url = f"/api/work/files/{file_data['file_id']}/download?link_id={attachment['link_id']}"
    assert client.get(download_url).status_code == 404
    target_headers = switch_user(app, client, 3)
    assert client.get(download_url).status_code == 404
    accepted = client.post(f'/api/work/handoffs/{handoff_id}/accept', headers=target_headers, json={})
    assert accepted.status_code == 200, accepted.json
    return source, accepted.json['data']['accepted_item_id'], attachment, other, download_url


def test_handoff_attachment_is_fixed_version_and_independent_of_source_read(app, client, tmp_path):
    source, target_id, attachment, other, download_url = prepare_attachment_handoff(app, client, tmp_path)
    response = client.get(f'/api/work/items/{target_id}/handoffs')
    packet = response.json['data']['incoming'][0]
    assert packet['files'] == [{**attachment, 'can_download': True}]
    assert 'object_key' not in response.get_data(as_text=True)
    assert '源组内部正文不能共享' not in response.get_data(as_text=True)
    assert client.get(f"/api/work/items/{source['id']}").status_code == 404
    assert client.get(download_url).data == b'fixed shared version'
    assert client.get(f"/api/work/files/{other['file_id']}/download?link_id={attachment['link_id']}").status_code == 404
    switch_user(app, client, 1)
    outgoing = client.get(f"/api/work/items/{source['id']}/handoffs").json['data']['outgoing']
    packet = next(row for row in outgoing if row['files'])
    assert not packet['files'][0]['can_download']
    assert client.get(download_url).status_code == 404


@pytest.mark.parametrize('failure', ['revoked', 'workspace_closed', 'vetoed', 'removed', 'wrong_version', 'missing_version'])
def test_handoff_attachment_rechecks_permission_and_fixed_link(app, client, tmp_path, failure):
    from workbench.collab.models import WorkFile, WorkFileLink, PersonWorkspaceRestrictionModel
    _, _, attachment, other, download_url = prepare_attachment_handoff(app, client, tmp_path)
    with app.app_context():
        if failure == 'revoked':
            WorkAccessGrant.query.filter_by(user_id=3, workspace_id=2).one().status = 'revoked'
        elif failure == 'workspace_closed':
            db.session.get(WorkWorkspace, 2).status = 'disabled'
        elif failure == 'vetoed':
            db.session.add(PersonWorkspaceRestrictionModel(person_id=3, workspace_id=2,
                                                           state='vetoed', reason='测试撤权'))
        elif failure == 'removed':
            db.session.get(WorkFile, attachment['id']).status = 'removed'
        elif failure == 'wrong_version':
            db.session.get(WorkFileLink, attachment['link_id']).version_id = other['version_id']
        else:
            db.session.get(WorkFileLink, attachment['link_id']).version_id = None
        db.session.commit()
    assert client.get(download_url).status_code == 404
