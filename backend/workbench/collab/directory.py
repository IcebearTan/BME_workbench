"""Read-only source organization projection; work grants remain locally owned."""
from datetime import date, datetime
from sqlalchemy import Date, DateTime
from workbench.extensions import db
from workbench.errors import ApiError
from .models import ClubGroup, ClubMembership, ClubOfficer, ClubPosition, UserModel

MODELS = {'users': UserModel, 'groups': ClubGroup, 'positions': ClubPosition,
          'officers': ClubOfficer, 'memberships': ClubMembership}


def sync_directory(snapshot):
    if not isinstance(snapshot, dict) or any(not isinstance(snapshot.get(k), list) for k in MODELS):
        raise ApiError('DIRECTORY_UNAVAILABLE', '组织目录响应无效', 503)
    changed = False
    for key, model in MODELS.items():
        for record in snapshot[key]:
            if not isinstance(record, dict) or type(record.get('id')) is not int:
                raise ApiError('DIRECTORY_UNAVAILABLE', '组织目录标识无效', 503)
            row = db.session.get(model, record['id'])
            if row is None:
                changed = True
                row = model(id=record['id'])
                db.session.add(row)
            for column in model.__table__.columns:
                if column.name not in record or column.name == 'id':
                    continue
                value = record[column.name]
                if value is not None and isinstance(column.type, DateTime):
                    value = datetime.fromisoformat(value)
                elif value is not None and isinstance(column.type, Date):
                    value = date.fromisoformat(value)
                if getattr(row, column.name) != value:
                    setattr(row, column.name, value)
                    changed = True
        db.session.flush()
    member_ids = [r['id'] for r in snapshot['memberships']]
    changed = bool(ClubMembership.query.filter(ClubMembership.id.not_in(member_ids)).delete(synchronize_session=False)) or changed
    officer_ids = [r['id'] for r in snapshot['officers']]
    changed = bool(ClubOfficer.query.filter(ClubOfficer.id.not_in(officer_ids), ClubOfficer.status != 'ended').update({'status': 'ended'}, synchronize_session=False)) or changed
    if changed:
        from .services.provisioning import backfill_all
        backfill_all()
    db.session.commit()
