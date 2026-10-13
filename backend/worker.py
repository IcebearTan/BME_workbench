"""One independent reminder/provisioning worker, managed separately from HTTP."""
import signal
import os
import threading
from datetime import timedelta
from pathlib import Path
import requests
from dotenv import load_dotenv
load_dotenv(os.getenv('WORKBENCH_ENV_FILE', str(Path(__file__).parent / '.env')))
from workbench import create_app
from workbench.extensions import db
from workbench.models import LoginAttempt, CodeConsumption, Session, now
from workbench.collab.directory import sync_directory
from workbench.collab.scheduler import _job_reminder_scan, _job_expiration_scan, _job_provision_sync

app=create_app()
stop=threading.Event()
for sig in (signal.SIGINT,signal.SIGTERM):signal.signal(sig,lambda *_:stop.set())
tick=0
while not stop.is_set():
    with app.app_context():
        try:
            cfg=app.config
            if not cfg['COLLAB_ENABLED'] or not app.extensions['identity_provider'].configured:
                raise RuntimeError('Worker requires enabled collaboration and identity integration')
            response=requests.post(cfg['IDENTITY_STATUS_URL'].rsplit('/',1)[0]+'/directory',
                json={'audience':cfg['IDENTITY_CLIENT_ID']},
                auth=(cfg['IDENTITY_CLIENT_ID'],cfg['IDENTITY_CLIENT_SECRET']),timeout=(3,5),allow_redirects=False)
            if response.status_code!=200 or len(response.content)>1024*1024:raise RuntimeError('Directory unavailable')
            sync_directory(response.json()['directory'])
            _job_reminder_scan(app)
            if tick%5==0:_job_expiration_scan(app)
            if tick%1440==0:_job_provision_sync(app)
            if tick%60==0:
                cutoff=now()-timedelta(days=1)
                LoginAttempt.query.filter(LoginAttempt.expires_at<cutoff).delete(synchronize_session=False)
                CodeConsumption.query.filter(CodeConsumption.consumed_at<cutoff).delete(synchronize_session=False)
                Session.query.filter(Session.expires_at<now()-timedelta(days=30)).delete(synchronize_session=False)
                db.session.commit()
        except Exception:
            db.session.rollback()
            app.logger.exception('Work worker cycle failed; will retry without using stale identity')
        finally:db.session.remove()
    tick+=1
    stop.wait(60)
