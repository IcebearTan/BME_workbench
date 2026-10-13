from .models import PersonWorkspaceRestrictionModel
from workbench.extensions import db


def workspace_denied(user, workspace_id):
    if user.lifecycle != 'active' or user.status != 'active':
        return True, '账号已失效'
    if user.person_id:
        restriction = db.session.get(PersonWorkspaceRestrictionModel, (user.person_id, workspace_id))
        if restriction and restriction.state == 'vetoed':
            return True, '该人员的工作区访问已被否决'
    return False, None
