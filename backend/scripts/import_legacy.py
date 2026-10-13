import argparse,json,sys,os
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from dotenv import load_dotenv
load_dotenv(os.getenv('WORKBENCH_ENV_FILE', str(Path(__file__).resolve().parents[1]/'.env')))
from workbench import create_app
from workbench.extensions import db
from workbench.import_legacy import import_snapshot

parser=argparse.ArgumentParser(description='Validate snapshot by default; --apply imports into empty work tables.')
parser.add_argument('snapshot');parser.add_argument('--administrator-subject',required=True);parser.add_argument('--apply',action='store_true')
args=parser.parse_args()
with create_app().app_context():
    try:print(json.dumps(import_snapshot(args.snapshot,args.administrator_subject,apply=args.apply)))
    except Exception:
        db.session.rollback();raise
