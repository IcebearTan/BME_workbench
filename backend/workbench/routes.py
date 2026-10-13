from flask import Blueprint, jsonify
from sqlalchemy import func, select
from .auth import current_actor, require_actor
from .extensions import db
from .models import Account, Membership, PersonRestriction, Workspace

api = Blueprint("api", __name__, url_prefix="/api")


@api.get("/health")
def health():
    return jsonify(status="ok", service="bme-workbench")


@api.get("/workspaces")
@require_actor()
def workspaces():
    from flask import current_app
    if current_app.config.get('COLLAB_ENABLED'):
        from .collab.compat import _current_user
        from .collab.models import WorkWorkspace, ClubGroup
        from .collab.services.access import workspace_access
        visible = workspace_access(_current_user())
        return jsonify(items=[{'id': w.id, 'name': (db.session.get(ClubGroup, w.club_group_id).name if w.club_group_id else '社团工作区'), 'role': visible[w.id]}
            for w in WorkWorkspace.query.filter(WorkWorkspace.id.in_(visible)).all()])
    account = current_actor()["account"]
    restricted = select(PersonRestriction.workspace_id).where(PersonRestriction.person_id == account.person_id)
    rows = db.session.execute(select(Workspace, Membership.role)
        .join(Membership, Membership.workspace_id == Workspace.id)
        .where(Membership.account_id == account.id, Workspace.id.not_in(restricted))
        .order_by(Workspace.id)).all()
    return jsonify(items=[{"id": workspace.id, "name": workspace.name, "role": role} for workspace, role in rows])


@api.get("/admin/overview")
@require_actor("governance:view")
def overview():
    # Governance is metadata-only. This grant confers no workspace membership.
    from flask import current_app
    if current_app.config.get('COLLAB_ENABLED'):
        from .collab.models import WorkWorkspace
        return jsonify(members=db.session.scalar(select(func.count()).select_from(Account)), workspaces=WorkWorkspace.query.count(), scope='workbench')
    return jsonify(members=db.session.scalar(select(func.count()).select_from(Account)),
                   workspaces=db.session.scalar(select(func.count()).select_from(Workspace)), scope="workbench")
