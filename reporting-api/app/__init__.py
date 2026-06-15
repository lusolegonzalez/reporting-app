from flask import Flask

from app.config import config_by_name
from app.extensions import init_extensions
from app.routes.audit import audit_bp
from app.routes.auth import auth_bp
from app.routes.etl import etl_bp
from app.routes.health import health_bp
from app.routes.reports import reports_bp
from app.routes.roles import roles_bp
from app.routes.users import users_bp

import app.models  # noqa: F401


def _configure_logging(app: Flask) -> None:
    import logging
    import os

    level_name = os.environ.get("LOG_LEVEL") or app.config.get("LOG_LEVEL") or "INFO"
    level = getattr(logging, str(level_name).upper(), logging.INFO)

    root = logging.getLogger()
    if not root.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s %(levelname)s [%(name)s] %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        root.addHandler(handler)
    root.setLevel(level)
    logging.getLogger("app").setLevel(level)


def _cleanup_stale_etl_executions(app: Flask) -> None:
    """Mark executions left in queued/running state as error on process start.

    These are left behind when the server is restarted while an ETL thread
    was active. Without cleanup, find_active_execution() keeps returning them
    and the frontend polls forever.
    """
    from app.extensions import db
    from app.models import EjecucionImportacion

    with app.app_context():
        try:
            stale = (
                db.session.query(EjecucionImportacion)
                .filter(EjecucionImportacion.estado.in_(("queued", "running")))
                .all()
            )
            if stale:
                for ej in stale:
                    ej.estado = "error"
                    ej.observaciones = "proceso_interrumpido: el servidor se reinicio durante la ejecucion."
                db.session.commit()
                app.logger.warning(
                    "[ETL-startup] %d ejecucion(es) interrumpidas marcadas como error.",
                    len(stale),
                )
        except Exception:
            app.logger.exception("[ETL-startup] no se pudo limpiar ejecuciones interrumpidas.")


def create_app(config_name: str | None = None) -> Flask:
    app = Flask(__name__)

    selected_config = config_name or app.config.get("ENV", "development")
    app.config.from_object(config_by_name[selected_config])

    _configure_logging(app)
    init_extensions(app)

    app.register_blueprint(health_bp, url_prefix="/api")
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(users_bp, url_prefix="/api/users")
    app.register_blueprint(roles_bp, url_prefix="/api/roles")
    app.register_blueprint(reports_bp, url_prefix="/api/reports")
    app.register_blueprint(etl_bp, url_prefix="/api/etl")
    app.register_blueprint(audit_bp, url_prefix="/api/audit")

    _cleanup_stale_etl_executions(app)

    return app
