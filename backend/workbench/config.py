import os
from pathlib import Path


def settings():
    mode = os.getenv("WORKBENCH_ENV", "development")
    lan_http = os.getenv("WORKBENCH_LAN_HTTP", "false").lower() == "true"
    default_db = "sqlite:///" + str(Path(__file__).resolve().parents[1] / "instance" / "workbench.db")
    return {
        "WORKBENCH_ENV": mode,
        "SECRET_KEY": os.getenv("WORKBENCH_SECRET_KEY", ""),
        "SQLALCHEMY_DATABASE_URI": os.getenv("WORKBENCH_DATABASE_URL", default_db),
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        "PUBLIC_ORIGIN": os.getenv("WORKBENCH_PUBLIC_ORIGIN", "http://127.0.0.1:8083"),
        "COOKIE_SECURE": mode == "production" and not lan_http,
        "LAN_HTTP": lan_http,
        "BASE_PATH": os.getenv("WORKBENCH_BASE_PATH", "").rstrip('/'),
        "COLLAB_ENABLED": os.getenv("WORKBENCH_COLLAB_ENABLED", "false").lower() == "true",
        "TRAINING_PUBLIC_URL": os.getenv("TRAINING_PUBLIC_URL", ""),
        "SESSION_COOKIE_NAME": "workbench_session",
        "LOGIN_COOKIE_NAME": "workbench_login",
        "SESSION_SECONDS": 8 * 60 * 60,
        "LOGIN_SECONDS": 5 * 60,
        "IDENTITY_PROVIDER_MODE": os.getenv("IDENTITY_PROVIDER_MODE", "disabled"),
        "IDENTITY_ISSUER": os.getenv("IDENTITY_ISSUER", ""),
        "IDENTITY_CLIENT_ID": os.getenv("IDENTITY_CLIENT_ID", ""),
        "IDENTITY_CLIENT_SECRET": os.getenv("IDENTITY_CLIENT_SECRET", ""),
        "IDENTITY_AUTHORIZE_URL": os.getenv("IDENTITY_AUTHORIZE_URL", ""),
        "IDENTITY_EXCHANGE_URL": os.getenv("IDENTITY_EXCHANGE_URL", ""),
        "IDENTITY_STATUS_URL": os.getenv("IDENTITY_STATUS_URL", ""),
        "MAX_CONTENT_LENGTH": 26 * 1024 * 1024,
        "RATELIMIT_STORAGE_URI": os.getenv('WORKBENCH_RATE_STORAGE', 'memory://'),
        "VERIFY_APPOINTMENTS": os.getenv('WORKBENCH_VERIFY_APPOINTMENTS', 'false').lower() == 'true',
        "WORK_FILE_ROOT": os.getenv('WORKBENCH_FILE_ROOT', str(Path(__file__).resolve().parents[1] / 'instance' / 'files')),
    }
