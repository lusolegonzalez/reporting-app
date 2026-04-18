from flask.cli import with_appcontext

from app import create_app
from app.extensions import db
from app.models import Rol, Usuario, UsuarioRol

app = create_app()


@app.cli.command("seed-initial-auth")
@with_appcontext
def seed_initial_auth() -> None:
    admin_role = Rol.query.filter_by(nombre="ADMIN").first()
    if admin_role is None:
        admin_role = Rol(nombre="ADMIN", descripcion="Rol administrador inicial")
        db.session.add(admin_role)
        db.session.flush()

    admin_user = Usuario.query.filter_by(email="admin@reporting.local").first()
    if admin_user is None:
        admin_user = Usuario(nombre="Admin", email="admin@reporting.local", activo=True, password_hash="")
        admin_user.set_password("Admin123*")
        db.session.add(admin_user)
        db.session.flush()
    else:
        admin_user.nombre = "Admin"
        admin_user.activo = True
        admin_user.set_password("Admin123*")

    relation_exists = UsuarioRol.query.filter_by(usuario_id=admin_user.id, rol_id=admin_role.id).first()
    if relation_exists is None:
        db.session.add(UsuarioRol(usuario_id=admin_user.id, rol_id=admin_role.id))

    db.session.commit()
    print("Seed de autenticación inicial aplicado: ADMIN + admin@reporting.local")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
