import hashlib
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import timedelta
from urllib.parse import parse_qs, urlsplit
from sqlalchemy import select
from workbench.auth import digest
from workbench.extensions import db
from workbench.models import Account, AuditEvent, CodeConsumption, LoginAttempt, Membership, PermissionGrant, Person, PersonRestriction, Session, Workspace, now
from conftest import ORIGIN, begin, login


def test_unauthenticated_routes_do_not_serve_data(client):
    for route in ("/api/auth/me", "/api/workspaces", "/api/admin/overview"):
        response = client.get(route)
        assert response.status_code == 401
        assert response.json["error"]["code"] == "SESSION_REQUIRED"


def test_login_origin_and_pkce(client, app):
    for origin in (None, "https://attacker.test"):
        response = client.post("/api/auth/login", headers={"Origin": origin} if origin else {})
        assert response.status_code == 403
    response = client.post("/api/auth/login", headers={"Origin": ORIGIN})
    params = parse_qs(urlsplit(response.json["authorization_url"]).query)
    assert params["redirect_uri"] == [ORIGIN + "/api/auth/callback"]
    assert len(params["challenge"][0]) == 43
    assert "HttpOnly" in response.headers["Set-Cookie"]
    assert "SameSite=Lax" in response.headers["Set-Cookie"]
    with app.app_context():
        attempt = db.session.get(LoginAttempt, digest(params["state"][0]))
        assert attempt is not None and attempt.verifier != params["challenge"][0]


def test_state_bound_to_browser_and_consumed_once(client, app):
    state = begin(client)
    other_browser = app.test_client()
    response = other_browser.get("/api/auth/callback", query_string={"code": "code-a", "state": state})
    assert response.location == "/login?error=LOGIN_STATE_INVALID"
    assert app.extensions["identity_provider"].exchange_calls == 0
    response = client.get("/api/auth/callback", query_string={"code": "code-a", "state": state})
    assert response.location == "/"
    assert client.get("/api/auth/callback", query_string={"code": "code-b", "state": state}).location.endswith("LOGIN_STATE_INVALID")
    assert app.extensions["identity_provider"].exchange_calls == 1


def test_callback_race_has_single_exchange(client, app):
    state = begin(client)
    browser = client.get_cookie("workbench_login", path="/api/auth").value
    def complete(_):
        competitor = app.test_client()
        competitor.set_cookie("workbench_login", browser, path="/api/auth")
        return competitor.get("/api/auth/callback", query_string={"state": state, "code": "race-code"}).location
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(complete, range(2)))
    assert results.count("/") == 1
    assert app.extensions["identity_provider"].exchange_calls == 1


def test_code_cannot_be_replayed_with_new_state(client, app):
    assert login(client, "same-code").location == "/"
    assert login(client, "same-code").location == "/login?error=CODE_REPLAYED"
    assert app.extensions["identity_provider"].exchange_calls == 1


def test_expired_login_state_is_rejected(client, app):
    state = begin(client)
    with app.app_context():
        db.session.get(LoginAttempt, digest(state)).expires_at = now() - timedelta(seconds=1)
        db.session.commit()
    assert client.get("/api/auth/callback", query_string={"code": "code-a", "state": state}).location.endswith("LOGIN_STATE_INVALID")


def test_session_is_independent_hashed_cookie_and_default_least_privilege(client, app):
    response = login(client)
    assert response.location == "/"
    cookie = client.get_cookie("workbench_session", path="/api")
    with app.app_context():
        session = db.session.scalar(select(Session))
        assert session.token_digest == hashlib.sha256(cookie.value.encode()).hexdigest()
        assert session.token_digest != cookie.value
        assert db.session.scalar(select(PermissionGrant)) is None
    me = client.get("/api/auth/me")
    assert me.json["permissions"] == []
    assert me.json["admission"] == {"community_active": True}
    assert client.get("/api/workspaces").json == {"items": []}
    assert client.get("/api/admin/overview").status_code == 403


def test_logout_requires_csrf_and_revokes_even_during_outage(client, app):
    login(client)
    csrf = client.get("/api/auth/me").json["csrf_token"]
    raw = client.get_cookie("workbench_session", path="/api").value
    assert client.post("/api/auth/logout", headers={"Origin": ORIGIN}).status_code == 403
    assert client.post("/api/auth/logout", headers={"Origin": ORIGIN, "X-CSRF-Token": "中文"}).status_code == 403
    assert client.post("/api/auth/logout", headers={"Origin": "https://attacker.test", "X-CSRF-Token": csrf}).status_code == 403
    app.extensions["identity_provider"].outage = True
    assert client.post("/api/auth/logout", headers={"Origin": ORIGIN, "X-CSRF-Token": csrf}).status_code == 204
    client.set_cookie("workbench_session", raw, path="/api")
    assert client.get("/api/auth/me").status_code == 401


def test_every_business_request_revalidates_admission(client, app):
    login(client)
    fake = app.extensions["identity_provider"]
    for route in ("/api/auth/me", "/api/workspaces", "/api/admin/overview"):
        client.get(route)
    assert fake.inspect_calls == 3
    fake.identity = replace(fake.identity, community_active=False)
    assert client.get("/api/workspaces").status_code == 403
    fake.identity = replace(fake.identity, community_active=True)
    assert client.get("/api/auth/me").status_code == 401


def test_outage_fails_closed_without_revoking_valid_session(client, app):
    login(client)
    fake = app.extensions["identity_provider"]
    fake.outage = True
    assert client.get("/api/workspaces").status_code == 503
    fake.outage = False
    assert client.get("/api/auth/me").status_code == 200


def test_failed_exchange_burns_attempt(client, app):
    fake = app.extensions["identity_provider"]
    fake.outage = True
    state = begin(client)
    browser = client.get_cookie("workbench_login", path="/api/auth").value
    assert client.get("/api/auth/callback", query_string={"code": "uncertain-code", "state": state}).location.endswith("IDENTITY_PROVIDER_UNAVAILABLE")
    fake.outage = False
    client.set_cookie("workbench_login", browser, path="/api/auth")
    assert client.get("/api/auth/callback", query_string={"code": "uncertain-code", "state": state}).location.endswith("LOGIN_STATE_INVALID")
    assert fake.exchange_calls == 1


def test_security_version_change_revokes_local_session(client, app):
    login(client)
    fake = app.extensions["identity_provider"]
    fake.identity = replace(fake.identity, security_version="2")
    assert client.get("/api/auth/me").status_code == 401


def test_person_remapping_never_migrates_permissions(client, app):
    login(client)
    fake = app.extensions["identity_provider"]
    fake.identity = replace(fake.identity, person_id="different-person")
    assert client.get("/api/auth/me").json["error"]["code"] == "IDENTITY_CHANGED"
    assert login(client).location.endswith("IDENTITY_CHANGED")
    with app.app_context():
        assert db.session.scalar(select(Account)).person.external_id == "person-1"


def test_person_block_cannot_be_bypassed_by_another_account(client, app):
    login(client)
    with app.app_context():
        db.session.scalar(select(Person)).blocked = True
        db.session.commit()
    fake = app.extensions["identity_provider"]
    fake.identity = replace(fake.identity, subject="account-2")
    assert login(client).location.endswith("ADMISSION_DENIED")
    with app.app_context():
        assert db.session.scalar(select(Account).where(Account.subject == "account-2")) is None


def test_workspace_restriction_follows_person_but_grants_do_not(client, app):
    login(client)
    with app.app_context():
        first = db.session.scalar(select(Account))
        work = Workspace(name="内部组")
        db.session.add(work)
        db.session.flush()
        db.session.add_all([Membership(account_id=first.id, workspace_id=work.id),
            PersonRestriction(person_id=first.person_id, workspace_id=work.id, reason="blocked"),
            PermissionGrant(account_id=first.id, permission="governance:view")])
        db.session.commit()
    assert client.get("/api/admin/overview").status_code == 200
    assert client.get("/api/workspaces").json["items"] == []
    fake = app.extensions["identity_provider"]
    fake.identity = replace(fake.identity, subject="account-2")
    login(client)
    with app.app_context():
        second = db.session.scalar(select(Account).where(Account.subject == "account-2"))
        workspace = db.session.scalar(select(Workspace))
        db.session.add(Membership(account_id=second.id, workspace_id=workspace.id))
        db.session.commit()
    assert client.get("/api/workspaces").json["items"] == []
    assert client.get("/api/admin/overview").status_code == 403


def test_case_sensitive_subjects_and_no_display_name_merge(client, app):
    login(client)
    fake = app.extensions["identity_provider"]
    fake.identity = replace(fake.identity, subject="ACCOUNT-1", person_id="PERSON-1")
    assert login(client).location == "/"
    with app.app_context():
        assert len(list(db.session.scalars(select(Account)))) == 2
        assert len(list(db.session.scalars(select(Person)))) == 2


def test_explicit_governance_cli_is_audited_and_does_not_grant_membership(client, app):
    login(client)
    runner = app.test_cli_runner()
    args = ["grant-governance", "--issuer", "https://training.test", "--subject", "account-1", "--reason", "initial local owner"]
    assert runner.invoke(args=args).exit_code == 0
    assert client.get("/api/admin/overview").status_code == 200
    assert client.get("/api/workspaces").json["items"] == []
    assert runner.invoke(args=args + ["--revoke"]).exit_code == 0
    assert client.get("/api/admin/overview").status_code == 403
    with app.app_context():
        assert len(list(db.session.scalars(select(AuditEvent).where(AuditEvent.event.like("governance_%"))))) == 2


def test_governance_cli_rejects_ambiguous_subject_and_allows_disabled_revocation(client, app):
    login(client)
    runner = app.test_cli_runner()
    args = ["grant-governance", "--issuer", "https://training.test", "--subject", "account-1", "--reason", "local review"]
    assert runner.invoke(args=args).exit_code == 0
    bad_args = ["grant-governance", "--issuer", "https://training.test", "--subject", "account-1 ", "--reason", "local review"]
    assert runner.invoke(args=bad_args).exit_code != 0
    with app.app_context():
        db.session.scalar(select(Account)).disabled = True
        db.session.commit()
    assert runner.invoke(args=args + ["--revoke"]).exit_code == 0
    with app.app_context():
        assert db.session.scalar(select(PermissionGrant)) is None
