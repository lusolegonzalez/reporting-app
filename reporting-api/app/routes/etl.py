"""Endpoints administrativos del proceso ETL."""
from __future__ import annotations

from datetime import date, datetime

from flask import Blueprint, jsonify, request
from flask_jwt_extended import current_user, jwt_required

from app.extensions import db
from app.models import EjecucionError, EjecucionImportacion, EjecucionTabla
from app.services.etl.runner import EtlAlreadyRunning, run_etl
from app.services.etl.sources import InMemoryTwinsSource

etl_bp = Blueprint("etl", __name__)


def _parse_date(raw: str | None) -> date | None:
    if not raw:
        return None
    try:
        return datetime.strptime(raw.strip(), "%Y-%m-%d").date()
    except ValueError:
        return None


@etl_bp.post("/run")
@jwt_required()
def run():
    payload = request.get_json(silent=True) or {}
    desde = _parse_date(payload.get("desde"))
    hasta = _parse_date(payload.get("hasta"))
    origen = (payload.get("origen") or "TwinsDbQuatro045").strip()

    if desde is None or hasta is None:
        return jsonify({"message": "desde/hasta requeridos (YYYY-MM-DD)."}), 400

    # Por ahora la fuente real (pyodbc) no esta cableada; usamos un origen
    # vacio para validar la maquinaria del runner sin dependencias externas.
    source = InMemoryTwinsSource()

    try:
        resumen = run_etl(
            source=source,
            desde=desde,
            hasta=hasta,
            origen=origen,
            created_by_user_id=getattr(current_user, "id", None),
        )
    except EtlAlreadyRunning as exc:
        return jsonify({"message": str(exc)}), 409
    except ValueError as exc:
        return jsonify({"message": str(exc)}), 400

    return (
        jsonify(
            {
                "ejecucion_id": resumen.ejecucion_id,
                "estado": resumen.estado,
                "pasos": [
                    {
                        "tabla_destino": p.tabla_destino,
                        "filas_leidas": p.filas_leidas,
                        "filas_insertadas": p.filas_insertadas,
                        "filas_actualizadas": p.filas_actualizadas,
                        "filas_descartadas": p.filas_descartadas,
                        "duracion_ms": p.duracion_ms,
                        "errores": [{"source_pk": s, "mensaje": m} for s, m in p.errores],
                    }
                    for p in resumen.pasos
                ],
            }
        ),
        202,
    )


@etl_bp.get("/ejecuciones/<int:ejecucion_id>")
@jwt_required()
def get_ejecucion(ejecucion_id: int):
    ejecucion = db.session.get(EjecucionImportacion, ejecucion_id)
    if ejecucion is None:
        return jsonify({"message": "Ejecucion no encontrada."}), 404

    tablas = (
        db.session.query(EjecucionTabla)
        .filter(EjecucionTabla.ejecucion_id == ejecucion_id)
        .order_by(EjecucionTabla.id.asc())
        .all()
    )
    errores = (
        db.session.query(EjecucionError)
        .filter(EjecucionError.ejecucion_id == ejecucion_id)
        .order_by(EjecucionError.id.asc())
        .all()
    )

    return (
        jsonify(
            {
                "id": ejecucion.id,
                "origen": ejecucion.origen,
                "fecha_desde": ejecucion.fecha_desde.isoformat(),
                "fecha_hasta": ejecucion.fecha_hasta.isoformat(),
                "estado": ejecucion.estado,
                "observaciones": ejecucion.observaciones,
                "tablas": [
                    {
                        "tabla_destino": t.tabla_destino,
                        "filas_leidas": t.filas_leidas,
                        "filas_insertadas": t.filas_insertadas,
                        "filas_actualizadas": t.filas_actualizadas,
                        "filas_descartadas": t.filas_descartadas,
                        "duracion_ms": t.duracion_ms,
                    }
                    for t in tablas
                ],
                "errores": [
                    {
                        "tabla_destino": e.tabla_destino,
                        "source_pk": e.source_pk,
                        "mensaje": e.mensaje,
                    }
                    for e in errores
                ],
            }
        ),
        200,
    )
