from datetime import datetime, timezone

from app.extensions import db


class EjecucionImportacion(db.Model):
    __tablename__ = "ejecuciones_importacion"

    id = db.Column(db.Integer, primary_key=True)
    origen = db.Column(db.String(120), nullable=False)
    fecha_desde = db.Column(db.Date, nullable=False)
    fecha_hasta = db.Column(db.Date, nullable=False)
    estado = db.Column(db.String(40), nullable=False)
    observaciones = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    created_by_user_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True)
