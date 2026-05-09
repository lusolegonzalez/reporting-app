"""Helpers de autorizacion para rutas Flask.

`admin_required` reutiliza el JWT emitido por `/auth/login`, que ya viaja con
los nombres de rol del usuario (`additional_claims={"roles": ...}`). Esto evita
hacer un round-trip extra a la base solo para validar permisos administrativos.

Diseno:
- Asume que toda ruta admin esta detras de `@jwt_required()` (lo seguimos
  declarando explicitamente para que el lector no tenga que adivinar).
- Si el JWT no incluye el claim `roles` (token viejo), cae al usuario actual.
- El nombre del rol admin es configurable via `ADMIN_ROLE_NAME` del config,
  con default "ADMIN".
"""
from __future__ import annotations

from functools import wraps

from flask import current_app, jsonify
from flask_jwt_extended import current_user, get_jwt, verify_jwt_in_request


def _resolve_role_names() -> list[str]:
    try:
        claims = get_jwt() or {}
    except Exception:  # noqa: BLE001
        claims = {}

    roles = claims.get("roles")
    if isinstance(roles, list) and roles:
        return [str(r) for r in roles]

    if current_user is not None:
        try:
            return list(current_user.role_names)
        except Exception:  # noqa: BLE001
            return []

    return []


def admin_required(view):
    """Decora una vista exigiendo que el usuario tenga el rol admin."""

    @wraps(view)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        admin_role = current_app.config.get("ADMIN_ROLE_NAME", "ADMIN")
        role_names = _resolve_role_names()
        if admin_role not in role_names:
            return (
                jsonify({"message": "Se requieren permisos de administrador."}),
                403,
            )
        return view(*args, **kwargs)

    return wrapper
