from flask import Blueprint, jsonify, request, current_app
from workbench.auth import current_actor
from workbench.extensions import db
from workbench.models import Person
from .compat import jwt_required
from .models import InternalGroupMember, ClubGroup, UserModel
from .organization import require_manager, enroll, end_member
bp = Blueprint('internal_organization', __name__, url_prefix='/api/admin/organization')


@bp.get('/members')
@jwt_required()
def members():
    actor = current_actor()['account']
    require_manager(actor)
    rows = InternalGroupMember.query.order_by(InternalGroupMember.id.desc()).all()
    return jsonify(code=200, data={'members': [{'id': r.id, 'user_id': r.user_id,
        'username': db.session.get(UserModel, r.user_id).username, 'person_id': db.session.get(Person, r.person_id).external_id,
        'group_id': r.group_id, 'group_name': r.group_name_snapshot, 'role': r.role, 'status': r.status,
        'started_on': str(r.started_on), 'ended_on': str(r.ended_on) if r.ended_on else None,
        'source_note': r.source_note} for r in rows],
        'groups': [{'id': g.id, 'name': g.name} for g in ClubGroup.query.filter_by(status='active').all()]})


@bp.post('/candidates')
@jwt_required()
def candidates():
    require_manager(current_actor()['account'])
    body = request.get_json(silent=True) or {}
    names = body.get('names')
    if not isinstance(names, list) or not names or len(names) > 200 or any(not isinstance(n, str) or len(n) > 100 for n in names):
        from workbench.errors import ApiError
        raise ApiError('INVALID_NAMES', '请输入至多200个姓名', 400)
    return jsonify(code=200, data={'matches': current_app.extensions['identity_provider'].candidates(names=names)})


@bp.post('/members')
@jwt_required()
def register_members():
    body = request.get_json(silent=True) or {}
    try:
        results = enroll(current_actor()['account'], body.get('entries'), body.get('reason'), body.get('source_note', ''))
        db.session.commit()
        return jsonify(code=200, data={'results': results})
    except Exception:
        db.session.rollback()
        raise


@bp.post('/members/<int:row_id>/end')
@jwt_required()
def retire_member(row_id):
    row = end_member(current_actor()['account'], row_id, (request.get_json(silent=True) or {}).get('reason'))
    db.session.commit()
    return jsonify(code=200, data={'id': row.id, 'status': row.status})
