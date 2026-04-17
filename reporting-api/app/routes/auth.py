from flask import Blueprint, jsonify


auth_bp = Blueprint("auth", __name__)


@auth_bp.post("/login")
def login_placeholder():
    return (
        jsonify(
            {
                "message": "Login placeholder listo. Falta implementar validación real y emisión de JWT.",
            }
        ),
        501,
    )
