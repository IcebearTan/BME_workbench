import secrets
from dataclasses import replace
from pathlib import Path
from urllib.parse import urlencode, urlsplit, parse_qs
import pytest
from flask_migrate import upgrade
from workbench import create_app
from workbench.errors import unavailable
from workbench.extensions import db
from workbench.provider import Identity

ORIGIN = "http://127.0.0.1:8083"


class FakeProvider:
    """In-process test double; never registered by runtime configuration."""
    configured = True

    def __init__(self):
        self.identity = Identity("https://training.test", "account-1", "person-1", "测试成员", "1", True, True, True)
        self.outage = False
        self.exchange_calls = 0
        self.inspect_calls = 0

    def authorize(self, **params):
        return "https://training.test/authorize?" + urlencode(params)

    def exchange(self, **kwargs):
        self.exchange_calls += 1
        if self.outage:
            raise unavailable()
        return self.identity

    def inspect(self, **kwargs):
        self.inspect_calls += 1
        if self.outage:
            raise unavailable()
        return self.identity


@pytest.fixture
def app(tmp_path):
    fake = FakeProvider()
    app = create_app({"TESTING": True, "WORKBENCH_ENV": "test", "SECRET_KEY": secrets.token_urlsafe(48),
        "SQLALCHEMY_DATABASE_URI": "sqlite:///" + str(tmp_path / "isolated.db"),
        "PUBLIC_ORIGIN": ORIGIN, "COOKIE_SECURE": False,
        "IDENTITY_ISSUER": "https://training.test"}, identity_provider=fake)
    with app.app_context():
        upgrade(directory=str(Path(__file__).resolve().parents[1] / "migrations"))
    yield app
    with app.app_context():
        db.session.remove()
        db.engine.dispose()


@pytest.fixture
def client(app):
    return app.test_client()


def begin(client):
    response = client.post("/api/auth/login", headers={"Origin": ORIGIN})
    assert response.status_code == 200
    return parse_qs(urlsplit(response.json["authorization_url"]).query)["state"][0]


def login(client, code=None):
    state = begin(client)
    return client.get("/api/auth/callback", query_string={"code": code or secrets.token_urlsafe(24), "state": state})
