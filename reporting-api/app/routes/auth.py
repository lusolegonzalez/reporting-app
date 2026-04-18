from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token, current_user, get_jwt, jwt_required
from sqlalchemy import func

from app.extensions import db, jwt
from app.models.user import Usuario


auth_bp = Blueprint("auth", __name__)


@jwt.user_lookup_loader
def load_user_from_jwt(_jwt_header, jwt_data):
    identity = jwt_data.get("sub")
    if identity is None:
        return None

    try:
        return db.session.get(Usuario, int(identity))
    except (TypeError, ValueError):
        return None


@auth_bp.post("/login")
def login():
    payload = request.get_json(silent=True) or {}
    email = (payload.get("email") or "").strip().lower()
    password = payload.get("password") or ""

    if not email or not password:
        return jsonify({"message": "Email y password son obligatorios."}), 400

    user = Usuario.query.filter(func.lower(Usuario.email) == email).first()

    if user is None or not user.activo or not user.check_password(password):
        return jsonify({"message": "Credenciales inválidas."}), 401

    token = create_access_token(identity=str(user.id), additional_claims={"roles": user.role_names})

    return (
        jsonify(
            {
                "access_token": token,
                "user": user.to_auth_dict(),
            }
        ),
        200,
    )


@auth_bp.get("/me")
@jwt_required()
def me():
    if current_user is None:
        return jsonify({"message": "Usuario no encontrado."}), 404

    user_payload = current_user.to_auth_dict()
    user_payload["roles"] = get_jwt().get("roles", user_payload["roles"])

    return jsonify(user_payload), 200
