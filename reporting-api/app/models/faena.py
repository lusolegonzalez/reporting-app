from datetime import datetime, timezone

from app.extensions import db


class Faena(db.Model):
    """Faena por identificador en una fecha."""

    __tablename__ = "faena"
    __table_args__ = (
        db.UniqueConstraint("twins_faena_id", name="uq_faena_twins_faena_id"),
        db.Index("ix_faena_fecha", "fecha_faena"),
        db.Index("ix_faena_identificador", "twins_identificador_id"),
        db.Index("ix_faena_subtropa", "subtropa_id"),
        {"schema": "core"},
    )

    id = db.Column(db.BigInteger, primary_key=True)
    twins_faena_id = db.Column(db.BigInteger, nullable=False)
    twins_identificador_id = db.Column(db.BigInteger, nullable=False)
    fecha_faena = db.Column(db.Date, nullable=False)
    subtropa_id = db.Column(
        db.BigInteger,
        db.ForeignKey("core.subtropa.id"),
        nullable=True,
    )
    operario_id = db.Column(
        db.BigInteger,
        db.ForeignKey("core.operario.id"),
        nullable=True,
    )
    cabezas = db.Column(db.Integer, nullable=True)
    kg_estimados = db.Column(db.Numeric(18, 3), nullable=True)
    vigente = db.Column(db.Boolean, nullable=False, default=True)
    etl_ejecucion_id_ult = db.Column(db.Integer, nullable=True)
    actualizado_en = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    subtropa = db.relationship("Subtropa")
    operario = db.relationship("Operario")
