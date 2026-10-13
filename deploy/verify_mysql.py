"""Explicit isolated MySQL migration/flow check; never uses the production database."""
import argparse
import io
import json
import os
import secrets
import sys
import tempfile
import warnings
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
from dotenv import load_dotenv
from sqlalchemy.engine import make_url
from sqlalchemy import create_engine, text
from sqlalchemy.exc import LegacyAPIWarning
from flask_migrate import upgrade
from workbench import create_app
from workbench.import_legacy import import_snapshot
from workbench.provider import Identity
from workbench.errors import unavailable

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--env-file', required=True)
parser.add_argument('--snapshot', required=True)
parser.add_argument('--administrator-subject', required=True)
parser.add_argument('--report', required=True)
parser.add_argument('--reset-verification', action='store_true', help='Recreate only the derived _verify database')
args = parser.parse_args()
load_dotenv(args.env_file)
production = make_url(os.environ['WORKBENCH_DATABASE_URL'])
if production.get_backend_name() != 'mysql' or not production.database or production.database.endswith('_verify'):
    raise SystemExit('Expected the independent production database configuration; verification uses its _verify sibling')
verification = production.set(database=production.database + '_verify')
if args.reset_verification:
    import re
    name = verification.database
    if not re.fullmatch(r'[A-Za-z0-9_]+', name) or name == production.database:
        raise SystemExit('Invalid verification database name')
    engine = create_engine(production)
    with engine.connect().execution_options(isolation_level='AUTOCOMMIT') as connection:
        connection.execute(text('DROP DATABASE IF EXISTS `' + name + '`'))
        connection.execute(text('CREATE DATABASE `' + name + '` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci'))
    engine.dispose()
snapshot = json.loads(Path(args.snapshot).read_text())
owner = next(u for u in snapshot['tables']['directory_user'] if str(u['id']) == args.administrator_subject)
directory = {k: snapshot['tables'][v] for k, v in [('users', 'directory_user'), ('groups', 'club_group'),
    ('positions', 'club_position'), ('officers', 'club_officer'), ('memberships', 'club_membership')]}


class VerificationProvider:
    """Only injected into this TESTING app, never a runtime authentication mode."""
    configured = True
    outage = False

    def authorize(self, **values): return 'http://127.0.0.1/verification?' + urlencode(values)
    def exchange(self, **values): return self.inspect()
    def inspect(self, **values):
        if self.outage: raise unavailable()
        return Identity(snapshot['issuer'], str(owner['id']), str(owner['person_id']),
                        '隔离验证管理员', '1', True, True, True, directory)


warnings.filterwarnings('ignore', category=LegacyAPIWarning)
with tempfile.TemporaryDirectory(prefix='workbench-private-verification-') as files:
    provider = VerificationProvider()
    app = create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': verification.render_as_string(hide_password=False),
        'BASE_PATH': '', 'WORK_FILE_ROOT': files}, identity_provider=provider)
    with app.app_context():
        upgrade(directory=str(Path(__file__).resolve().parents[1] / 'backend/migrations'))
        counts = import_snapshot(args.snapshot, args.administrator_subject, apply=True)
        client = app.test_client()
        origin = app.config['PUBLIC_ORIGIN']
        begin = client.post('/api/auth/login', headers={'Origin': origin})
        assert begin.status_code == 200
        state = parse_qs(urlsplit(begin.json['authorization_url']).query)['state'][0]
        assert client.get('/api/auth/callback', query_string={'state': state, 'code': secrets.token_urlsafe(32)}).status_code == 302
        me = client.get('/api/auth/me'); assert me.status_code == 200
        headers = {'Origin': origin, 'X-CSRF-Token': me.json['csrf_token']}
        checks = []
        for path in ['/api/work/me', '/api/work/items', '/api/work/me/todos', '/api/work/items?mine=1', '/api/work/files',
                     '/api/work/governance/workspaces', '/api/work/governance/grants', '/api/admin/club/groups', '/api/organization', '/api/notifications']:
            response = client.get(path)
            assert response.status_code == 200, (path, response.status_code)
            checks.append(path)
        workspace = client.get('/api/work/me').json['data']['workspaces'][0]['id']
        item = client.post('/api/work/items', headers=headers, json={'workspace_id': workspace, 'kind': 'task',
            'title': 'verification-only', 'task': {'assignee_user_id': owner['id'], 'due_at': '2030-01-01'}})
        assert item.status_code == 200, item.json
        item_id = item.json['data']['id']
        for command in ['publish', 'start', 'complete']:
            version = client.get('/api/work/items/' + str(item_id)).json['data']['version']
            result = client.post('/api/work/items/' + str(item_id) + '/commands', headers=headers,
                json={'command': command, 'expected_version': version, 'completion_note': 'verification'})
            assert result.status_code == 200, result.json
        assert client.get('/api/work/items/' + str(item_id)).json['data']['status'] == 'done'
        topic = client.post('/api/work/items', headers=headers,
            json={'workspace_id': workspace, 'kind': 'topic', 'title': 'verification-file'}).json['data']
        assert client.post('/api/work/items/' + str(topic['id']) + '/commands', headers=headers,
            json={'command': 'publish', 'expected_version': 1}).status_code == 200
        uploaded = client.post('/api/work/items/' + str(topic['id']) + '/files', headers=headers,
            data={'file': (io.BytesIO(b'verification'), 'check.txt')})
        assert uploaded.status_code == 200, uploaded.json
        provider.outage = True
        assert client.get('/api/work/items').status_code == 503
        provider.outage = False
        assert client.get('/api/work/items').status_code == 200
        report = {'database': verification.database, 'migrations': 'passed', 'import_counts': counts,
                  'read_routes_passed': checks, 'task_lifecycle': 'passed', 'private_upload': 'passed',
                  'upstream_outage_recovery': 'passed', 'identity_provider': 'isolated test double; not a production user login'}
        Path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=2))
        print(json.dumps(report, ensure_ascii=False))
