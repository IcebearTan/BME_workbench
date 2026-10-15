import json
from dataclasses import replace

import pytest

from conftest import login, ORIGIN
from test_collaboration import prepare, create, command
from workbench.extensions import db
from workbench.collab.models import (
    PersonWorkspaceRestrictionModel, WorkAccessGrant, WorkEvent,
    WorkItemParticipant,
)


def detail(client, item):
    response = client.get(f"/api/work/items/{item['id']}")
    assert response.status_code == 200, response.json
    return response.json['data']


def settings(client, headers, item, task, **fields):
    return client.patch(f"/api/work/items/{item['id']}", json={
        'expected_version': detail(client, item)['version'], 'task': task, **fields,
    }, headers=headers)


def login_as(app, client, user_id):
    provider = app.extensions['identity_provider']
    provider.identity = replace(provider.identity, subject=str(user_id), person_id=str(user_id))
    assert login(client).status_code == 302
    me = client.get('/api/auth/me')
    assert me.status_code == 200, me.json
    return {'Origin': ORIGIN, 'X-CSRF-Token': me.json['csrf_token']}


def veto(app, user_id, workspace_id=1):
    with app.app_context():
        db.session.add(PersonWorkspaceRestrictionModel(
            person_id=user_id, workspace_id=workspace_id, state='vetoed', reason='隔离测试否决'))
        db.session.commit()


def test_minimal_draft_can_be_configured_and_published_with_cross_group_reviewer(app, client):
    headers = prepare(app, client)
    item = create(client, headers, kind='task', visibility='participants')
    assert set(item['allowed_actions']) == {'edit', 'publish'}
    response = settings(client, headers, item, {
        'assignee_user_id': 1, 'due_at': '2030-01-02', 'reviewer_user_id': 3,
        'priority': 'high', 'accept_criteria': '交付说明完整',
    })
    assert response.status_code == 200, response.json
    with app.app_context():
        assert WorkItemParticipant.query.filter_by(item_id=item['id']).count() == 0
        event = WorkEvent.query.filter_by(item_id=item['id'], event_type='edited').one()
        change = json.loads(event.diff_json)['task']
        assert change['reviewer_user_id'] == {'from': None, 'to': 3}
    command(client, headers, item, 'publish')
    command(client, headers, item, 'start')
    command(client, headers, item, 'submit', result_note='已完成交付')
    reviewer_headers = login_as(app, client, 3)
    reviewer_detail = detail(client, item)
    assert reviewer_detail['item_access']['via'] == 'participant'
    assert 'review_accept' in reviewer_detail['allowed_actions']
    command(client, reviewer_headers, item, 'review_accept')
    with app.app_context():
        assert WorkAccessGrant.query.filter_by(user_id=3, workspace_id=1).count() == 0


def test_draft_settings_can_be_cleared_and_publication_requires_ready_fields(app, client):
    headers = prepare(app, client)
    item = create(client, headers, kind='task')
    for task in ({'assignee_user_id': 1, 'due_at': '2030-01-01',
                  'reviewer_user_id': 3, 'priority': 'urgent', 'accept_criteria': '草拟标准'},
                 {'assignee_user_id': None, 'due_at': None, 'reviewer_user_id': None,
                  'priority': None, 'accept_criteria': None}):
        response = settings(client, headers, item, task)
        assert response.status_code == 200, response.json
    current = detail(client, item)
    assert current['task']['assignee_user_id'] is None
    assert current['task']['due_at'] is None
    assert current['task']['reviewer_user_id'] is None
    assert current['task']['priority'] == 'normal'
    response = client.post(f"/api/work/items/{item['id']}/commands", json={
        'command': 'publish', 'expected_version': current['version'],
    }, headers=headers)
    assert response.status_code == 409
    assert detail(client, item)['status'] == 'draft'


def test_create_retry_returns_current_version_for_following_publish(app, client):
    headers = prepare(app, client)
    item = create(client, headers, idempotency_key='retry-topic')
    changed = client.patch(f"/api/work/items/{item['id']}", json={
        'expected_version': item['version'], 'title': '补充后的讨论',
    }, headers=headers)
    assert changed.status_code == 200
    retried = create(client, headers, idempotency_key='retry-topic')
    assert retried['id'] == item['id']
    assert retried['version'] == item['version'] + 1
    response = client.post(f"/api/work/items/{item['id']}/commands", json={
        'command': 'publish', 'expected_version': retried['version'],
    }, headers=headers)
    assert response.status_code == 200, response.json


@pytest.mark.parametrize('task', [
    {'status': 'done'}, {'assignee_user_id': True}, {'assignee_user_id': -1},
    {'assignee_user_id': '²'}, {'assignee_user_id': '1' * 100},
    {'reviewer_user_id': 1.5}, {'due_at': '2030-01-01junk'},
    {'due_at': '2030-02-30'}, {'priority': 'immediate'},
    {'accept_criteria': []}, {'accept_criteria': '长' * 2001}, None,
])
def test_invalid_task_settings_rejected_without_partial_write(app, client, task):
    headers = prepare(app, client)
    item = create(client, headers, kind='task')
    response = settings(client, headers, item, task, title='不得保存')
    assert response.status_code == 400, response.json
    current = detail(client, item)
    assert current['title'] == item['title'] and current['version'] == item['version']


def test_stale_settings_and_unrelated_member_cannot_change_task(app, client):
    headers = prepare(app, client)
    item = create(client, headers, kind='task')
    assert settings(client, headers, item, {'assignee_user_id': 1, 'due_at': '2030-01-01'}).status_code == 200
    stale = client.patch(f"/api/work/items/{item['id']}", json={
        'expected_version': item['version'], 'task': {'priority': 'urgent'},
    }, headers=headers)
    assert stale.status_code == 409
    command(client, headers, item, 'publish')
    member_headers = login_as(app, client, 2)
    response = settings(client, member_headers, item, {'priority': 'urgent'})
    assert response.status_code == 403
    assert detail(client, item)['task']['priority'] == 'normal'


@pytest.mark.parametrize('field', ['assignee_user_id', 'reviewer_user_id'])
def test_settings_cannot_select_person_denied_in_item_workspace(app, client, field):
    headers = prepare(app, client)
    item = create(client, headers, kind='task')
    veto(app, 3)
    response = settings(client, headers, item, {field: 3})
    assert response.status_code == 400
    assert detail(client, item)['task'][field] is None


@pytest.mark.parametrize('field', ['assignee_user_id', 'reviewer_user_id'])
def test_publication_rechecks_person_access_after_settings(app, client, field):
    headers = prepare(app, client)
    item = create(client, headers, kind='task')
    params = {'assignee_user_id': 1, 'reviewer_user_id': 2, 'due_at': '2030-01-01', field: 3}
    assert settings(client, headers, item, params).status_code == 200
    veto(app, 3)
    response = client.post(f"/api/work/items/{item['id']}/commands", json={
        'command': 'publish', 'expected_version': detail(client, item)['version'],
    }, headers=headers)
    assert response.status_code == 409
    assert detail(client, item)['status'] == 'draft'
    with app.app_context():
        assert WorkItemParticipant.query.filter_by(item_id=item['id']).count() == 0


def test_published_settings_keep_assignment_commands_and_grant_reviewer_item_access(app, client):
    headers = prepare(app, client)
    item = create(client, headers, kind='task', task={'assignee_user_id': 1, 'due_at': '2030-01-01'})
    command(client, headers, item, 'publish')
    for task in ({'assignee_user_id': 3}, {'due_at': '2031-01-01'}, {'due_at': None}):
        assert settings(client, headers, item, task).status_code == 409
    response = settings(client, headers, item, {
        'priority': 'high', 'accept_criteria': '提交成品', 'reviewer_user_id': 3,
    })
    assert response.status_code == 200, response.json
    login_as(app, client, 3)
    assert detail(client, item)['item_access']['via'] == 'participant'
    with app.app_context():
        assert WorkAccessGrant.query.filter_by(user_id=3, workspace_id=1).count() == 0


@pytest.mark.parametrize('state', ['review', 'done', 'cancelled'])
def test_review_and_terminal_tasks_cannot_change_acceptance_settings(app, client, state):
    headers = prepare(app, client)
    item = create(client, headers, kind='task', task={
        'assignee_user_id': 1, 'reviewer_user_id': 3, 'due_at': '2030-01-01',
    })
    command(client, headers, item, 'publish')
    if state == 'cancelled':
        command(client, headers, item, 'cancel', reason='隔离测试取消')
    else:
        command(client, headers, item, 'start')
        command(client, headers, item, 'submit', result_note='完成')
        if state == 'done':
            command(client, headers, item, 'review_accept')
    for task in ({'reviewer_user_id': None}, {'accept_criteria': '替换标准'}):
        assert settings(client, headers, item, task).status_code == 409
    assert detail(client, item)['task']['reviewer_user_id'] == 3


def test_invitation_rejects_workspace_veto_and_role_members_cannot_be_removed(app, client):
    headers = prepare(app, client)
    item = create(client, headers, kind='task', task={
        'assignee_user_id': 1, 'reviewer_user_id': 2, 'due_at': '2030-01-01',
    })
    command(client, headers, item, 'publish')
    veto(app, 3)
    response = client.post(f"/api/work/items/{item['id']}/participants", json={'user_id': 3}, headers=headers)
    assert response.status_code == 400
    for user_id in (1, 2):
        response = client.delete(f"/api/work/items/{item['id']}/participants/{user_id}", headers=headers)
        assert response.status_code == 409
    with app.app_context():
        assert WorkItemParticipant.query.filter_by(item_id=item['id'], removed_at=None).count() == 2


def test_topic_cannot_receive_task_fields(app, client):
    headers = prepare(app, client)
    item = create(client, headers)
    assert settings(client, headers, item, {'priority': 'high'}).status_code == 400
    response = client.patch(f"/api/work/items/{item['id']}", json={
        'expected_version': item['version'], 'status': 'done',
    }, headers=headers)
    assert response.status_code == 400


def test_other_members_cannot_configure_someone_elses_draft(app, client):
    headers = prepare(app, client)
    item = create(client, headers, kind='task')
    other_headers = login_as(app, client, 2)
    response = client.patch(f"/api/work/items/{item['id']}", json={
        'expected_version': item['version'], 'task': {'assignee_user_id': 2},
    }, headers=other_headers)
    assert response.status_code == 404


def test_unverified_person_cannot_be_configured_or_published_as_reviewer(app, client):
    headers = prepare(app, client)
    provider = app.extensions['identity_provider']
    provider.identity.directory['users'][2]['verification_status'] = 'unverified'
    item = create(client, headers, kind='task', task={
        'assignee_user_id': 1, 'reviewer_user_id': 3, 'due_at': '2030-01-01',
    })
    assert settings(client, headers, item, {'reviewer_user_id': 3}).status_code == 400
    response = client.post(f"/api/work/items/{item['id']}/commands", json={
        'command': 'publish', 'expected_version': detail(client, item)['version'],
    }, headers=headers)
    assert response.status_code == 409


def test_promote_preserves_legacy_reviewer_field_and_grants_only_item_access(app, client):
    headers = prepare(app, client)
    item = create(client, headers, visibility='participants')
    command(client, headers, item, 'publish')
    command(client, headers, item, 'promote', assignee_id=1,
            reviewer_id=3, due_at='2030-01-01')
    login_as(app, client, 3)
    assert detail(client, item)['task']['reviewer_user_id'] == 3
    assert detail(client, item)['item_access']['via'] == 'participant'
    with app.app_context():
        assert WorkAccessGrant.query.filter_by(user_id=3, workspace_id=1).count() == 0


def test_promote_cannot_add_reviewer_denied_in_source_workspace(app, client):
    headers = prepare(app, client)
    item = create(client, headers)
    command(client, headers, item, 'publish')
    veto(app, 3)
    response = client.post(f"/api/work/items/{item['id']}/commands", json={
        'command': 'promote', 'expected_version': detail(client, item)['version'],
        'assignee_id': 1, 'reviewer_id': 3, 'due_at': '2030-01-01',
    }, headers=headers)
    assert response.status_code == 400
    assert detail(client, item)['kind'] == 'topic'
