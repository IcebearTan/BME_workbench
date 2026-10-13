import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(os.getenv('WORKBENCH_ENV_FILE', str(Path(__file__).parent / '.env')))
from workbench import create_app

app = create_app()
