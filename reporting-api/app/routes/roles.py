from flask import Blueprint, jsonify


roles_bp = Blueprint("roles", __name__)


@roles_bp.get("")
def list_roles_placeholder():
    return jsonify({"items": [], "message": "Listado placeholder de roles"}), 200
