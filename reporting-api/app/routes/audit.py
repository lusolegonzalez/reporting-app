"""Endpoints de consulta de auditoria.

Lectura de:
- Auditoria funcional: `auditorias_consultas_reportes` (consultas a reportes).
- Auditoria tecnica:   `ejecuciones_importacion` + `etl.ejecucion_*` (ETL).

El detalle por id de una ejecucion ETL ya vive en /api/etl/ejecuciones/<id>;
aqui agregamos el LISTADO + el listado de auditorias funcionales.
"""
from __future__ import annotations

from datetime import date, datetime

from flask import Blueprint, jsonify, request
from sqlalchemy import desc

from app.extensions import db
from app.models import (
    AuditoriaConsultaReporte,
    EjecucionImportacion,
    Reporte,
    Usuario,
)
from app.utils.auth import admin_required

audit_bp = Blueprint("audit", __name__)


_DEFAULT_LIMIT = 50
_MAX_LIMIT = 200


def _parse_int(raw, default: int, *, lo: int, hi: int) -> int:
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return default
    return max(lo, min(hi, value))


def _parse_date(raw: str | None) -> date | None:
    if not raw:
        return None
    try:
        return datetime.strptime(raw.strip(), "%Y-%m-%d").date()
    except ValueError:
        return None


def _parse_bool(raw: str | None) -> bool | None:
    if raw is None:
        return None
    v = raw.strip().lower()
    if v in ("true", "1"):
        return True
    if v in ("false", "0"):
        return False
    return None


# ---------------------------------------------------------------------------
# Auditoria funcional: consultas a reportes
# ---------------------------------------------------------------------------


@audit_bp.get("/reportes")
@admin_required
def list_report_audits():
    """Lista las consultas funcionales realizadas a reportes.

    Filtros (query string, todos opcionales):
        - usuario_id, reporte_id, reporte_codigo
        - desde, hasta (YYYY-MM-DD; aplican a fecha_consulta)
        - resultado_ok (true|false)
        - limit (default 50, max 200), offset
    """
    q = (
        db.session.query(AuditoriaConsultaReporte, Usuario, Reporte)
        .join(Usuario, Usuario.id == AuditoriaConsultaReporte.usuario_id)
        .join(Reporte, Reporte.id == AuditoriaConsultaReporte.reporte_id)
    )

    usuario_id = request.args.get("usuario_id", type=int)
    if usuario_id is not None:
        q = q.filter(AuditoriaConsultaReporte.usuario_id == usuario_id)

    reporte_id = request.args.get("reporte_id", type=int)
    if reporte_id is not None:
        q = q.filter(AuditoriaConsultaReporte.reporte_id == reporte_id)

    reporte_codigo = (request.args.get("reporte_codigo") or "").strip().upper()
    if reporte_codigo:
        q = q.filter(Reporte.codigo == reporte_codigo)

    desde = _parse_date(request.args.get("desde"))
    if desde is not None:
        q = q.filter(AuditoriaConsultaReporte.fecha_consulta >= desde)

    hasta = _parse_date(request.args.get("hasta"))
    if hasta is not None:
        q = q.filter(
            AuditoriaConsultaReporte.fecha_consulta
            <= datetime.combine(hasta, datetime.max.time())
        )

    resultado_ok = _parse_bool(request.args.get("resultado_ok"))
    if resultado_ok is not None:
        q = q.filter(AuditoriaConsultaReporte.resultado_ok.is_(resultado_ok))

    limit = _parse_int(request.args.get("limit"), _DEFAULT_LIMIT, lo=1, hi=_MAX_LIMIT)
    offset = _parse_int(request.args.get("offset"), 0, lo=0, hi=10_000_000)

    total = q.with_entities(db.func.count(AuditoriaConsultaReporte.id)).scalar() or 0
    rows = (
        q.order_by(desc(AuditoriaConsultaReporte.fecha_consulta))
        .offset(offset)
        .limit(limit)
        .all()
    )

    items = [
        {
            "id": audit.id,
            "fecha_consulta": audit.fecha_consulta.isoformat(),
            "usuario": {"id": user.id, "email": user.email, "nombre": user.nombre},
            "reporte": {"id": rep.id, "codigo": rep.codigo, "nombre": rep.nombre},
            "filtros_json": audit.filtros_json,
            "resultado_ok": bool(audit.resultado_ok),
            "duracion_ms": audit.duracion_ms,
            "observaciones": audit.observaciones,
        }
        for audit, user, rep in rows
    ]

    return jsonify({"items": items, "total": int(total), "limit": limit, "offset": offset}), 200


# ---------------------------------------------------------------------------
# Auditoria tecnica: ejecuciones ETL
# ---------------------------------------------------------------------------


@audit_bp.get("/etl-ejecuciones")
@admin_required
def list_etl_executions():
    """Lista las ejecuciones tecnicas de importacion (ETL).

    Filtros (query string, todos opcionales):
        - origen, estado
        - desde, hasta (filtran por created_at)
        - limit, offset
    """
    q = db.session.query(EjecucionImportacion)

    origen = (request.args.get("origen") or "").strip()
    if origen:
        q = q.filter(EjecucionImportacion.origen == origen)

    estado = (request.args.get("estado") or "").strip().lower()
    if estado:
        q = q.filter(EjecucionImportacion.estado == estado)

    desde = _parse_date(request.args.get("desde"))
    if desde is not None:
        q = q.filter(EjecucionImportacion.created_at >= datetime.combine(desde, datetime.min.time()))

    hasta = _parse_date(request.args.get("hasta"))
    if hasta is not None:
        q = q.filter(EjecucionImportacion.created_at <= datetime.combine(hasta, datetime.max.time()))

    limit = _parse_int(request.args.get("limit"), _DEFAULT_LIMIT, lo=1, hi=_MAX_LIMIT)
    offset = _parse_int(request.args.get("offset"), 0, lo=0, hi=10_000_000)

    total = q.with_entities(db.func.count(EjecucionImportacion.id)).scalar() or 0
    rows = q.order_by(desc(EjecucionImportacion.id)).offset(offset).limit(limit).all()

    items = [
        {
            "id": e.id,
            "origen": e.origen,
            "fecha_desde": e.fecha_desde.isoformat(),
            "fecha_hasta": e.fecha_hasta.isoformat(),
            "estado": e.estado,
            "created_at": e.created_at.isoformat(),
            "created_by_user_id": e.created_by_user_id,
            "observaciones": e.observaciones,
        }
        for e in rows
    ]

    return jsonify({"items": items, "total": int(total), "limit": limit, "offset": offset}), 200
