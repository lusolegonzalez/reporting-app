import os

from flask.cli import with_appcontext
from sqlalchemy import text

from app import create_app
from app.extensions import db
from app.models import Reporte, Rol, RolReportePermiso, Usuario, UsuarioRol
from app.services.reports import report_registry

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
        {
            "codigo": "DDJJ_MENUDENCIAS",
            "nombre": "Declaración Jurada Menudencias",
            "descripcion": "Reporte de producción en carácter de declaración jurada (SENASA).",
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
            db.session.add(
                RolReportePermiso(
                    rol_id=admin_role.id,
                    reporte_id=report.id,
                    puede_ver=True,
                    puede_exportar=True,
                )
            )
        else:
            permission.puede_ver = True
            permission.puede_exportar = True

    db.session.commit()
    print("Seed inicial aplicado: ADMIN + admin@reporting.local + reportes base")


@app.cli.command("smoke-check")
@with_appcontext
def smoke_check() -> None:
    """Smoke check: valida que el sistema este minimamente sano.

    Chequea: conectividad a DB, existencia del rol ADMIN, usuario admin
    activo, reportes seed registrados en el registry y consistencia basica
    de permisos. Sale con codigo 0 si todo OK; imprime resumen.
    """
    import sys

    failures: list[str] = []
    ok: list[str] = []

    # 1) DB ping
    try:
        db.session.execute(text("SELECT 1"))
        ok.append("DB intermedia responde (SELECT 1)")
    except Exception as exc:  # noqa: BLE001
        failures.append(f"DB no responde: {exc}")

    # 2) Rol ADMIN
    admin_role = Rol.query.filter_by(nombre=app.config.get("ADMIN_ROLE_NAME", "ADMIN")).first()
    if admin_role is None:
        failures.append("No existe el rol ADMIN. Correr 'flask seed-initial-auth'.")
    else:
        ok.append(f"Rol admin OK (id={admin_role.id})")

    # 3) Usuario admin activo
    admin_user = Usuario.query.filter_by(email="admin@reporting.local").first()
    if admin_user is None or not admin_user.activo:
        failures.append("No hay un usuario admin activo (admin@reporting.local).")
    else:
        ok.append(f"Usuario admin activo (id={admin_user.id})")

    # 4) Reportes seed presentes en DB
    for codigo in ("REP_RESUMEN", "REP_DETALLE", "DDJJ_MENUDENCIAS"):
        rep = Reporte.query.filter_by(codigo=codigo).first()
        if rep is None:
            failures.append(f"Falta el reporte seed {codigo}.")
        else:
            ok.append(f"Reporte {codigo} en DB")

    # 5) Reportes ejecutables registrados
    registered = {d.codigo for d in report_registry.all()}
    if "DDJJ_MENUDENCIAS" not in registered:
        failures.append("DDJJ_MENUDENCIAS no esta registrado en report_registry.")
    else:
        ok.append("DDJJ_MENUDENCIAS registrado en registry")

    # 6) Permiso de admin sobre DDJJ_MENUDENCIAS
    if admin_role is not None:
        ddjj = Reporte.query.filter_by(codigo="DDJJ_MENUDENCIAS").first()
        if ddjj is not None:
            perm = RolReportePermiso.query.filter_by(rol_id=admin_role.id, reporte_id=ddjj.id).first()
            if perm is None or not perm.puede_ver:
                failures.append("Admin no tiene puede_ver sobre DDJJ_MENUDENCIAS.")
            else:
                ok.append("Admin tiene permiso de ver DDJJ_MENUDENCIAS")
            if perm is not None and not perm.puede_exportar:
                ok.append("Admin sin permiso de exportar (revisar si es esperado)")

    print("--- SMOKE CHECK ---")
    for line in ok:
        print(f"  [OK]   {line}")
    for line in failures:
        print(f"  [FAIL] {line}")
    print(f"resultado: {'OK' if not failures else 'FAIL'} ({len(ok)} ok / {len(failures)} fail)")
    if failures:
        sys.exit(1)


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8521"))
    app.run(host="0.0.0.0", port=port)
