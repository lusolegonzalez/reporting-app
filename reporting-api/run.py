from flask.cli import with_appcontext

from app import create_app
from app.extensions import db
from app.models import Reporte, Rol, RolReportePermiso, Usuario, UsuarioRol

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

    base_reports = [
        {
            "codigo": "REP_RESUMEN",
            "nombre": "Resumen General",
            "descripcion": "Reporte base de ejemplo para dashboard inicial.",
        },
        {
            "codigo": "REP_DETALLE",
            "nombre": "Detalle Operativo",
            "descripcion": "Reporte base de ejemplo con mayor detalle.",
        },
    ]

    for base_report in base_reports:
        report = Reporte.query.filter_by(codigo=base_report["codigo"]).first()
        if report is None:
            report = Reporte(
                codigo=base_report["codigo"],
                nombre=base_report["nombre"],
                descripcion=base_report["descripcion"],
                activo=True,
            )
            db.session.add(report)
            db.session.flush()
        else:
            report.nombre = base_report["nombre"]
            report.descripcion = base_report["descripcion"]
            report.activo = True

        permission = RolReportePermiso.query.filter_by(rol_id=admin_role.id, reporte_id=report.id).first()
        if permission is None:
            db.session.add(RolReportePermiso(rol_id=admin_role.id, reporte_id=report.id, puede_ver=True))
        else:
            permission.puede_ver = True

    db.session.commit()
    print("Seed inicial aplicado: ADMIN + admin@reporting.local + reportes base")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
