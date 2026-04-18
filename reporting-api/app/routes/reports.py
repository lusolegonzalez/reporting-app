from flask import Blueprint, jsonify, request
from flask_jwt_extended import current_user, jwt_required

from app.extensions import db
from app.models import Reporte, Rol, RolReportePermiso


reports_bp = Blueprint("reports", __name__)


def _serialize_report(report: Reporte) -> dict:
    return {
        "id": report.id,
        "codigo": report.codigo,
        "nombre": report.nombre,
        "descripcion": report.descripcion,
        "activo": report.activo,
    }


@reports_bp.get("")
@jwt_required()
def list_reports():
    reports = Reporte.query.order_by(Reporte.id.asc()).all()
    return jsonify({"items": [_serialize_report(report) for report in reports]}), 200


@reports_bp.post("")
@jwt_required()
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
@jwt_required()
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
@jwt_required()
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
        role_ids.append(role_id)

        role = db.session.get(Rol, role_id)
        if role is None:
            return jsonify({"message": f"Rol {role_id} no encontrado."}), 404

        permission = RolReportePermiso.query.filter_by(rol_id=role_id, reporte_id=report.id).first()
        if permission is None:
            permission = RolReportePermiso(rol_id=role_id, reporte_id=report.id, puede_ver=can_view)
            db.session.add(permission)
        else:
            permission.puede_ver = can_view

    if role_ids:
        RolReportePermiso.query.filter(
            RolReportePermiso.reporte_id == report.id,
            ~RolReportePermiso.rol_id.in_(role_ids),
        ).delete(synchronize_session=False)

    db.session.commit()
    return jsonify({"message": "Visibilidad actualizada."}), 200


@reports_bp.get("/<int:report_id>/visibility")
@jwt_required()
def get_report_visibility(report_id: int):
    report = db.session.get(Reporte, report_id)
    if report is None:
        return jsonify({"message": "Reporte no encontrado."}), 404

    rows = (
        db.session.query(Rol.id, Rol.nombre, RolReportePermiso.puede_ver)
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
                    {"role_id": role_id, "rol": role_name, "puede_ver": bool(can_view)}
                    for role_id, role_name, can_view in rows
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
