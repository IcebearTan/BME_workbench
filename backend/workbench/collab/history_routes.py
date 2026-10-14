from flask import Blueprint, jsonify, request
from sqlalchemy import or_
from workbench.auth import current_actor
from workbench.errors import ApiError
from workbench.extensions import db
from .compat import jwt_required
from .models import ClubOfficer, ClubOrgEvent, UserModel, InternalGroupMember
from workbench.models import Person
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
    local_person = Person.query.filter_by(issuer=actor['account'].issuer, external_id=str(target.person_id)).first() if target.person_id else None
    local_condition = InternalGroupMember.user_id.in_(ids)
    if local_person:
        local_condition = or_(local_condition, InternalGroupMember.person_id == local_person.id)
    local_records = InternalGroupMember.query.filter(local_condition).all()
    from datetime import date
    for row in local_records:
        years = list(range(row.started_on.year, (row.ended_on or date.today()).year + 1))
        data['years'] = sorted(set(data['years']) | set(years), reverse=True)
        if year is not None and year not in years:
            continue
        operator = db.session.get(UserModel, row.recorded_by)
        local_events = [{'id': f'internal-{row.id}-start', 'kind': 'member_registered',
            'occurred_at': row.recorded_at.isoformat(), 'operator_name': operator.username if operator else None,
            'detail': {'reason': row.reason}}]
        if row.ended_at:
            operator = db.session.get(UserModel, row.ended_by)
            local_events.append({'id': f'internal-{row.id}-end', 'kind': 'member_ended',
                'occurred_at': row.ended_at.isoformat(), 'operator_name': operator.username if operator else None,
                'detail': {'reason': row.end_reason}})
        data['records'].append({'id': f'internal-{row.id}', 'user_id': row.user_id,
            'title': '分管核心' if row.role == 'coordinator' else '小组成员',
            'department': row.group_name_snapshot, 'status': row.status, 'display_status': row.status,
            'term_start': str(row.started_on), 'term_end': str(row.ended_on) if row.ended_on else None,
            'end_reason': row.end_reason, 'record_source': 'internal', 'source_note': row.source_note,
            'years': years, 'date_precision': 'day', 'events': local_events})
    data['records'].sort(key=lambda r: (r['term_start'] or '', str(r['id'])), reverse=True)
    data.update(user_id=target.id, username=target.username,
                people=[{'id': u.id, 'name': u.username} for u in UserModel.query.order_by(UserModel.username, UserModel.id).all()] if governance else [],
                can_select_person=governance)
    return jsonify(code=200, data=data)
