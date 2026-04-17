from flask import Flask

from app.config import config_by_name
from app.extensions import init_extensions
from app.routes.auth import auth_bp
from app.routes.health import health_bp
from app.routes.reports import reports_bp
from app.routes.roles import roles_bp
from app.routes.users import users_bp

import app.models  # noqa: F401


def create_app(config_name: str | None = None) -> Flask:
    app = Flask(__name__)

    selected_config = config_name or app.config.get("ENV", "development")
    app.config.from_object(config_by_name[selected_config])

    init_extensions(app)

    app.register_blueprint(health_bp, url_prefix="/api")
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(users_bp, url_prefix="/api/users")
    app.register_blueprint(roles_bp, url_prefix="/api/roles")
    app.register_blueprint(reports_bp, url_prefix="/api/reports")

    return app
