from datetime import datetime, timezone

from app.extensions import db


class Reporte(db.Model):
    __tablename__ = "reportes"

    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(50), nullable=False, unique=True)
    nombre = db.Column(db.String(120), nullable=False)
    descripcion = db.Column(db.String(255), nullable=True)
    activo = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))


class RolReportePermiso(db.Model):
    __tablename__ = "roles_reportes_permisos"

    id = db.Column(db.Integer, primary_key=True)
    rol_id = db.Column(db.Integer, db.ForeignKey("roles.id"), nullable=False, index=True)
    reporte_id = db.Column(db.Integer, db.ForeignKey("reportes.id"), nullable=False, index=True)
    puede_ver = db.Column(db.Boolean, nullable=False, default=False)
