from flask import Blueprint, jsonify, request
from sqlalchemy import or_
from workbench.auth import current_actor
from workbench.errors import ApiError
from workbench.extensions import db
from .compat import jwt_required
from .models import ClubOfficer, ClubOrgEvent, UserModel
from .history_format import serialize_history

bp = Blueprint('appointment_history', __name__, url_prefix='/api/appointments')


@bp.get('/history')
@jwt_required()
def history():
    actor = current_actor()
    subject = actor['account'].subject
    user_id = request.args.get('user_id', subject)
    if not str(user_id).isdecimal():
        raise ApiError('INVALID_USER', '用户标识不正确', 400)
    target = db.session.get(UserModel, int(user_id))
    if not target:
        raise ApiError('NOT_FOUND', '人员名录尚未同步或用户不存在', 404)
    own = target.person_id is not None and str(target.person_id) == actor['account'].person.external_id
    governance = bool({'governance:view', 'governance:manage'} & set(actor['permissions']))
    if not own and not governance:
        raise ApiError('FORBIDDEN', '仅能查看自己的任职履历', 403)
    year = request.args.get('year', type=int)
    if 'year' in request.args and (year is None or not 1900 <= year <= 9999):
        raise ApiError('INVALID_YEAR', '年份格式不正确', 400)
    related = UserModel.query.filter_by(person_id=target.person_id).all() if target.person_id else [target]
    ids = [u.id for u in related]
    condition = ClubOfficer.user_id.in_(ids)
    if target.person_id:
        condition = or_(condition, ClubOfficer.person_id == target.person_id)
    records = ClubOfficer.query.filter(condition).all()
    record_ids = [r.id for r in records]
    events = ClubOrgEvent.query.filter(ClubOrgEvent.officer_id.in_(record_ids)).order_by(ClubOrgEvent.occurred_at, ClubOrgEvent.id).all() if record_ids else []
    operator_ids = {e.operator_id for e in events if e.operator_id}
    names = {u.id: u.username for u in UserModel.query.filter(UserModel.id.in_(operator_ids)).all()} if operator_ids else {}
    data = serialize_history(records, events, year, names)
    data.update(user_id=target.id, username=target.username,
                people=[{'id': u.id, 'name': u.username} for u in UserModel.query.order_by(UserModel.username, UserModel.id).all()] if governance else [],
                can_select_person=governance)
    return jsonify(code=200, data=data)
