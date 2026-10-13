import base64
import hashlib
import hmac
import secrets
from datetime import timedelta
from functools import wraps
from flask import Blueprint, current_app, jsonify, redirect, request
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from .extensions import db
from .errors import ApiError, denied, unavailable
from .models import Account, AuditEvent, CodeConsumption, LoginAttempt, PermissionGrant, Person, Session, now

auth = Blueprint("auth", __name__, url_prefix="/api/auth")


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def csrf_token(raw_session):
    return hmac.new(current_app.secret_key.encode(), ("csrf:" + raw_session).encode(), hashlib.sha256).hexdigest()


def provider():
    return current_app.extensions["identity_provider"]


def redirect_uri():
    return current_app.config["PUBLIC_ORIGIN"] + "/api/auth/callback"


def same_origin():
    if request.headers.get("Origin") != current_app.config["PUBLIC_ORIGIN"]:
        raise ApiError("ORIGIN_REJECTED", "请从工作台页面发起操作", 403)


def cookie_options(path):
    return dict(secure=current_app.config["COOKIE_SECURE"], httponly=True, samesite="Lax", path=path)


def invalidate_session(session, reason="Local or upstream admission/session validation failed"):
    session.revoked_at = now()
    db.session.add(AuditEvent(event="session_revoked", account_id=session.account_id, reason=reason))
    db.session.commit()


def local_session():
    raw = request.cookies.get(current_app.config["SESSION_COOKIE_NAME"], "")
    if not raw:
        raise ApiError("SESSION_REQUIRED", "请先通过训练营账号登录", 401)
    session = db.session.get(Session, digest(raw))
    if session is None or session.revoked_at is not None or session.expires_at <= now():
        raise ApiError("SESSION_REVOKED", "工作台会话已失效，请重新登录", 401)
    return raw, session


def current_actor():
    # Cache only on this request (not a potentially reused application context).
    cached = getattr(request, "_workbench_actor", None)
    if cached is not None:
        return cached
    raw, session = local_session()
    account = session.account
    if account.disabled or account.person.blocked:
        invalidate_session(session)
        raise denied()
    try:
        identity = provider().inspect(issuer=account.issuer, subject=account.subject)
    except ApiError as exc:
        if exc.status == 403:
            invalidate_session(session)
        raise
    if (identity.issuer, identity.subject, identity.person_id) != (
        account.issuer, account.subject, account.person.external_id
    ):
        invalidate_session(session)
        raise ApiError("IDENTITY_CHANGED", "人员关联发生变化，需完成身份核对后重新接入", 403)
    if not identity.admitted:
        invalidate_session(session)
        raise denied()
    if identity.security_version != session.security_version:
        invalidate_session(session)
        raise ApiError("SESSION_REVOKED", "账号安全状态已变更，请重新登录", 401)
    permissions = list(db.session.scalars(select(PermissionGrant.permission).where(PermissionGrant.account_id == account.id)))
    result = {"account": account, "identity": identity, "permissions": permissions, "raw_session": raw}
    request._workbench_actor = result
    return result


def require_actor(permission=None):
    def decorate(func):
        @wraps(func)
        def wrapped(*args, **kwargs):
            actor = current_actor()
            if permission and permission not in actor["permissions"]:
                raise ApiError("PERMISSION_DENIED", "没有此工作台管理权限", 403)
            return func(*args, **kwargs)
        return wrapped
    return decorate


@auth.get("/status")
def status():
    enabled = provider().configured
    return jsonify(configured=enabled, login_enabled=enabled, provider="training-platform",
                   message="训练营身份接入已配置" if enabled else "训练营身份接入尚未配置")


@auth.post("/login")
def login():
    same_origin()
    if not provider().configured:
        raise unavailable()
    state, browser, verifier = (secrets.token_urlsafe(32) for _ in range(3))
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    url = provider().authorize(state=state, challenge=challenge, redirect_uri=redirect_uri())
    db.session.add(LoginAttempt(state_digest=digest(state), browser_digest=digest(browser), verifier=verifier,
        expires_at=now() + timedelta(seconds=current_app.config["LOGIN_SECONDS"])))
    db.session.commit()
    response = jsonify(authorization_url=url)
    response.set_cookie(current_app.config["LOGIN_COOKIE_NAME"], browser,
        max_age=current_app.config["LOGIN_SECONDS"], **cookie_options("/api/auth"))
    return response


def consume_attempt():
    state, code = request.args.get("state", ""), request.args.get("code", "")
    browser = request.cookies.get(current_app.config["LOGIN_COOKIE_NAME"], "")
    if not state or not browser or not code or len(state) > 256 or len(code) > 2048:
        raise ApiError("LOGIN_STATE_INVALID", "登录请求已过期或不属于当前浏览器，请重新登录", 400)
    attempt = db.session.get(LoginAttempt, digest(state))
    if (attempt is None or attempt.consumed_at is not None or attempt.expires_at <= now()
            or not hmac.compare_digest(attempt.browser_digest, digest(browser))):
        raise ApiError("LOGIN_STATE_INVALID", "登录请求已过期或不属于当前浏览器，请重新登录", 400)
    verifier = attempt.verifier
    updated = db.session.execute(update(LoginAttempt).where(
        LoginAttempt.state_digest == digest(state), LoginAttempt.consumed_at.is_(None),
        LoginAttempt.expires_at > now()).values(consumed_at=now(), verifier=""))
    if updated.rowcount != 1:
        db.session.rollback()
        raise ApiError("LOGIN_STATE_INVALID", "登录请求已经使用，请重新登录", 400)
    # Commit BEFORE the external exchange: a failed or ambiguous exchange burns the
    # attempt, rather than risking retries with an already consumed upstream code.
    db.session.add(CodeConsumption(code_digest=digest(current_app.config["IDENTITY_ISSUER"] + "\0" + code)))
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise ApiError("CODE_REPLAYED", "登录票据已经使用，请重新登录", 400) from None
    return code, verifier


def map_account(identity):
    if not identity.admitted:
        raise denied()
    person = db.session.scalar(select(Person).where(Person.issuer == identity.issuer, Person.external_id == identity.person_id))
    account = db.session.scalar(select(Account).where(Account.issuer == identity.issuer, Account.subject == identity.subject))
    if ((person and (person.issuer, person.external_id) != (identity.issuer, identity.person_id))
            or (account and (account.issuer, account.subject) != (identity.issuer, identity.subject))):
        raise ApiError("IDENTITY_CHANGED", "身份映射存在冲突，需要人工核对", 403)
    if account and (account.person.external_id != identity.person_id or account.person.issuer != identity.issuer):
        raise ApiError("IDENTITY_CHANGED", "人员关联发生变化，需完成身份核对后重新接入", 403)
    if (person and person.blocked) or (account and account.disabled):
        raise denied()
    if person is None:
        person = Person(issuer=identity.issuer, external_id=identity.person_id)
        db.session.add(person)
        db.session.flush()
    if account is None:
        account = Account(issuer=identity.issuer, subject=identity.subject, person_id=person.id,
                          display_name=identity.display_name)
        db.session.add(account)
        db.session.flush()
    else:
        account.display_name = identity.display_name
    return account


@auth.get("/callback")
def callback():
    try:
        code, verifier = consume_attempt()
        identity = provider().exchange(code=code, verifier=verifier, redirect_uri=redirect_uri())
        account = map_account(identity)
        old_raw = request.cookies.get(current_app.config["SESSION_COOKIE_NAME"], "")
        old_session = db.session.get(Session, digest(old_raw)) if old_raw else None
        if old_session:
            old_session.revoked_at = now()
        raw = secrets.token_urlsafe(32)
        db.session.add(Session(token_digest=digest(raw), account_id=account.id,
            security_version=identity.security_version,
            expires_at=now() + timedelta(seconds=current_app.config["SESSION_SECONDS"])))
        db.session.add(AuditEvent(event="login_succeeded", account_id=account.id,
                                 reason="Training identity and community admission verified"))
        db.session.commit()
        response = redirect("/")
        response.set_cookie(current_app.config["SESSION_COOKIE_NAME"], raw,
            max_age=current_app.config["SESSION_SECONDS"], **cookie_options("/api"))
    except ApiError as exc:
        db.session.rollback()
        response = redirect("/login?error=" + exc.code)
    except IntegrityError:
        db.session.rollback()
        response = redirect("/login?error=LOGIN_RETRY_REQUIRED")
    response.delete_cookie(current_app.config["LOGIN_COOKIE_NAME"], **cookie_options("/api/auth"))
    return response


@auth.get("/me")
@require_actor()
def me():
    actor = current_actor()
    account, identity = actor["account"], actor["identity"]
    return jsonify(actor={"id": account.id, "display_name": identity.display_name,
                          "issuer": account.issuer, "subject": account.subject,
                          "person_id": account.person.external_id},
                   admission={"community_active": True}, permissions=actor["permissions"],
                   csrf_token=csrf_token(actor["raw_session"]))


@auth.post("/logout")
def logout():
    # Local revocation remains available even when the upstream is unavailable or
    # admission has expired. No business data is served by this exception.
    same_origin()
    raw = request.cookies.get(current_app.config["SESSION_COOKIE_NAME"], "")
    expected = csrf_token(raw) if raw else ""
    supplied = request.headers.get("X-CSRF-Token", "")
    if not expected or not hmac.compare_digest(supplied.encode(), expected.encode()):
        raise ApiError("CSRF_REJECTED", "操作校验失败，请刷新工作台后重试", 403)
    session = db.session.get(Session, digest(raw))
    if session and session.revoked_at is None:
        invalidate_session(session, reason="Member requested local logout")
    response = current_app.response_class(status=204)
    response.delete_cookie(current_app.config["SESSION_COOKIE_NAME"], **cookie_options("/api"))
    return response
