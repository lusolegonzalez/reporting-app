from datetime import datetime, timezone

from app.extensions import db


class Reporte(db.Model):
    __tablename__ = "reportes"
    __table_args__ = (
        db.UniqueConstraint("codigo", name="uq_reportes_codigo"),
        db.Index("ix_reportes_activo", "activo"),
    )

    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(50), nullable=False)
    nombre = db.Column(db.String(120), nullable=False)
    descripcion = db.Column(db.String(255), nullable=True)
    activo = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    roles_permisos = db.relationship("RolReportePermiso", back_populates="reporte", cascade="all, delete-orphan")
    auditorias_consultas = db.relationship("AuditoriaConsultaReporte", back_populates="reporte")


class RolReportePermiso(db.Model):
    __tablename__ = "roles_reportes_permisos"
    __table_args__ = (
        db.UniqueConstraint("rol_id", "reporte_id", name="uq_roles_reportes_permisos_rol_reporte"),
    )

    id = db.Column(db.Integer, primary_key=True)
    rol_id = db.Column(db.Integer, db.ForeignKey("roles.id"), nullable=False, index=True)
    reporte_id = db.Column(db.Integer, db.ForeignKey("reportes.id"), nullable=False, index=True)
    puede_ver = db.Column(db.Boolean, nullable=False, default=False)

    rol = db.relationship("Rol", back_populates="reportes_permisos")
    reporte = db.relationship("Reporte", back_populates="roles_permisos")
