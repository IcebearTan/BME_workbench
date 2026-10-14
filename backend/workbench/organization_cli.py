import json
from pathlib import Path
import click
from flask import current_app
from .extensions import db
from .models import Account
from .collab.organization import require_manager, enroll


def register(app):
    @app.cli.command('import-organization')
    @click.argument('payload', type=click.Path(exists=True, dir_okay=False))
    @click.option('--operator-subject', required=True)
    @click.option('--apply', is_flag=True, default=False)
    @click.option('--result', type=click.Path(dir_okay=False))
    def import_organization(payload, operator_subject, apply, result):
        """Preview a roster count or explicitly register qualified memberships."""
        data = json.loads(Path(payload).read_text())
        actor = Account.query.filter_by(issuer=current_app.config['IDENTITY_ISSUER'], subject=operator_subject).first()
        if actor is None:
            raise click.ClickException('Operator account is not registered in this workbench')
        require_manager(actor)
        if not apply:
            click.echo(json.dumps({'apply': False, 'relations': len(data.get('entries', [])),
                'users': len({e['user_id'] for e in data.get('entries', [])})}))
            return
        try:
            results = enroll(actor, data.get('entries'), data.get('reason'), data.get('source_note', ''))
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise
        output = json.dumps({'results': results}, ensure_ascii=False, indent=2)
        if result:
            destination = Path(result)
            destination.write_text(output)
            destination.chmod(0o600)
        click.echo(json.dumps({'relations': len(results), 'created': sum(r['status'] == 'created' for r in results),
            'unchanged': sum(r['status'] == 'unchanged' for r in results), 'vetoed': sum(r.get('grant_status') == 'vetoed' for r in results)}))
