from datetime import date
from workbench.extensions import db
from workbench.models import Account, PermissionGrant
from workbench.collab.models import ClubOfficer, ClubOrgEvent, UserModel
from test_collaboration import prepare


def test_cross_year_and_unknown_history(app, client):
    prepare(app, client)
    with app.app_context():
        row = db.session.get(ClubOfficer, 11)
        row.term_start = date(2025, 1, 1)
        db.session.add(ClubOfficer(id=12, user_id=1, person_id=1, title='历任职位', status='ended',
            historical_year=2025, record_source='backfill', source_note='隔离测试资料'))
        db.session.add(ClubOfficer(id=13, user_id=1, person_id=1, title='年代不详的职位', status='ended', record_source='backfill'))
        db.session.commit()
    # The source snapshot still owns row 11 and rewrites its start; mirror fixture there too.
    app.extensions['identity_provider'].identity.directory['officers'][0]['term_start'] = '2025-01-01'
    for year in (2025, 2026):
        response = client.get(f'/api/appointments/history?year={year}')
        assert response.status_code == 200
        assert any(r['id'] == 11 for r in response.json['data']['records'])
    result = client.get('/api/appointments/history').json['data']
    assert result['undated_count'] == 1
    assert next(r for r in result['records'] if r['id'] == 12)['date_precision'] == 'year'
    assert result['people'] == []


def test_history_permissions_and_person_scope(app, client):
    prepare(app, client)
    assert client.get('/api/appointments/history?user_id=2').status_code == 403
    # Another account for the same verified source person shares the personal archive.
    app.extensions['identity_provider'].identity.directory['users'][1]['person_id'] = 1
    assert client.get('/api/appointments/history?user_id=2').status_code == 200
    assert client.get('/api/appointments/history?user_id=3').status_code == 403
    with app.app_context():
        account = Account.query.filter_by(subject='1').one()
        db.session.add(PermissionGrant(account_id=account.id, permission='governance:view'))
        db.session.commit()
    response = client.get('/api/appointments/history?user_id=3')
    assert response.status_code == 200
    assert len(response.json['data']['people']) == 3
    assert client.get('/api/appointments/history?year=invalid').status_code == 400
    assert client.get('/api/appointments/history?user_id=bad').status_code == 400


def test_history_events_sync_append_only_and_do_not_grant(app, client):
    prepare(app, client)
    snapshot = app.extensions['identity_provider'].identity.directory
    snapshot['officer_events'] = [{'id': 101, 'kind': 'officer_edited', 'officer_id': 11, 'user_id': 1,
        'occurred_at': '2026-01-01T12:00:00', 'operator_id': 3,
        'detail_json': '{"reason":"日期登记纠错"}'}]
    response = client.get('/api/appointments/history')
    assert response.status_code == 200
    assert response.json['data']['records'][0]['events'][0]['detail']['reason'] == '日期登记纠错'
    snapshot['officer_events'][0]['detail_json'] = '{"reason":"must-not-overwrite"}'
    client.get('/api/appointments/history')
    with app.app_context():
        assert ClubOrgEvent.query.count() == 1
        assert 'must-not-overwrite' not in db.session.get(ClubOrgEvent, 101).detail_json
        assert PermissionGrant.query.count() == 0


def test_auth_required_and_upstream_failure(app, client):
    app.config['COLLAB_ENABLED'] = True
    assert client.get('/api/appointments/history').status_code == 401
    prepare(app, client)
    app.extensions['identity_provider'].outage = True
    assert client.get('/api/appointments/history').status_code == 503


def test_own_history_does_not_require_workspace_grants(app, client):
    from workbench.collab.models import WorkAccessGrant
    prepare(app, client)
    with app.app_context():
        WorkAccessGrant.query.delete()
        db.session.commit()
    assert client.get('/api/appointments/history').status_code == 200
    assert client.get('/api/appointments/history?user_id=2').status_code == 403


def test_upgrade_preserves_existing_appointment_and_events(tmp_path):
    import secrets
    from pathlib import Path
    from sqlalchemy import text
    from flask_migrate import upgrade
    from workbench import create_app
    from conftest import FakeProvider, ORIGIN
    migrated = create_app({'TESTING': True, 'WORKBENCH_ENV': 'test', 'SECRET_KEY': secrets.token_urlsafe(48),
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///' + str(tmp_path / 'older.db'),
        'PUBLIC_ORIGIN': ORIGIN, 'COOKIE_SECURE': False, 'IDENTITY_ISSUER': 'https://training.test'}, identity_provider=FakeProvider())
    with migrated.app_context():
        directory = str(Path(__file__).resolve().parents[1] / 'migrations')
        upgrade(directory=directory, revision='0799a5ced593')
        db.session.execute(text("INSERT INTO directory_user (id,username,person_id) VALUES (1,'旧成员',42)"))
        db.session.execute(text("INSERT INTO club_officer (id,user_id,title,term_start,term_end,status) VALUES (1,1,'原职位','2025-01-01','2025-12-31','ended')"))
        db.session.execute(text("INSERT INTO club_org_event (id,kind,officer_id,occurred_at) VALUES (1,'officer_ended',1,'2026-01-01 00:00:00')"))
        db.session.commit()
        upgrade(directory=directory)
        row = db.session.get(ClubOfficer, 1)
        assert row.term_start == date(2025, 1, 1) and row.term_end == date(2025, 12, 31)
        assert row.person_id == 42 and row.record_source == 'legacy'
        assert ClubOrgEvent.query.count() == 1
        db.session.remove()
        db.engine.dispose()
