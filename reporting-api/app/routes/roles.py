from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from app.extensions import db
from app.models import Rol


roles_bp = Blueprint("roles", __name__)


def _serialize_role(role: Rol) -> dict:
    return {
        "id": role.id,
        "nombre": role.nombre,
        "descripcion": role.descripcion,
    }


@roles_bp.get("")
@jwt_required()
def list_roles():
    roles = Rol.query.order_by(Rol.id.asc()).all()
    return jsonify({"items": [_serialize_role(role) for role in roles]}), 200


@roles_bp.post("")
@jwt_required()
def create_role():
    payload = request.get_json(silent=True) or {}
    nombre = (payload.get("nombre") or "").strip().upper()
    descripcion = (payload.get("descripcion") or "").strip() or None

    if not nombre:
        return jsonify({"message": "Nombre es obligatorio."}), 400

    if Rol.query.filter_by(nombre=nombre).first() is not None:
        return jsonify({"message": "Ya existe un rol con ese nombre."}), 409

    role = Rol(nombre=nombre, descripcion=descripcion)
    db.session.add(role)
    db.session.commit()

    return jsonify(_serialize_role(role)), 201


@roles_bp.put("/<int:role_id>")
@jwt_required()
def update_role(role_id: int):
    role = db.session.get(Rol, role_id)
    if role is None:
        return jsonify({"message": "Rol no encontrado."}), 404

    payload = request.get_json(silent=True) or {}

    if "nombre" in payload:
        nombre = (payload.get("nombre") or "").strip().upper()
        if not nombre:
            return jsonify({"message": "Nombre inválido."}), 400

        exists = Rol.query.filter(Rol.nombre == nombre, Rol.id != role.id).first()
        if exists is not None:
            return jsonify({"message": "Ya existe un rol con ese nombre."}), 409
        role.nombre = nombre

    if "descripcion" in payload:
        descripcion = (payload.get("descripcion") or "").strip()
        role.descripcion = descripcion or None

    db.session.commit()
    return jsonify(_serialize_role(role)), 200
