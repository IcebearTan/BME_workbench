"""Only workbench-owned records. No cross-database foreign keys or passwords."""
from datetime import datetime, timezone
from sqlalchemy.dialects.mysql import VARCHAR
from .extensions import db


def identity_string(length):
    return db.String(length).with_variant(VARCHAR(length, collation="utf8mb4_bin"), "mysql")


def now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Person(db.Model):
    __tablename__ = "person"
    id = db.Column(db.Integer, primary_key=True)
    issuer = db.Column(identity_string(255), nullable=False)
    external_id = db.Column(identity_string(128), nullable=False)
    blocked = db.Column(db.Boolean, nullable=False, default=False)
    __table_args__ = (db.UniqueConstraint("issuer", "external_id"),)


class Account(db.Model):
    __tablename__ = "account"
    id = db.Column(db.Integer, primary_key=True)
    issuer = db.Column(identity_string(255), nullable=False)
    subject = db.Column(identity_string(128), nullable=False)
    person_id = db.Column(db.Integer, db.ForeignKey("person.id"), nullable=False)
    display_name = db.Column(db.String(100), nullable=False)
    disabled = db.Column(db.Boolean, nullable=False, default=False)
    person = db.relationship(Person)
    __table_args__ = (db.UniqueConstraint("issuer", "subject"),)


class LoginAttempt(db.Model):
    __tablename__ = "login_attempt"
    state_digest = db.Column(db.String(64), primary_key=True)
    browser_digest = db.Column(db.String(64), nullable=False)
    verifier = db.Column(db.String(128), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    consumed_at = db.Column(db.DateTime)


class CodeConsumption(db.Model):
    __tablename__ = "code_consumption"
    code_digest = db.Column(db.String(64), primary_key=True)
    consumed_at = db.Column(db.DateTime, nullable=False, default=now)


class Session(db.Model):
    __tablename__ = "work_session"
    token_digest = db.Column(db.String(64), primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey("account.id"), nullable=False)
    security_version = db.Column(db.String(64), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    revoked_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, nullable=False, default=now)
    account = db.relationship(Account)


class Workspace(db.Model):
    __tablename__ = "workspace"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)


class Membership(db.Model):
    __tablename__ = "membership"
    account_id = db.Column(db.Integer, db.ForeignKey("account.id"), primary_key=True)
    workspace_id = db.Column(db.Integer, db.ForeignKey("workspace.id"), primary_key=True)
    role = db.Column(db.String(20), nullable=False, default="member")
    __table_args__ = (db.CheckConstraint("role IN ('member', 'coordinator')", name="role"),)


class PersonRestriction(db.Model):
    __tablename__ = "person_restriction"
    person_id = db.Column(db.Integer, db.ForeignKey("person.id"), primary_key=True)
    workspace_id = db.Column(db.Integer, db.ForeignKey("workspace.id"), primary_key=True)
    reason = db.Column(db.String(255), nullable=False)


class PermissionGrant(db.Model):
    __tablename__ = "permission_grant"
    account_id = db.Column(db.Integer, db.ForeignKey("account.id"), primary_key=True)
    permission = db.Column(db.String(64), primary_key=True)
    created_at = db.Column(db.DateTime, nullable=False, default=now)
    __table_args__ = (db.CheckConstraint("permission = 'governance:view'", name="permission"),)


class AuditEvent(db.Model):
    __tablename__ = "audit_event"
    id = db.Column(db.Integer, primary_key=True)
    event = db.Column(db.String(64), nullable=False)
    account_id = db.Column(db.Integer, db.ForeignKey("account.id"))
    reason = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=now)
