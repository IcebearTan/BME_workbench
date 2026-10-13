import secrets
from dataclasses import asdict
import pytest
from sqlalchemy.dialects import mysql
from sqlalchemy.schema import CreateTable
from workbench import create_app
from workbench.errors import ApiError
from workbench.models import Account, Person
from workbench.provider import DisabledProvider, HttpIdentityProvider
from conftest import FakeProvider, ORIGIN


def config():
    return {"IDENTITY_ISSUER": "https://training.test", "IDENTITY_CLIENT_ID": "workbench-client",
        "IDENTITY_CLIENT_SECRET": secrets.token_urlsafe(32),
        "IDENTITY_AUTHORIZE_URL": "https://training.test/authorize",
        "IDENTITY_EXCHANGE_URL": "https://training.test/exchange",
        "IDENTITY_STATUS_URL": "https://training.test/status"}


class Response:
    def __init__(self, data, status=200):
        self.data, self.status_code, self.content = data, status, b"response"

    def json(self):
        return self.data


def payload():
    return {**asdict(FakeProvider().identity), "audience": "workbench-client", "role": "super_admin"}


def test_disabled_provider_never_authenticates(app, client):
    app.extensions["identity_provider"] = DisabledProvider()
    assert client.get("/api/auth/status").json["login_enabled"] is False
    assert client.post("/api/auth/login", headers={"Origin": ORIGIN}).status_code == 503


@pytest.mark.parametrize("field,value", [("issuer", "https://other.test"), ("audience", "points-store"),
    ("subject", ""), ("subject", "account "), ("person_id", None), ("community_active", "true"),
    ("person_active", 1), ("security_version", None)])
def test_http_provider_rejects_invalid_or_incomplete_claims(monkeypatch, field, value):
    data = payload()
    data[field] = value
    monkeypatch.setattr("workbench.provider.requests.post", lambda *args, **kwargs: Response(data))
    with pytest.raises(ApiError) as caught:
        HttpIdentityProvider(config()).inspect(issuer="https://training.test", subject="account-1")
    assert caught.value.status == 503


@pytest.mark.parametrize("status", [301, 400, 401, 403, 404, 500])
def test_upstream_http_failures_are_outages_not_member_revocations(monkeypatch, status):
    monkeypatch.setattr("workbench.provider.requests.post", lambda *args, **kwargs: Response({}, status))
    with pytest.raises(ApiError) as caught:
        HttpIdentityProvider(config()).inspect(issuer="https://training.test", subject="account-1")
    assert caught.value.code == "IDENTITY_PROVIDER_UNAVAILABLE"


def test_http_provider_has_dedicated_audience_pkce_and_ignores_central_roles(monkeypatch):
    calls = []
    def post(*args, **kwargs):
        calls.append(kwargs)
        return Response(payload())
    monkeypatch.setattr("workbench.provider.requests.post", post)
    provider = HttpIdentityProvider(config())
    identity = provider.exchange(code="one-use", verifier="pkce", redirect_uri=ORIGIN + "/api/auth/callback")
    assert not hasattr(identity, "role")
    assert calls[0]["allow_redirects"] is False
    assert calls[0]["json"]["code_verifier"] == "pkce"
    assert calls[0]["json"]["audience"] == "workbench-client"
    assert "code_challenge_method=S256" in provider.authorize(state="state", challenge="challenge", redirect_uri="https://workbench.test/api/auth/callback")


def test_explicit_invalid_code_is_rejected(monkeypatch):
    monkeypatch.setattr("workbench.provider.requests.post", lambda *args, **kwargs: Response({"error": "INVALID_CODE"}, 400))
    with pytest.raises(ApiError) as caught:
        HttpIdentityProvider(config()).exchange(code="expired", verifier="pkce", redirect_uri=ORIGIN)
    assert caught.value.status == 403


def test_production_requires_dedicated_config_and_secure_transport():
    with pytest.raises(ValueError, match="SECRET_KEY"):
        create_app({"SECRET_KEY": ""})
    with pytest.raises(ValueError, match="HTTPS"):
        create_app({"WORKBENCH_ENV": "production", "SECRET_KEY": secrets.token_urlsafe(32),
            "PUBLIC_ORIGIN": "http://workbench.test", "COOKIE_SECURE": False})
    with pytest.raises(ValueError, match="MySQL"):
        create_app({"WORKBENCH_ENV": "production", "SECRET_KEY": secrets.token_urlsafe(32),
            "PUBLIC_ORIGIN": "https://workbench.test", "COOKIE_SECURE": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
    values = config()
    values["IDENTITY_EXCHANGE_URL"] = "http://training.test/exchange"
    with pytest.raises(ValueError, match="HTTPS"):
        HttpIdentityProvider(values)


def test_mysql_identity_columns_preserve_case():
    for model in (Account, Person):
        ddl = str(CreateTable(model.__table__).compile(dialect=mysql.dialect()))
        assert ddl.count("COLLATE utf8mb4_bin") == 2
