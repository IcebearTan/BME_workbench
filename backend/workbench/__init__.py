from pathlib import Path
from urllib.parse import urlsplit
from flask import Flask, jsonify
from sqlalchemy import event
from sqlalchemy.engine import Engine
from .config import settings
from .errors import ApiError
from .extensions import db, migrate, limiter
from .provider import DisabledProvider, HttpIdentityProvider
from .transport import lan_url


@event.listens_for(Engine, "connect")
def enable_sqlite_foreign_keys(connection, _record):
    if connection.__class__.__module__.startswith("sqlite3"):
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def create_app(test_config=None, identity_provider=None):
    app = Flask(__name__)
    app.config.from_mapping(settings())
    if test_config:
        app.config.update(test_config)
    if app.config["WORKBENCH_ENV"] not in ("development", "production", "test"):
        raise ValueError("WORKBENCH_ENV must be development, production or test")
    if not app.secret_key or len(app.secret_key) < 32:
        raise ValueError("Set WORKBENCH_SECRET_KEY to an independently generated secret of at least 32 characters")
    origin = urlsplit(app.config["PUBLIC_ORIGIN"])
    if (origin.scheme not in ("http", "https") or not origin.netloc or origin.path
            or origin.query or origin.fragment or origin.username):
        raise ValueError("WORKBENCH_PUBLIC_ORIGIN must be an origin without path or trailing slash")
    if app.config["WORKBENCH_ENV"] == "production":
        campus_http = app.config.get('LAN_HTTP') and lan_url(app.config['PUBLIC_ORIGIN'])
        if not campus_http and (origin.scheme != "https" or not app.config["COOKIE_SECURE"]):
            raise ValueError("Production requires HTTPS and secure cookies")
        if not app.config["SQLALCHEMY_DATABASE_URI"].startswith("mysql+pymysql://"):
            raise ValueError("Production requires an explicitly configured independent MySQL database")
    if identity_provider is not None and not app.testing:
        raise ValueError("Injected identity providers are available only in tests")
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    Path(__file__).resolve().parents[1].joinpath("instance").mkdir(exist_ok=True)
    db.init_app(app)
    base = app.config.get('BASE_PATH', '')
    if base and (not base.startswith('/') or '..' in base or '//' in base or not all(c.isalnum() or c in '/-_' for c in base)):
        raise ValueError('Invalid WORKBENCH_BASE_PATH')
    migrate.init_app(app, db)
    app.config['RATELIMIT_ENABLED'] = not app.testing
    limiter.init_app(app)
    mode = app.config["IDENTITY_PROVIDER_MODE"]
    if mode not in ("disabled", "http"):
        raise ValueError("IDENTITY_PROVIDER_MODE must be disabled or http")
    app.extensions["identity_provider"] = identity_provider or (
        HttpIdentityProvider(app.config) if mode == "http" else DisabledProvider())
    from .auth import auth
    from .routes import api
    from .cli import grant_governance
    app.register_blueprint(auth)
    app.register_blueprint(api)
    app.cli.add_command(grant_governance)
    from .collab.blueprints.work import bp as work_bp
    from .collab.blueprints.work_files import bp as files_bp
    from .collab.notifications import bp as notifications_bp
    from .collab.directory_routes import bp as directory_bp
    app.register_blueprint(work_bp)
    app.register_blueprint(files_bp)
    app.register_blueprint(notifications_bp)
    app.register_blueprint(directory_bp)
    from .collab.history_routes import bp as history_bp
    app.register_blueprint(history_bp)
    from .integrations import bp as integrations_bp
    app.register_blueprint(integrations_bp)

    @app.errorhandler(ApiError)
    def api_error(exc):
        return jsonify(error={"code": exc.code, "message": exc.message}), exc.status

    @app.after_request
    def security_headers(response):
        response.headers["Cache-Control"] = "no-store"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    return app
