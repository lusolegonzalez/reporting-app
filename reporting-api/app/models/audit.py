from datetime import datetime, timezone

from app.extensions import db


class AuditoriaConsultaReporte(db.Model):
    __tablename__ = "auditorias_consultas_reportes"
    __table_args__ = (
        db.Index("ix_auditorias_consultas_reportes_fecha_consulta", "fecha_consulta"),
        db.Index("ix_auditorias_consultas_reportes_resultado_ok", "resultado_ok"),
    )

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False, index=True)
    reporte_id = db.Column(db.Integer, db.ForeignKey("reportes.id"), nullable=False, index=True)
    filtros_json = db.Column(db.Text, nullable=True)
    fecha_consulta = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    resultado_ok = db.Column(db.Boolean, nullable=False, default=True)
    observaciones = db.Column(db.Text, nullable=True)

    usuario = db.relationship("Usuario", back_populates="auditorias_consultas")
    reporte = db.relationship("Reporte", back_populates="auditorias_consultas")
