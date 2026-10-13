from datetime import datetime
from flask import Blueprint, jsonify
from workbench.extensions import db
from .compat import jwt_required, _current_user


class WorkNotification(db.Model):
    __tablename__ = 'work_notification'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text)
    source_type = db.Column(db.String(32))
    source_id = db.Column(db.Integer)
    is_read = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=datetime.now)


def create_notification(user_id, title, content, *, source_type=None, source_id=None, **_):
    row = WorkNotification(user_id=user_id, title=title, content=content,
                           source_type=source_type, source_id=source_id)
    db.session.add(row)
    return row


bp = Blueprint('workbench_notifications', __name__, url_prefix='/api/notifications')


@bp.get('')
@jwt_required()
def inbox():
    uid = _current_user().id
    rows = WorkNotification.query.filter_by(user_id=uid).order_by(WorkNotification.id.desc()).limit(100).all()
    return jsonify(items=[{'id': r.id, 'title': r.title, 'content': r.content, 'source_type': r.source_type,
                           'source_id': r.source_id, 'is_read': r.is_read,
                           'created_at': r.created_at.isoformat()} for r in rows],
                   unread=WorkNotification.query.filter_by(user_id=uid, is_read=False).count())


@bp.post('/<int:nid>/read')
@jwt_required()
def mark_read(nid):
    row = WorkNotification.query.filter_by(id=nid, user_id=_current_user().id).first_or_404()
    row.is_read = True
    db.session.commit()
    return jsonify(ok=True)
