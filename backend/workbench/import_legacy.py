"""Explicit, transactional import into an empty independent work database."""
import hashlib
import json
from datetime import date, datetime
from pathlib import Path
from sqlalchemy import Date, DateTime, Boolean, select, func
from .extensions import db
from .models import Account, Person, PermissionGrant, AuditEvent
from .collab import models as domain
from .collab.notifications import WorkNotification


def import_snapshot(path, administrator_subject, *, apply=False):
    data=json.loads(Path(path).read_text())
    if data.get('schema_version') != 1 or data.get('issuer') != 'bme-training':
        raise ValueError('Unsupported source schema/issuer')
    tables=data['tables']
    if Account.query.count() or Person.query.count():
        raise ValueError('Target identity tables must be empty before the initial migration')
    allowed={m.__table__.name:m.__table__ for m in vars(domain).values() if isinstance(m,type) and hasattr(m,'__table__')}
    allowed['work_notification']=WorkNotification.__table__
    if set(tables)-set(allowed): raise ValueError('Unexpected source tables')
    for name, rows in tables.items():
        digest=hashlib.sha256(json.dumps(rows,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
        if digest != data['sha256'].get(name):raise ValueError('Snapshot integrity mismatch: '+name)
        if db.session.scalar(select(func.count()).select_from(allowed[name])):
            raise ValueError('Target must be empty: '+name)
    users=tables.get('directory_user',[])
    owner=next((u for u in users if str(u['id'])==administrator_subject),None)
    if not owner or not owner.get('person_id'):raise ValueError('Administrator must exist in the exported identity projection')
    if not apply:return {n:len(rows) for n,rows in tables.items()}
    for table in db.metadata.sorted_tables:
        if table.name not in tables:continue
        for raw in tables[table.name]:
            row={}
            for col in table.columns:
                if col.name not in raw:continue
                value=raw[col.name]
                if value is not None and isinstance(col.type,DateTime):value=datetime.fromisoformat(value)
                elif value is not None and isinstance(col.type,Date):value=date.fromisoformat(value)
                elif value is not None and isinstance(col.type,Boolean):value=bool(value)
                row[col.name]=value
            db.session.execute(table.insert().values(**row))
    persons={}
    for user in users:
        pid=user.get('person_id')
        if not pid:continue
        person=persons.get(pid)
        if person is None:
            person=Person(issuer=data['issuer'],external_id=str(pid))
            db.session.add(person);db.session.flush();persons[pid]=person
        account=Account(issuer=data['issuer'],subject=str(user['id']),person_id=person.id,
                        display_name=user['username'],disabled=(user.get('lifecycle') or 'active')!='active' or (user.get('status') or 'active')!='active')
        db.session.add(account);db.session.flush()
        if str(user['id'])==administrator_subject:
            for permission in ['governance:view','governance:manage']:
                db.session.add(PermissionGrant(account_id=account.id,permission=permission))
            db.session.add(AuditEvent(event='governance_migration',account_id=account.id,
                reason='Project owner explicitly designated this account as the first administrator on 2026-10-13'))
    actual={name:db.session.scalar(select(func.count()).select_from(allowed[name])) for name in tables}
    if actual != {n:len(r) for n,r in tables.items()}:raise ValueError('Imported row counts differ')
    db.session.commit()
    return actual
