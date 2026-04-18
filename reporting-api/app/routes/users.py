from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from sqlalchemy import func

from app.extensions import db
from app.models import Rol, Usuario, UsuarioRol


users_bp = Blueprint("users", __name__)


def _serialize_user(user: Usuario) -> dict:
    return {
        "id": user.id,
        "nombre": user.nombre,
        "email": user.email,
        "activo": user.activo,
        "roles": user.role_names,
    }


@users_bp.get("")
@jwt_required()
def list_users():
    users = Usuario.query.order_by(Usuario.id.asc()).all()
    return jsonify({"items": [_serialize_user(user) for user in users]}), 200


@users_bp.post("")
@jwt_required()
def create_user():
    payload = request.get_json(silent=True) or {}

    nombre = (payload.get("nombre") or "").strip()
    email = (payload.get("email") or "").strip().lower()
    password = payload.get("password") or ""
    activo = payload.get("activo", True)

    if not nombre or not email or not password:
        return jsonify({"message": "Nombre, email y password son obligatorios."}), 400

    if Usuario.query.filter(func.lower(Usuario.email) == email).first() is not None:
        return jsonify({"message": "Ya existe un usuario con ese email."}), 409

    user = Usuario(nombre=nombre, email=email, activo=bool(activo), password_hash="")
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    return jsonify(_serialize_user(user)), 201


@users_bp.put("/<int:user_id>")
@jwt_required()
def update_user(user_id: int):
    user = db.session.get(Usuario, user_id)
    if user is None:
        return jsonify({"message": "Usuario no encontrado."}), 404

    payload = request.get_json(silent=True) or {}

    if "nombre" in payload:
        nombre = (payload.get("nombre") or "").strip()
        if not nombre:
            return jsonify({"message": "Nombre inválido."}), 400
        user.nombre = nombre

    if "email" in payload:
        email = (payload.get("email") or "").strip().lower()
        if not email:
            return jsonify({"message": "Email inválido."}), 400

        exists = Usuario.query.filter(func.lower(Usuario.email) == email, Usuario.id != user.id).first()
        if exists is not None:
            return jsonify({"message": "Ya existe un usuario con ese email."}), 409
        user.email = email

    if "password" in payload and payload.get("password"):
        user.set_password(payload.get("password"))

    if "activo" in payload:
        user.activo = bool(payload.get("activo"))

    db.session.commit()
    return jsonify(_serialize_user(user)), 200


@users_bp.put("/<int:user_id>/roles")
@jwt_required()
def assign_user_roles(user_id: int):
    user = db.session.get(Usuario, user_id)
    if user is None:
        return jsonify({"message": "Usuario no encontrado."}), 404

    payload = request.get_json(silent=True) or {}
    role_ids = payload.get("role_ids")

    if not isinstance(role_ids, list):
        return jsonify({"message": "role_ids debe ser una lista de IDs."}), 400

    unique_ids = []
    for role_id in role_ids:
        try:
            role_id_int = int(role_id)
        except (TypeError, ValueError):
            return jsonify({"message": "role_ids contiene un valor inválido."}), 400
        if role_id_int not in unique_ids:
            unique_ids.append(role_id_int)

    roles = Rol.query.filter(Rol.id.in_(unique_ids)).all() if unique_ids else []
    if len(roles) != len(unique_ids):
        return jsonify({"message": "Uno o más roles no existen."}), 404

    UsuarioRol.query.filter_by(usuario_id=user.id).delete()
    for role in roles:
        db.session.add(UsuarioRol(usuario_id=user.id, rol_id=role.id))

    db.session.commit()
    db.session.refresh(user)

    return jsonify(_serialize_user(user)), 200


@users_bp.get("/<int:user_id>/roles")
@jwt_required()
def get_user_roles(user_id: int):
    user = db.session.get(Usuario, user_id)
    if user is None:
        return jsonify({"message": "Usuario no encontrado."}), 404

    return (
        jsonify(
            {
                "user_id": user.id,
                "roles": [{"id": user_rol.rol.id, "nombre": user_rol.rol.nombre} for user_rol in user.roles if user_rol.rol],
            }
        ),
        200,
    )
