from flask import Blueprint, jsonify


users_bp = Blueprint("users", __name__)


@users_bp.get("")
def list_users_placeholder():
    return jsonify({"items": [], "message": "Listado placeholder de usuarios"}), 200


@users_bp.post("")
def create_user_placeholder():
    return jsonify({"message": "Alta de usuario placeholder"}), 501
