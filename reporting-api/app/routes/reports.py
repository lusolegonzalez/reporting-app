import io
import logging

from flask import Blueprint, jsonify, request, send_file, current_app
from flask_jwt_extended import current_user, jwt_required

from app.extensions import db
from app.models import Reporte, Rol, RolReportePermiso
from app.services.audit import record_report_query
from app.services.etl.availability import (
    find_active_execution,
    find_missing_ranges,
)
from app.services.etl.runner import queue_etl_async
from app.services.reports import (
    ReportNotFoundError,
    ReportPermissionError,
    ReportValidationError,
    report_registry,
)
from app.utils.auth import admin_required


logger = logging.getLogger(__name__)

reports_bp = Blueprint("reports", __name__)


ETL_AUTO_ORIGEN_DEFAULT = "TwinsDbQuatro045"


def _serialize_report(report: Reporte) -> dict:
    return {
        "id": report.id,
        "codigo": report.codigo,
        "nombre": report.nombre,
        "descripcion": report.descripcion,
        "activo": report.activo,
    }


# ---------------------------------------------------------------------------
# Helpers de permisos
# ---------------------------------------------------------------------------


def _user_role_ids(user) -> list[int]:
    if user is None:
        return []
    return [ur.rol_id for ur in user.roles]


def _user_can_view(user, report: Reporte) -> bool:
    role_ids = _user_role_ids(user)
    if not role_ids:
        return False
    exists = (
        RolReportePermiso.query.filter(
            RolReportePermiso.reporte_id == report.id,
            RolReportePermiso.rol_id.in_(role_ids),
            RolReportePermiso.puede_ver.is_(True),
        ).first()
    )
    return exists is not None


def _user_can_export(user, report: Reporte) -> bool:
    role_ids = _user_role_ids(user)
    if not role_ids:
        return False
    exists = (
        RolReportePermiso.query.filter(
            RolReportePermiso.reporte_id == report.id,
            RolReportePermiso.rol_id.in_(role_ids),
            RolReportePermiso.puede_exportar.is_(True),
        ).first()
    )
    return exists is not None


@reports_bp.get("")
@admin_required
def list_reports():
    reports = Reporte.query.order_by(Reporte.id.asc()).all()
    return jsonify({"items": [_serialize_report(report) for report in reports]}), 200


@reports_bp.post("")
@admin_required
def create_report():
    payload = request.get_json(silent=True) or {}
    codigo = (payload.get("codigo") or "").strip().upper()
    nombre = (payload.get("nombre") or "").strip()
    descripcion = (payload.get("descripcion") or "").strip() or None
    activo = payload.get("activo", True)

    if not codigo or not nombre:
        return jsonify({"message": "Código y nombre son obligatorios."}), 400

    if Reporte.query.filter_by(codigo=codigo).first() is not None:
        return jsonify({"message": "Ya existe un reporte con ese código."}), 409

    report = Reporte(codigo=codigo, nombre=nombre, descripcion=descripcion, activo=bool(activo))
    db.session.add(report)
    db.session.commit()

    return jsonify(_serialize_report(report)), 201


@reports_bp.put("/<int:report_id>")
@admin_required
def update_report(report_id: int):
    report = db.session.get(Reporte, report_id)
    if report is None:
        return jsonify({"message": "Reporte no encontrado."}), 404

    payload = request.get_json(silent=True) or {}

    if "codigo" in payload:
        codigo = (payload.get("codigo") or "").strip().upper()
        if not codigo:
            return jsonify({"message": "Código inválido."}), 400
        exists = Reporte.query.filter(Reporte.codigo == codigo, Reporte.id != report.id).first()
        if exists is not None:
            return jsonify({"message": "Ya existe un reporte con ese código."}), 409
        report.codigo = codigo

    if "nombre" in payload:
        nombre = (payload.get("nombre") or "").strip()
        if not nombre:
            return jsonify({"message": "Nombre inválido."}), 400
        report.nombre = nombre

    if "descripcion" in payload:
        descripcion = (payload.get("descripcion") or "").strip()
        report.descripcion = descripcion or None

    if "activo" in payload:
        report.activo = bool(payload.get("activo"))

    db.session.commit()
    return jsonify(_serialize_report(report)), 200


@reports_bp.put("/<int:report_id>/visibility")
@admin_required
def update_report_visibility(report_id: int):
    report = db.session.get(Reporte, report_id)
    if report is None:
        return jsonify({"message": "Reporte no encontrado."}), 404

    payload = request.get_json(silent=True) or {}
    visibility = payload.get("visibility")

    if not isinstance(visibility, list):
        return jsonify({"message": "visibility debe ser una lista."}), 400

    role_ids = []
    for item in visibility:
        if not isinstance(item, dict):
            return jsonify({"message": "visibility contiene un valor inválido."}), 400
        try:
            role_id = int(item.get("role_id"))
        except (TypeError, ValueError):
            return jsonify({"message": "role_id inválido."}), 400
        can_view = bool(item.get("puede_ver", False))
        can_export = bool(item.get("puede_exportar", False))
        # Coherencia: no se puede exportar si no se puede ver.
        if can_export and not can_view:
            can_export = False
        role_ids.append(role_id)

        role = db.session.get(Rol, role_id)
        if role is None:
            return jsonify({"message": f"Rol {role_id} no encontrado."}), 404

        permission = RolReportePermiso.query.filter_by(rol_id=role_id, reporte_id=report.id).first()
        if permission is None:
            permission = RolReportePermiso(
                rol_id=role_id,
                reporte_id=report.id,
                puede_ver=can_view,
                puede_exportar=can_export,
            )
            db.session.add(permission)
        else:
            permission.puede_ver = can_view
            permission.puede_exportar = can_export

    if role_ids:
        RolReportePermiso.query.filter(
            RolReportePermiso.reporte_id == report.id,
            ~RolReportePermiso.rol_id.in_(role_ids),
        ).delete(synchronize_session=False)

    db.session.commit()
    return jsonify({"message": "Visibilidad actualizada."}), 200


@reports_bp.get("/<int:report_id>/visibility")
@admin_required
def get_report_visibility(report_id: int):
    report = db.session.get(Reporte, report_id)
    if report is None:
        return jsonify({"message": "Reporte no encontrado."}), 404

    rows = (
        db.session.query(Rol.id, Rol.nombre, RolReportePermiso.puede_ver, RolReportePermiso.puede_exportar)
        .join(RolReportePermiso, RolReportePermiso.rol_id == Rol.id, isouter=True)
        .filter((RolReportePermiso.reporte_id == report.id) | (RolReportePermiso.reporte_id.is_(None)))
        .order_by(Rol.id.asc())
        .all()
    )

    return (
        jsonify(
            {
                "report_id": report.id,
                "visibility": [
                    {
                        "role_id": role_id,
                        "rol": role_name,
                        "puede_ver": bool(can_view),
                        "puede_exportar": bool(can_export),
                    }
                    for role_id, role_name, can_view, can_export in rows
                ],
            }
        ),
        200,
    )


@reports_bp.get("/visible/me")
@jwt_required()
def list_visible_reports_for_me():
    if current_user is None:
        return jsonify({"message": "Usuario no encontrado."}), 404

    role_ids = [user_role.rol_id for user_role in current_user.roles]

    if not role_ids:
        return jsonify({"items": []}), 200

    reports = (
        Reporte.query.join(RolReportePermiso, RolReportePermiso.reporte_id == Reporte.id)
        .filter(
            Reporte.activo.is_(True),
            RolReportePermiso.rol_id.in_(role_ids),
            RolReportePermiso.puede_ver.is_(True),
        )
        .order_by(Reporte.id.asc())
        .distinct()
        .all()
    )

    return jsonify({"items": [_serialize_report(report) for report in reports]}), 200


# ---------------------------------------------------------------------------
# Capa de ejecucion de reportes (registry)
# ---------------------------------------------------------------------------


_FORMATOS_EXPORTACION = {"excel", "pdf"}
_FORMATOS_VALIDOS = {"json"} | _FORMATOS_EXPORTACION


def _get_report_or_404(codigo: str):
    """Busca el `Reporte` por codigo. Devuelve (response, status) si no existe."""
    report = Reporte.query.filter_by(codigo=codigo.strip().upper()).first()
    if report is None or not report.activo:
        return jsonify({"message": "Reporte no encontrado o inactivo."}), 404
    return report


@reports_bp.get("/by-codigo/<string:codigo>/metadata")
@jwt_required()
def get_report_metadata(codigo: str):
    """Devuelve la metadata del reporte: parametros y permisos del usuario actual."""
    result = _get_report_or_404(codigo)
    if isinstance(result, tuple):
        return result
    report: Reporte = result

    try:
        definition = report_registry.get(report.codigo)
    except ReportNotFoundError:
        return (
            jsonify({"message": "El reporte no tiene una definición ejecutable registrada."}),
            404,
        )

    if not _user_can_view(current_user, report):
        return jsonify({"message": "Sin permiso para visualizar este reporte."}), 403

    can_export = _user_can_export(current_user, report)

    return (
        jsonify(
            {
                "codigo": definition.codigo,
                "nombre": definition.nombre,
                "descripcion": definition.descripcion,
                "parametros": [p.to_dict() for p in definition.parametros],
                "permisos": {
                    "puede_ver": True,
                    "puede_exportar": can_export,
                },
                "formatos_disponibles": {
                    "json": True,
                    "excel": can_export,
                    "pdf": can_export,
                },
            }
        ),
        200,
    )


@reports_bp.post("/by-codigo/<string:codigo>/run")
@jwt_required()
def run_report(codigo: str):
    """Ejecuta un reporte registrado y devuelve la respuesta estandarizada."""
    result = _get_report_or_404(codigo)

    if isinstance(result, tuple):
        return result
    report: Reporte = result

    user_id = getattr(current_user, "id", None)
    raw_body = request.get_json(silent=True) or {}
    raw_params_preview = raw_body.get("parametros") or {}
    formato_preview = (raw_body.get("formato") or "json").strip().lower()
    logger.info(
        "[REPORT] run request codigo=%s formato=%s user_id=%s parametros=%s",
        report.codigo, formato_preview, user_id, raw_params_preview,
    )

    try:
        definition = report_registry.get(report.codigo)
    except ReportNotFoundError:
        logger.info("[REPORT] run codigo=%s -> 404 no executable definition", report.codigo)
        return (
            jsonify({"message": "El reporte no tiene una definición ejecutable registrada."}),
            404,
        )

    if not _user_can_view(current_user, report):
        return jsonify({"message": "Sin permiso para visualizar este reporte."}), 403

    payload = request.get_json(silent=True) or {}
    raw_parametros = payload.get("parametros") or {}
    if not isinstance(raw_parametros, dict):
        return jsonify({"message": "'parametros' debe ser un objeto."}), 400

    formato = (payload.get("formato") or "json").strip().lower()
    if formato not in _FORMATOS_VALIDOS:
        return jsonify({"message": f"Formato inválido: {formato!r}."}), 400

    can_export = _user_can_export(current_user, report)
    if formato in _FORMATOS_EXPORTACION and not can_export:
        return (
            jsonify({"message": f"Sin permiso para exportar este reporte en formato {formato}."}),
            403,
        )

    try:
        report_request = definition.parse_and_validate(raw_parametros)
    except ReportValidationError as exc:
        logger.info(
            "[REPORT] run codigo=%s -> 400 validation field=%s msg=%s",
            report.codigo, exc.field, exc.message,
        )
        return jsonify({"message": exc.message, "field": exc.field}), 400

    # ── ETL bajo demanda ───────────────────────────────────────────────
    # Si el reporte declara un rango requerido en la base intermedia, validamos
    # cobertura. Si falta data, disparamos ETL asincronico y respondemos 202.
    etl_status = _ensure_etl_coverage(definition, report_request)
    if etl_status is not None:
        logger.info(
            "[REPORT] codigo=%s -> 202 %s ejecucion_id=%s reusada=%s rango_faltante=%s",
            report.codigo,
            etl_status.get("status"),
            etl_status.get("ejecucion_id"),
            etl_status.get("reusada"),
            etl_status.get("rango_faltante"),
        )
        return jsonify(etl_status), 202

    try:
        with record_report_query(
            usuario_id=current_user.id,
            reporte_id=report.id,
            parametros=report_request.parametros,
        ):
            response = definition.execute(report_request)
    except ReportValidationError as exc:
        logger.info(
            "[REPORT] execute codigo=%s -> 400 validation field=%s msg=%s",
            report.codigo, exc.field, exc.message,
        )
        return jsonify({"message": exc.message, "field": exc.field}), 400
    except ReportPermissionError as exc:
        logger.info("[REPORT] execute codigo=%s -> 403 %s", report.codigo, exc)
        return jsonify({"message": str(exc)}), 403
    except Exception:  # noqa: BLE001
        logger.exception("[REPORT] execute codigo=%s -> 500 unhandled", report.codigo)
        return jsonify({"message": "Error ejecutando el reporte."}), 500

    response.export_permitido = {"excel": can_export, "pdf": can_export}

    if formato == "json":
        logger.info(
            "[REPORT] codigo=%s -> 200 report_ready secciones=%d alertas=%d",
            report.codigo, len(response.secciones), len(response.alertas),
        )
        return jsonify(response.to_dict()), 200

    # ── Exportación real ────────────────────────────────────────────────────
    from app.services.reports.exporters import export_to_excel, export_to_pdf, _make_filename

    try:
        if formato == "excel":
            file_bytes = export_to_excel(response)
            filename = _make_filename(response, "xlsx")
            mimetype = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        else:  # pdf
            file_bytes = export_to_pdf(response)
            filename = _make_filename(response, "pdf")
            mimetype = "application/pdf"
    except Exception:  # noqa: BLE001
        return jsonify({"message": f"Error generando exportación {formato}."}), 500

    buf = io.BytesIO(file_bytes)
    buf.seek(0)
    return send_file(
        buf,
        mimetype=mimetype,
        as_attachment=True,
        download_name=filename,
    )


def _ensure_etl_coverage(definition, report_request):
    """Devuelve None si la base intermedia ya tiene el rango requerido.

    Si el reporte declara `loaded_range_requerido` y hay huecos, dispara ETL
    asincronico (o reutiliza uno encolado/en curso) y devuelve un payload
    estructurado describiendo el estado, para que el endpoint responda 202.
    """
    fn = getattr(definition, "loaded_range_requerido", None)
    if not callable(fn):
        logger.debug(
            "[REPORT] coverage check skipped codigo=%s (reporte no declara rango)",
            getattr(definition, "codigo", "?"),
        )
        return None

    rango = fn(report_request)
    if rango is None:
        logger.debug(
            "[REPORT] coverage check skipped codigo=%s (loaded_range_requerido devolvio None)",
            getattr(definition, "codigo", "?"),
        )
        return None
    desde, hasta = rango
    origen = current_app.config.get("ETL_AUTO_ORIGEN") or ETL_AUTO_ORIGEN_DEFAULT

    logger.info(
        "[REPORT] coverage check codigo=%s origen=%s desde=%s hasta=%s",
        getattr(definition, "codigo", "?"), origen, desde, hasta,
    )

    gaps = find_missing_ranges(desde, hasta, origen)
    if not gaps:
        logger.info(
            "[REPORT] coverage available=true origen=%s desde=%s hasta=%s "
            "(rango cubierto por ejecuciones ok/partial existentes)",
            origen, desde, hasta,
        )
        return None  # todo el rango ya esta cargado

    gaps_str = ",".join(f"{g.desde}..{g.hasta}" for g in gaps)
    logger.info(
        "[REPORT] coverage available=false origen=%s desde=%s hasta=%s huecos=[%s]",
        origen, desde, hasta, gaps_str,
    )

    # Rango faltante a cargar: tomamos el envoltorio [min_desde, max_hasta]
    # para hacer una unica corrida (mas simple y consistente con el lock).
    g_desde = min(g.desde for g in gaps)
    g_hasta = max(g.hasta for g in gaps)

    # Anti-duplicacion: reusar ejecucion activa que ya cubra el faltante
    activa = find_active_execution(g_desde, g_hasta, origen)
    if activa is not None:
        logger.info(
            "[REPORT] ETL already running execution_id=%s estado=%s origen=%s "
            "rango_activo=%s..%s (reusando, no se dispara nueva corrida)",
            activa.id, activa.estado, origen,
            activa.fecha_desde, activa.fecha_hasta,
        )
        return {
            "status": "preparing_data",
            "ejecucion_id": activa.id,
            "estado": activa.estado,
            "origen": origen,
            "rango_faltante": {"desde": g_desde.isoformat(), "hasta": g_hasta.isoformat()},
            "huecos": [g.to_dict() for g in gaps],
            "reusada": True,
            "message": "Se esta cargando el rango solicitado, reintente en unos instantes.",
        }

    from app.routes.etl import build_source_for_kind, default_source_kind

    source_kind = default_source_kind()
    logger.info(
        "[REPORT] triggering ETL for missing range origen=%s source_kind=%s desde=%s hasta=%s",
        origen, source_kind, g_desde, g_hasta,
    )

    def _factory():
        return build_source_for_kind(source_kind)

    try:
        ejecucion_id = queue_etl_async(
            desde=g_desde,
            hasta=g_hasta,
            origen=origen,
            created_by_user_id=getattr(current_user, "id", None),
            source_factory=_factory,
        )
    except Exception:  # noqa: BLE001
        current_app.logger.exception(
            "[REPORT] no se pudo encolar ETL on-demand origen=%s desde=%s hasta=%s",
            origen, g_desde, g_hasta,
        )
        return {
            "status": "etl_dispatch_error",
            "origen": origen,
            "rango_faltante": {"desde": g_desde.isoformat(), "hasta": g_hasta.isoformat()},
            "message": "Falta cargar datos del rango pedido y no se pudo iniciar el ETL.",
        }

    logger.info(
        "[REPORT] ETL queued execution_id=%s estado=queued origen=%s desde=%s hasta=%s",
        ejecucion_id, origen, g_desde, g_hasta,
    )
    return {
        "status": "preparing_data",
        "ejecucion_id": ejecucion_id,
        "estado": "queued",
        "origen": origen,
        "rango_faltante": {"desde": g_desde.isoformat(), "hasta": g_hasta.isoformat()},
        "huecos": [g.to_dict() for g in gaps],
        "reusada": False,
        "message": "Faltan datos del rango. Se inicio la carga ETL en segundo plano.",
    }


def _safe_json_dumps(value: dict) -> str:
    import json
    from datetime import date, datetime

    def _default(v):
        if isinstance(v, (date, datetime)):
            return v.isoformat()
        return str(v)

    try:
        return json.dumps(value, default=_default, ensure_ascii=False)
    except Exception:  # noqa: BLE001
        return "{}"
