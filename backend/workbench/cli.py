import click
from flask.cli import with_appcontext
from sqlalchemy import select
from .extensions import db
from .models import Account, AuditEvent, PermissionGrant


@click.command("grant-governance")
@click.option("--issuer", required=True)
@click.option("--subject", required=True)
@click.option("--reason", required=True)
@click.option("--revoke", is_flag=True, help="Revoke instead of granting")
@with_appcontext
def grant_governance(issuer, subject, reason, revoke):
    """Explicit local grant for an account that has already passed admission."""
    if not reason.strip() or len(reason) > 255:
        raise click.ClickException("A non-empty reason of at most 255 characters is required")
    if not issuer or not subject or issuer != issuer.strip() or subject != subject.strip():
        raise click.ClickException("Issuer and subject must be exact non-empty identifiers without outer whitespace")
    account = db.session.scalar(select(Account).where(Account.issuer == issuer, Account.subject == subject))
    if account is None or (account.issuer, account.subject) != (issuer, subject):
        raise click.ClickException("Account must first complete a valid workbench login")
    if not revoke and (account.disabled or account.person.blocked):
        raise click.ClickException("Disabled accounts/persons cannot receive governance access")
    grant = db.session.get(PermissionGrant, (account.id, "governance:view"))
    if revoke and grant:
        db.session.delete(grant)
    elif not revoke and grant is None:
        db.session.add(PermissionGrant(account_id=account.id, permission="governance:view"))
    db.session.add(AuditEvent(event="governance_revoked" if revoke else "governance_granted",
                             account_id=account.id, reason=reason))
    db.session.commit()
    click.echo("Local governance grant updated; no workspace membership was changed.")
