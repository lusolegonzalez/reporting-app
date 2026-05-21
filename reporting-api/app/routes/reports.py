import io

from flask import Blueprint, jsonify, request, send_file
from flask_jwt_extended import current_user, jwt_required

from app.extensions import db
from app.models import Reporte, Rol, RolReportePermiso
from app.services.audit import record_report_query
from app.services.reports import (
    ReportNotFoundError,
    ReportPermissionError,
    ReportValidationError,
    report_registry,
)
from app.utils.auth import admin_required


reports_bp = Blueprint("reports", __name__)


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

    print(request.get_json())

    try:
        definition = report_registry.get(report.codigo)
    except ReportNotFoundError:
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
        return jsonify({"message": exc.message, "field": exc.field}), 400

    try:
        with record_report_query(
            usuario_id=current_user.id,
            reporte_id=report.id,
            parametros=report_request.parametros,
        ):
            response = definition.execute(report_request)
    except ReportValidationError as exc:
        return jsonify({"message": exc.message, "field": exc.field}), 400
    except ReportPermissionError as exc:
        return jsonify({"message": str(exc)}), 403
    except Exception:  # noqa: BLE001
        return jsonify({"message": "Error ejecutando el reporte."}), 500

    response.export_permitido = {"excel": can_export, "pdf": can_export}

    if formato == "json":
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
