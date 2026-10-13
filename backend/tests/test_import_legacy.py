import hashlib,json
import pytest
from workbench.import_legacy import import_snapshot
from workbench.models import Account,PermissionGrant
from workbench.collab.models import WorkWorkspace,WorkAccessGrant
from workbench.extensions import db


def snapshot(tmp_path):
    tables={'directory_user':[{'id':7,'username':'迁移管理员','person_id':2,'status':'active','lifecycle':'active'}],
            'club_group':[{'id':1,'name':'软件组','status':'active','sort_order':0}],
            'club_membership':[{'id':1,'user_id':7,'group_id':1,'slot':'primary','joined_at':'2026-01-01'}],
            'work_workspace':[{'id':9,'club_group_id':1,'status':'active','scope':'group','auto_grant':False}],
            'work_access_grant':[{'id':12,'user_id':7,'role':'coordinator','workspace_id':9,
                'source_type':'membership','source_id':1,'group_id_snapshot':1,'status':'active','origin':'manual',
                'granted_by':7,'grant_reason':'原授权'}]}
    data={'schema_version':1,'issuer':'bme-training','tables':tables,
          'sha256':{n:hashlib.sha256(json.dumps(rows,sort_keys=True,ensure_ascii=False).encode()).hexdigest() for n,rows in tables.items()}}
    path=tmp_path/'snapshot.json';path.write_text(json.dumps(data,ensure_ascii=False));return path,data


def test_import_preserves_ids_and_only_explicit_owner_becomes_admin(app,tmp_path):
    path,_=snapshot(tmp_path)
    with app.app_context():
        assert import_snapshot(path,'7')['work_workspace']==1
        assert Account.query.count()==0
        counts=import_snapshot(path,'7',apply=True)
        assert counts['work_access_grant']==1
        assert db.session.get(WorkWorkspace,9).club_group_id==1
        assert db.session.get(WorkAccessGrant,12).source_id==1
        actor=Account.query.one()
        assert actor.subject=='7' and actor.person.external_id=='2'
        assert {g.permission for g in PermissionGrant.query.all()}=={'governance:view','governance:manage'}
        with pytest.raises(ValueError):import_snapshot(path,'7',apply=True)


def test_changed_snapshot_is_rejected_without_writes(app,tmp_path):
    path,data=snapshot(tmp_path);data['tables']['work_workspace'][0]['club_group_id']=999
    path.write_text(json.dumps(data))
    with app.app_context():
        with pytest.raises(ValueError,match='integrity'):import_snapshot(path,'7',apply=True)
        assert WorkWorkspace.query.count()==0 and Account.query.count()==0
