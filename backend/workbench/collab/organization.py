"""Workbench-owned organization. Account permissions are never merged by name."""
import json
from datetime import date, datetime
from flask import current_app
from workbench.extensions import db
from workbench.errors import ApiError
from workbench.models import Account, Person, PermissionGrant, AuditEvent
from .models import UserModel, ClubGroup, InternalGroupMember, WorkWorkspace, WorkAccessGrant
from .services import provisioning


def require_manager(account):
    if account.disabled or account.person.blocked or not db.session.get(PermissionGrant, (account.id, 'governance:manage')):
        raise ApiError('FORBIDDEN', '需要工作台成员管理权限', 403)


def enroll(account, entries, reason, source_note=''):
    require_manager(account)
    if not isinstance(entries, list) or not entries or len(entries) > 200:
        raise ApiError('INVALID_ENTRIES', '一次登记1至200条小组关系', 400)
    if not isinstance(reason, str) or not reason.strip() or len(reason) > 200 or not isinstance(source_note, str) or len(source_note) > 500:
        raise ApiError('INVALID_REASON', '请填写登记原因及有效资料来源', 400)
    normalized = {}
    people = {}
    declared_names = {}
    for entry in entries:
        if not isinstance(entry, dict) or any(type(entry.get(k)) is not int or entry[k] < 1 for k in ('user_id', 'group_id', 'person_id')):
            raise ApiError('INVALID_ENTRY', '请选择已核对的账号、人员和小组', 400)
        group = db.session.get(ClubGroup, entry['group_id'])
        if not group or group.status != 'active' or entry.get('role') not in ('member', 'coordinator'):
            raise ApiError('INVALID_GROUP', '小组已归档或角色不正确', 400)
        workspace = WorkWorkspace.query.filter_by(club_group_id=group.id, scope='group').first()
        if workspace and workspace.status != 'active':
            raise ApiError('WORKSPACE_DISABLED', '该组工作区已停用，请先单独处理工作区状态', 409)
        uid, pid = entry['user_id'], entry['person_id']
        if uid in people and people[uid] != pid:
            raise ApiError('PERSON_CONFLICT', '同一账号不能登记为不同人员', 409)
        people[uid] = pid
        if 'name' in entry:
            name = entry['name']
            if not isinstance(name, str) or not name.strip() or len(name) > 100 or (uid in declared_names and declared_names[uid] != name.strip()):
                raise ApiError('NAME_CONFLICT', '同一账号的姓名不一致', 409)
            declared_names[uid] = name.strip()
        key = (uid, group.id)
        existing = normalized.get(key)
        if existing and existing['role'] != entry['role']:
            raise ApiError('ROLE_CONFLICT', '同一账号同一组的角色存在冲突', 409)
        normalized[key] = entry
    identities = {}
    provider = current_app.extensions['identity_provider']
    if declared_names:
        named_uids = list(declared_names)
        matches = provider.candidates(names=[declared_names[uid] for uid in named_uids])
        if not isinstance(matches, list) or len(matches) != len(named_uids):
            raise ApiError('DIRECTORY_UNAVAILABLE', '姓名匹配响应无效', 503)
        for uid, match in zip(named_uids, matches):
            if (match.get('status') != 'unique_matched' or match.get('resolved_user_id') != uid
                    or match.get('resolved_account', {}).get('eligible') is not True
                    or len(match.get('candidates', [])) != 1 or match['candidates'][0].get('person_id') != people[uid]):
                raise ApiError('MATCH_CHANGED', '认证姓名或正式参与账号已变化，请重新核对名单', 409)
    for uid, pid in people.items():
        known = Account.query.filter_by(issuer=current_app.config['IDENTITY_ISSUER'], subject=str(uid)).first()
        known_person = Person.query.filter_by(issuer=current_app.config['IDENTITY_ISSUER'], external_id=str(pid)).first()
        if known_person and known_person.blocked:
            raise ApiError('PERSON_BLOCKED', '人员已被本地停用，导入不能恢复', 403)
        if known and (known.disabled or known.person.blocked or known.person.external_id != str(pid)):
            raise ApiError('PERSON_CONFLICT', '本地账号被停用或人员标识已变化，需人工处理', 409)
        identity = provider.admit(subject=str(uid), person_id=str(pid), operator_subject=account.subject, reason=reason)
        if (identity.issuer != current_app.config['IDENTITY_ISSUER'] or identity.subject != str(uid)
                or identity.person_id != str(pid) or not identity.admitted):
            raise ApiError('VERIFIED_MEMBER_REQUIRED', '来源未确认有效认证身份', 403)
        identities[uid] = identity
    results = []
    for (uid, gid), entry in normalized.items():
        identity = identities[uid]
        person = Person.query.filter_by(issuer=identity.issuer, external_id=identity.person_id).with_for_update().first()
        if not person:
            person = Person(issuer=identity.issuer, external_id=identity.person_id)
            db.session.add(person)
            db.session.flush()
        if person.blocked:
            raise ApiError('PERSON_BLOCKED', '人员已被本地停用', 403)
        user = db.session.get(UserModel, uid)
        if not user:
            user = UserModel(id=uid, username=identity.display_name, person_id=int(identity.person_id),
                status='active', lifecycle='active', verification_status='verified')
            db.session.add(user)
        else:
            if user.person_id not in (None, int(identity.person_id)):
                raise ApiError('PERSON_CONFLICT', '名录人员标识已变化', 409)
            user.person_id = int(identity.person_id)
            user.username = identity.display_name
            user.verification_status = 'verified'
            user.status, user.lifecycle = 'active', 'active'
        known = Account.query.filter_by(issuer=identity.issuer, subject=identity.subject).first()
        if known is None:
            db.session.add(Account(issuer=identity.issuer, subject=identity.subject,
                                  person_id=person.id, display_name=identity.display_name))
        db.session.flush()
        group = db.session.get(ClubGroup, gid)
        old = InternalGroupMember.query.filter_by(active_key=f'{uid}:{gid}').with_for_update().first()
        if old and old.role == entry['role']:
            results.append({'user_id': uid, 'group_id': gid, 'id': old.id, 'status': 'unchanged'})
            continue
        if old:
            old.status, old.active_key = 'ended', None
            old.ended_on, old.ended_at, old.ended_by = date.today(), datetime.now(), int(account.subject)
            old.end_reason = '角色调整：' + reason[:190]
            db.session.flush()
        row = InternalGroupMember(user_id=uid, person_id=person.id, group_id=gid, role=entry['role'],
            status='active', active_key=f'{uid}:{gid}', started_on=date.today(), recorded_by=int(account.subject),
            reason=reason, source_note=source_note, group_name_snapshot=group.name)
        db.session.add(row)
        db.session.flush()
        ws = WorkWorkspace.query.filter_by(club_group_id=gid, scope='group', status='active').first()
        if not ws:
            ws = WorkWorkspace(club_group_id=gid, scope='group', status='active', auto_grant=True)
            db.session.add(ws)
            db.session.flush()
        # Import is an explicit local assignment; preserve person vetoes and manual grants.
        from .services.access import grant_status_reason
        grants = WorkAccessGrant.query.filter_by(user_id=uid, workspace_id=ws.id, status='active').all()
        if any(g.role == 'coordinator' and grant_status_reason(g)[0] for g in grants) and row.role == 'member':
            results.append({'user_id': uid, 'group_id': gid, 'id': row.id, 'status': 'created', 'grant_status': 'existing'})
        else:
            from .enforcement import workspace_denied
            denied = workspace_denied(user, ws.id)[0] or bool(WorkAccessGrant.query.filter_by(user_id=uid, workspace_id=ws.id, status='vetoed').first())
            if not denied:
                db.session.add(WorkAccessGrant(user_id=uid, workspace_id=ws.id, role=row.role,
                    source_type='internal_membership', source_id=row.id, group_id_snapshot=gid,
                    status='active', origin='manual', granted_by=int(account.subject), grant_reason=reason))
            results.append({'user_id': uid, 'group_id': gid, 'id': row.id, 'status': 'created', 'grant_status': 'vetoed' if denied else 'granted'})
        db.session.add(AuditEvent(event='internal_membership_registered', account_id=account.id,
            reason=f'关系#{row.id} 账号#{uid} 小组#{gid} {row.role}：{reason}'[:255]))
    return results


def end_member(account, row_id, reason):
    require_manager(account)
    if not isinstance(reason, str) or not reason.strip() or len(reason) > 200:
        raise ApiError('INVALID_REASON', '请填写结束原因', 400)
    row = db.session.get(InternalGroupMember, row_id)
    if not row:
        raise ApiError('NOT_FOUND', '成员关系不存在', 404)
    if row.status == 'ended':
        return row
    row.status, row.active_key = 'ended', None
    row.ended_on, row.ended_at, row.ended_by = date.today(), datetime.now(), int(account.subject)
    row.end_reason = reason
    db.session.add(AuditEvent(event='internal_membership_ended', account_id=account.id,
        reason=json.dumps({'membership_id': row.id, 'reason': reason}, ensure_ascii=False)))
    return row
