from datetime import date
from flask import Blueprint, jsonify, request
from workbench.extensions import db
from .compat import jwt_required, _current_user
from .models import ClubGroup, ClubOfficer, ClubMembership, UserModel
from .services.access import require_governance

bp = Blueprint('workbench_directory', __name__, url_prefix='/api')


@bp.get('/user/user_list')
@jwt_required()
def candidates():
    require_governance(_current_user())
    return jsonify([{'User_Id': u.id, 'User_Name': u.username} for u in UserModel.query.filter_by(status='active', lifecycle='active').all()])


@bp.get('/admin/club/groups')
@jwt_required()
def groups():
    require_governance(_current_user())
    return jsonify(code=200, data={'groups': [{'id': g.id, 'name': g.name, 'parent_id': g.parent_id,
        'status': g.status, 'sort_order': g.sort_order} for g in ClubGroup.query.order_by(ClubGroup.sort_order).all()]})


@bp.get('/admin/officers')
@jwt_required()
def officers():
    require_governance(_current_user())
    rows = ClubOfficer.query.filter_by(status='active').all()
    return jsonify(code=200, data={'officers': [{'id': o.id, 'user_id': o.user_id, 'title': o.title,
        'department': o.department, 'group_id': o.group_id} for o in rows], 'total': len(rows)})


@bp.get('/admin/club/membership/<int:uid>')
@jwt_required()
def membership(uid):
    require_governance(_current_user())
    result = {'primary': None, 'secondary': None}
    for row in ClubMembership.query.filter_by(user_id=uid).all():
        group = db.session.get(ClubGroup, row.group_id)
        result[row.slot] = {'membership_id': row.id, 'id': row.group_id, 'name': group.name if group else ''}
    return jsonify(code=200, data=result)


@bp.get('/organization')
@jwt_required()
def organization():
    users = {u.id: u for u in UserModel.query.all()}
    today = date.today()
    active = [o for o in ClubOfficer.query.filter_by(status='active').all()
              if o.term_start <= today and (o.term_end is None or o.term_end >= today)]
    def person(uid, officer=None):
        user = users.get(uid)
        return {'id': uid, 'username': user.username if user else '历史成员',
                'avatar_url': user.avatar_url if user else None, 'title': officer.title if officer else None}
    nodes = {g.id: {'id': g.id, 'name': g.name, 'description': g.description,
                    'parent_id': g.parent_id, 'members': [], 'children': []}
             for g in ClubGroup.query.filter_by(status='active').order_by(ClubGroup.sort_order).all()}
    by_user = {o.user_id: o for o in active}
    for member in ClubMembership.query.all():
        if member.group_id in nodes:
            nodes[member.group_id]['members'].append(person(member.user_id, by_user.get(member.user_id)))
    for officer in active:
        if officer.group_id in nodes and officer.user_id not in {u['id'] for u in nodes[officer.group_id]['members']}:
            nodes[officer.group_id]['members'].append(person(officer.user_id, officer))
    tree = []
    for node in nodes.values():
        parent = nodes.get(node['parent_id'])
        (parent['children'] if parent else tree).append(node)
    return jsonify(code=200, data={'president': None, 'management': [person(o.user_id, o) for o in active if o.group_id is None], 'tree': tree})
