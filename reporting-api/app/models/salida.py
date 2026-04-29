from datetime import datetime, timezone

from app.extensions import db


class Salida(db.Model):
    """Linea de emision/salida normalizada y deduplicada."""

    __tablename__ = "salida"
    __table_args__ = (
        db.UniqueConstraint("twins_salida_pk", name="uq_salida_origen"),
        db.UniqueConstraint(
            "fecha_emision",
            "dedup_key",
            name="uq_salida_dedup",
        ),
        db.Index("ix_salida_fecha", "fecha_emision"),
        db.Index("ix_salida_mercaderia", "mercaderia_id"),
        db.Index("ix_salida_faena", "faena_id"),
        db.Index("ix_salida_identificador", "twins_identificador_id"),
        {"schema": "core"},
    )

    id = db.Column(db.BigInteger, primary_key=True)
    twins_movimiento_id = db.Column(db.BigInteger, nullable=False)
    twins_identificador_id = db.Column(db.BigInteger, nullable=False)
    twins_salida_pk = db.Column(db.Text, nullable=False)
    fecha_emision = db.Column(db.Date, nullable=False)
    fecha_creacion = db.Column(db.DateTime(timezone=False), nullable=True)
    mercaderia_id = db.Column(
        db.BigInteger,
        db.ForeignKey("core.mercaderia.id"),
        nullable=False,
    )
    cantidad_cajas = db.Column(db.Numeric(18, 3), nullable=False, default=0)
    peso_kg = db.Column(db.Numeric(18, 3), nullable=False, default=0)
    faena_id = db.Column(
        db.BigInteger,
        db.ForeignKey("core.faena.id"),
        nullable=True,
    )
    operario_id = db.Column(
        db.BigInteger,
        db.ForeignKey("core.operario.id"),
        nullable=True,
    )
    dedup_key = db.Column(db.Text, nullable=False)
    vigente = db.Column(db.Boolean, nullable=False, default=True)
    etl_ejecucion_id_ult = db.Column(db.Integer, nullable=True)
    actualizado_en = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    mercaderia = db.relationship("Mercaderia")
    faena = db.relationship("Faena")
    operario = db.relationship("Operario")
