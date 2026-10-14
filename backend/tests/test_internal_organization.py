from dataclasses import replace
import pytest
from workbench.extensions import db
from workbench.models import Account, PermissionGrant
from workbench.provider import Identity
from workbench.errors import unavailable
from workbench.collab.models import InternalGroupMember, ClubGroup, WorkAccessGrant
from test_collaboration import prepare


def manager(app, client):
    headers = prepare(app, client)
    with app.app_context():
        account = Account.query.filter_by(subject='1').one()
        db.session.add(PermissionGrant(account_id=account.id, permission='governance:manage'))
        db.session.add(ClubGroup(id=3, name='第三组', status='active'))
        db.session.commit()
    provider = app.extensions['identity_provider']
    def admit(**params):
        if provider.outage:
            raise unavailable()
        return replace(provider.identity, subject=params['subject'], person_id=params['person_id'],
                       display_name='已认证成员' + params['subject'])
    provider.admit = admit
    return headers


def add(client, headers, entries):
    return client.post('/api/admin/organization/members', headers=headers,
        json={'entries': entries, 'reason': '正式名单登记', 'source_note': '2026学年正式名单'})


def entry(user_id=2, group_id=1, role='coordinator'):
    return {'user_id': user_id, 'person_id': user_id, 'group_id': group_id, 'role': role}


def test_multiple_groups_and_multiple_coordinators(app, client):
    headers = manager(app, client)
    response = add(client, headers, [entry(group_id=i) for i in (1, 2, 3)] + [entry(user_id=3)])
    assert response.status_code == 200, response.json
    with app.app_context():
        assert InternalGroupMember.query.filter_by(user_id=2, status='active').count() == 3
        assert InternalGroupMember.query.filter_by(group_id=1, role='coordinator', status='active').count() == 2
    assert client.get('/api/admin/organization/members').status_code == 200


def test_idempotent_and_role_change_preserves_period(app, client):
    headers = manager(app, client)
    assert add(client, headers, [entry()]).status_code == 200
    response = add(client, headers, [entry()])
    assert response.json['data']['results'][0]['status'] == 'unchanged'
    assert add(client, headers, [entry(role='member')]).status_code == 200
    with app.app_context():
        rows = InternalGroupMember.query.order_by(InternalGroupMember.id).all()
        assert len(rows) == 2 and rows[0].status == 'ended' and rows[1].role == 'member'
        assert rows[0].ended_at is not None and rows[0].end_reason
        from workbench.collab.services.access import grant_status_reason
        old_grant = WorkAccessGrant.query.filter_by(source_type='internal_membership', source_id=rows[0].id).one()
        assert not grant_status_reason(old_grant)[0]


def test_ending_one_group_keeps_other_groups(app, client):
    headers = manager(app, client)
    response = add(client, headers, [entry(group_id=1), entry(group_id=2)])
    row_id = response.json['data']['results'][0]['id']
    response = client.post(f'/api/admin/organization/members/{row_id}/end', headers=headers, json={'reason': '组内职责结束'})
    assert response.status_code == 200
    with app.app_context():
        from workbench.collab.services.access import grant_status_reason
        grants = WorkAccessGrant.query.filter_by(source_type='internal_membership', user_id=2).all()
        assert [grant_status_reason(g)[0] for g in grants] == [False, True]


def test_permissions_csrf_person_conflicts_and_outage(app, client):
    headers = prepare(app, client)
    assert add(client, headers, [entry()]).status_code == 403
    with app.app_context():
        account = Account.query.filter_by(subject='1').one()
        account_id = account.id
        db.session.add(PermissionGrant(account_id=account.id, permission='governance:view'))
        db.session.commit()
    assert add(client, headers, [entry()]).status_code == 403
    assert client.post('/api/admin/organization/members', json={'entries': [entry()]}).status_code == 403
    with app.app_context():
        db.session.add(PermissionGrant(account_id=account_id, permission='governance:manage'))
        db.session.commit()
    assert add(client, headers, [entry(), {**entry(group_id=2), 'person_id': 3}]).status_code == 409
    app.extensions['identity_provider'].admit = lambda **_: (_ for _ in ()).throw(unavailable())
    assert add(client, headers, [entry()]).status_code == 503
    with app.app_context():
        assert InternalGroupMember.query.count() == 0


def test_person_veto_and_source_roles_are_not_bypassed(app, client):
    headers = manager(app, client)
    from workbench.collab.models import PersonWorkspaceRestrictionModel
    with app.app_context():
        db.session.add(PersonWorkspaceRestrictionModel(person_id=2, workspace_id=1, state='vetoed', reason='人员否决'))
        db.session.commit()
    assert add(client, headers, [entry(role='member')]).status_code == 200
    with app.app_context():
        assert WorkAccessGrant.query.filter_by(source_type='internal_membership', user_id=2).count() == 0


def test_organization_projection_contains_local_roles(app, client):
    headers = manager(app, client)
    assert add(client, headers, [entry()]).status_code == 200
    response = client.get('/api/organization')
    first = next(g for g in response.json['data']['tree'] if g['id'] == 1)
    member = next(m for m in first['members'] if m['id'] == 2)
    assert member['title'] == '分管核心'
    history = client.get('/api/appointments/history?user_id=2').json['data']['records']
    assert any(r['record_source'] == 'internal' and r['title'] == '分管核心' for r in history)


def test_mismatched_upstream_identity_cannot_create_membership(app, client):
    headers = manager(app, client)
    provider = app.extensions['identity_provider']
    provider.admit = lambda **_: replace(provider.identity, subject='wrong', person_id='wrong')
    assert add(client, headers, [entry()]).status_code == 403
    with app.app_context():
        assert InternalGroupMember.query.count() == 0


def test_named_roster_rechecks_primary_account_before_admitting(app, client):
    headers = manager(app, client)
    provider = app.extensions['identity_provider']
    provider.candidates = lambda **_: [{'status': 'ambiguous', 'resolved_user_id': None}]
    assert add(client, headers, [{**entry(), 'name': '成员2'}]).status_code == 409
    with app.app_context():
        assert InternalGroupMember.query.count() == 0
    provider.candidates = lambda **_: [{'status': 'unique_matched', 'resolved_user_id': 2,
        'resolved_account': {'eligible': True}, 'candidates': [{'person_id': 2}]}]
    assert add(client, headers, [{**entry(), 'name': '成员2'}]).status_code == 200


def test_merge_scan_counts_only_internal_membership_history(app, client):
    import base64
    headers = manager(app, client)
    assert add(client, headers, [entry()]).status_code == 200
    with app.app_context():
        WorkAccessGrant.query.delete()
        db.session.commit()
    app.config.update(IDENTITY_CLIENT_ID='integration', IDENTITY_CLIENT_SECRET='test-secret')
    response = client.post('/api/integrations/account-usage', headers={
        'Authorization': 'Basic ' + base64.b64encode(b'integration:test-secret').decode()},
        json={'issuer': app.config['IDENTITY_ISSUER'], 'subject': '2', 'person_id': '2'})
    assert response.status_code == 200 and response.json['has_business_data']
    assert response.json['counts']['internal_memberships'] == 1
