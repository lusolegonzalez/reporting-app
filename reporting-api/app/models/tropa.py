from datetime import datetime, timezone

from app.extensions import db


class Tropa(db.Model):
    """Tropa (cabecera de ingreso de hacienda)."""

    __tablename__ = "tropa"
    __table_args__ = (
        db.UniqueConstraint(
            "twins_ingreso_hacienda_id",
            name="uq_tropa_twins_ingreso_hacienda_id",
        ),
        db.Index("ix_tropa_numero", "numero_tropa"),
        {"schema": "core"},
    )

    id = db.Column(db.BigInteger, primary_key=True)
    twins_ingreso_hacienda_id = db.Column(db.BigInteger, nullable=False)
    numero_tropa = db.Column(db.Text, nullable=False)
    fecha_ingreso = db.Column(db.Date, nullable=True)
    proveedor_codigo = db.Column(db.Text, nullable=True)
    proveedor_nombre = db.Column(db.Text, nullable=True)
    etl_ejecucion_id_ult = db.Column(db.Integer, nullable=True)
    actualizado_en = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    subtropas = db.relationship("Subtropa", back_populates="tropa")


class Subtropa(db.Model):
    """Subtropa / parcial de una tropa."""

    __tablename__ = "subtropa"
    __table_args__ = (
        db.UniqueConstraint(
            "twins_subtropa_id",
            name="uq_subtropa_twins_subtropa_id",
        ),
        db.Index("ix_subtropa_tropa", "tropa_id"),
        db.Index("ix_subtropa_lista_detalle", "twins_lista_detalle_id"),
        {"schema": "core"},
    )

    id = db.Column(db.BigInteger, primary_key=True)
    tropa_id = db.Column(
        db.BigInteger,
        db.ForeignKey("core.tropa.id"),
        nullable=False,
    )
    twins_subtropa_id = db.Column(db.BigInteger, nullable=False)
    twins_lista_detalle_id = db.Column(db.BigInteger, nullable=True)
    numero_subtropa = db.Column(db.Text, nullable=True)
    cabezas_declaradas = db.Column(db.Integer, nullable=True)
    etl_ejecucion_id_ult = db.Column(db.Integer, nullable=True)
    actualizado_en = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    tropa = db.relationship("Tropa", back_populates="subtropas")
