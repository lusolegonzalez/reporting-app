from datetime import datetime, timezone

from app.extensions import db


class Rol(db.Model):
    __tablename__ = "roles"
    __table_args__ = (db.UniqueConstraint("nombre", name="uq_roles_nombre"),)

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(80), nullable=False)
    descripcion = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    usuarios = db.relationship("UsuarioRol", back_populates="rol", cascade="all, delete-orphan")
    reportes_permisos = db.relationship("RolReportePermiso", back_populates="rol", cascade="all, delete-orphan")
