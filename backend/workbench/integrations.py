import hmac,re
from flask import Blueprint, current_app, request, jsonify
from sqlalchemy import or_
from .extensions import db
from .models import Account, PermissionGrant, Person
from .collab.models import WorkItem, WorkAccessGrant, WorkItemParticipant, WorkFile, WorkReply, WorkEvent, WorkSubmission, PersonWorkspaceRestrictionModel, UserModel, InternalGroupMember

bp=Blueprint('workbench_integrations',__name__,url_prefix='/api/integrations')


@bp.post('/group-usage')
def group_usage():
    auth=request.authorization
    cfg=current_app.config
    if (not auth or not cfg.get('IDENTITY_CLIENT_SECRET') or auth.type.lower()!='basic'
        or not hmac.compare_digest((auth.username or '').encode(),cfg['IDENTITY_CLIENT_ID'].encode())
        or not hmac.compare_digest((auth.password or '').encode(),cfg['IDENTITY_CLIENT_SECRET'].encode())):
        return jsonify(error='INVALID_CLIENT'),401
    gid=(request.get_json(silent=True) or {}).get('group_id')
    if type(gid) is not int or gid<1:return jsonify(error='INVALID_GROUP'),400
    from .collab.models import WorkWorkspace
    count=WorkItem.query.join(WorkWorkspace,WorkWorkspace.id==WorkItem.workspace_id).filter(
        WorkWorkspace.club_group_id==gid, WorkItem.status.in_(('draft','open','todo','in_progress','blocked','review'))).count()
    return jsonify(group_id=gid,open_items=count,workspaces=WorkWorkspace.query.filter_by(club_group_id=gid).count())


@bp.post('/account-usage')
def account_usage():
    auth=request.authorization
    cfg=current_app.config
    if (not auth or not cfg.get('IDENTITY_CLIENT_SECRET') or auth.type.lower()!='basic'
        or not hmac.compare_digest((auth.username or '').encode(),cfg['IDENTITY_CLIENT_ID'].encode())
        or not hmac.compare_digest((auth.password or '').encode(),cfg['IDENTITY_CLIENT_SECRET'].encode())):
        return jsonify(error='INVALID_CLIENT'),401
    body=request.get_json(silent=True) or {}
    subject=body.get('subject')
    if body.get('issuer')!=cfg['IDENTITY_ISSUER'] or not isinstance(subject,str) or not re.fullmatch(r'[1-9][0-9]{0,10}',subject):
        return jsonify(error='INVALID_SUBJECT'),400
    uid=int(subject)
    person_id=body.get('person_id')
    account=Account.query.filter_by(issuer=cfg['IDENTITY_ISSUER'],subject=subject).first()
    if person_id is None and account:
        person_id=account.person.external_id
    if person_id is not None and (not isinstance(person_id,str) or not re.fullmatch(r'[1-9][0-9]{0,10}',person_id)):
        return jsonify(error='INVALID_PERSON'),400
    uids={uid}
    if person_id:
        uids.update(row.id for row in UserModel.query.filter_by(person_id=int(person_id)).all())
    counts={name:model.query.filter(getattr(model,column).in_(uids)).count() for name,model,column in [
        ('items',WorkItem,'created_by'),('grants',WorkAccessGrant,'user_id'),
        ('participants',WorkItemParticipant,'user_id'),('files',WorkFile,'created_by'),
        ('replies',WorkReply,'author_id'),('events',WorkEvent,'actor_user_id'),('submissions',WorkSubmission,'submitted_by'),
        ('internal_memberships',InternalGroupMember,'user_id')]}
    counts['governance']=PermissionGrant.query.filter_by(account_id=account.id).count() if account else 0
    if person_id:
        counts['person_restrictions']=PersonWorkspaceRestrictionModel.query.filter_by(person_id=int(person_id)).count()
        person=Person.query.filter_by(issuer=cfg['IDENTITY_ISSUER'],external_id=person_id).first()
        counts['person_blocked']=int(bool(person and person.blocked))
        if person:
            accounts=db.session.query(Account.id).filter_by(person_id=person.id)
            counts['person_governance']=PermissionGrant.query.filter(PermissionGrant.account_id.in_(accounts)).count()
    return jsonify(subject=subject,has_business_data=any(counts.values()),counts=counts)
