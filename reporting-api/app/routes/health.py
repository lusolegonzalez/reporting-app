"""Endpoint de salud minimo del servicio."""
from __future__ import annotations

import logging

from flask import Blueprint, jsonify
from sqlalchemy import text

from app.extensions import db

logger = logging.getLogger(__name__)

health_bp = Blueprint("health", __name__)


@health_bp.get("/health")
def health_check():
    return jsonify({"status": "ok", "service": "reporting-api"}), 200


@health_bp.get("/health/ready")
def health_ready():
    """Readiness: el servicio + base intermedia responden.

    Hace un `SELECT 1` con timeout corto. Si la DB no responde, devuelve 503
    con detalle para el orquestador (k8s/systemd/loadbalancer).
    """
    try:
        db.session.execute(text("SELECT 1"))
        return jsonify({"status": "ready", "service": "reporting-api", "db": "ok"}), 200
    except Exception as exc:  # noqa: BLE001
        logger.warning("Health readiness fail: %s", exc)
        return (
            jsonify(
                {
                    "status": "not_ready",
                    "service": "reporting-api",
                    "db": "error",
                    "detail": str(exc)[:200],
                }
            ),
            503,
        )
