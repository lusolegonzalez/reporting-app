from datetime import datetime, timezone

from sqlalchemy.dialects.postgresql import JSONB

from app.extensions import db


class EjecucionTabla(db.Model):
    """Conteos por tabla destino de una ejecucion ETL."""

    __tablename__ = "ejecucion_tabla"
    __table_args__ = (
        db.Index("ix_etl_ejecucion_tabla_ejecucion", "ejecucion_id"),
        {"schema": "etl"},
    )

    id = db.Column(db.BigInteger, primary_key=True)
    ejecucion_id = db.Column(
        db.Integer,
        db.ForeignKey("ejecuciones_importacion.id", ondelete="CASCADE"),
        nullable=False,
    )
    tabla_destino = db.Column(db.Text, nullable=False)
    filas_leidas = db.Column(db.Integer, nullable=False, default=0)
    filas_insertadas = db.Column(db.Integer, nullable=False, default=0)
    filas_actualizadas = db.Column(db.Integer, nullable=False, default=0)
    filas_descartadas = db.Column(db.Integer, nullable=False, default=0)
    duracion_ms = db.Column(db.Integer, nullable=False, default=0)
    creado_en = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )


class EjecucionError(db.Model):
    """Errores puntuales registrados durante una ejecucion ETL."""

    __tablename__ = "ejecucion_error"
    __table_args__ = (
        db.Index("ix_etl_ejecucion_error_ejecucion", "ejecucion_id"),
        {"schema": "etl"},
    )

    id = db.Column(db.BigInteger, primary_key=True)
    ejecucion_id = db.Column(
        db.Integer,
        db.ForeignKey("ejecuciones_importacion.id", ondelete="CASCADE"),
        nullable=False,
    )
    tabla_destino = db.Column(db.Text, nullable=False)
    source_pk = db.Column(db.Text, nullable=True)
    mensaje = db.Column(db.Text, nullable=False)
    payload = db.Column(JSONB, nullable=True)
    ocurrido_en = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
