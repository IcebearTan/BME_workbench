"""Work-domain adapters using independent workbench sessions, not training JWTs."""
import hmac
from functools import wraps
from flask import current_app, request
from workbench.auth import current_actor, csrf_token, same_origin
from workbench.errors import ApiError
from workbench.extensions import db, limiter
from workbench.models import AuditEvent
from .models import UserModel


def _current_user():
    subject = current_actor()['account'].subject
    user = db.session.get(UserModel, int(subject)) if subject.isdecimal() else None
    if not user:
        raise ApiError('DIRECTORY_UNAVAILABLE', '组织名录尚未同步，请重试', 503)
    return user


def jwt_required():
    def decorate(func):
        @wraps(func)
        def wrapped(*args, **kwargs):
            if not current_app.config.get('COLLAB_ENABLED'):
                raise ApiError('COLLAB_UNAVAILABLE', '协作功能尚未启用', 503)
            actor = current_actor()
            if request.method not in ('GET', 'HEAD', 'OPTIONS'):
                same_origin()
                expected = csrf_token(actor['raw_session'])
                actual = request.headers.get('X-CSRF-Token', '')
                if not hmac.compare_digest(actual.encode(), expected.encode()):
                    raise ApiError('CSRF_REJECTED', '操作校验失败，请刷新后重试', 403)
            return func(*args, **kwargs)
        return wrapped
    return decorate


def audit_log(operation=None, **_):
    def decorate(func):
        @wraps(func)
        def wrapped(*args, **kwargs):
            result = func(*args, **kwargs)
            if current_app.make_response(result).status_code < 400:
                db.session.add(AuditEvent(event='collaboration_governance',
                    account_id=current_actor()['account'].id, reason=(operation or func.__name__)[:255]))
                db.session.commit()
            return result
        return wrapped
    return decorate
