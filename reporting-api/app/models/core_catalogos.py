from datetime import datetime, timezone

from app.extensions import db


class Mercaderia(db.Model):
    """Mercaderia normalizada con su categoria de reporting."""

    __tablename__ = "mercaderia"
    __table_args__ = (
        db.UniqueConstraint("twins_id", name="uq_mercaderia_twins_id"),
        db.CheckConstraint(
            "origen_clasificacion IN ('AUTO','MANUAL')",
            name="ck_mercaderia_origen_clasificacion",
        ),
        db.Index("ix_mercaderia_codigo", "codigo"),
        db.Index("ix_mercaderia_categoria", "categoria_id"),
        {"schema": "core"},
    )

    id = db.Column(db.BigInteger, primary_key=True)
    twins_id = db.Column(db.BigInteger, nullable=False)
    codigo = db.Column(db.Text, nullable=False)
    descripcion = db.Column(db.Text, nullable=False)
    categoria_id = db.Column(
        db.SmallInteger,
        db.ForeignKey("core.mercaderia_categoria.id"),
        nullable=False,
    )
    origen_clasificacion = db.Column(db.Text, nullable=False, default="AUTO")
    vigente = db.Column(db.Boolean, nullable=False, default=True)
    etl_ejecucion_id_alta = db.Column(db.Integer, nullable=True)
    etl_ejecucion_id_ult = db.Column(db.Integer, nullable=True)
    creado_en = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    actualizado_en = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    categoria = db.relationship("MercaderiaCategoria")


class Operario(db.Model):
    """Operario de Twins (faena / emision)."""

    __tablename__ = "operario"
    __table_args__ = (
        db.UniqueConstraint("twins_id", name="uq_operario_twins_id"),
        {"schema": "core"},
    )

    id = db.Column(db.BigInteger, primary_key=True)
    twins_id = db.Column(db.BigInteger, nullable=False)
    codigo = db.Column(db.Text, nullable=True)
    descripcion = db.Column(db.Text, nullable=True)
    vigente = db.Column(db.Boolean, nullable=False, default=True)
    etl_ejecucion_id_ult = db.Column(db.Integer, nullable=True)
    actualizado_en = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
