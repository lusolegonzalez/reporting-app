from datetime import datetime, timezone

from app.extensions import db


class MercaderiaCategoria(db.Model):
    """Catalogo cerrado de categorias de reporting de mercaderias."""

    __tablename__ = "mercaderia_categoria"
    __table_args__ = (
        db.UniqueConstraint("codigo", name="uq_mercaderia_categoria_codigo"),
        {"schema": "core"},
    )

    id = db.Column(db.SmallInteger, primary_key=True)
    codigo = db.Column(db.Text, nullable=False)
    descripcion = db.Column(db.Text, nullable=False)
    activo = db.Column(db.Boolean, nullable=False, default=True)


class MercaderiaClasificacionRegla(db.Model):
    """Regla declarativa para clasificar mercaderias durante el ETL."""

    __tablename__ = "mercaderia_clasificacion_regla"
    __table_args__ = (
        db.CheckConstraint(
            "tipo_match IN ('PREFIJO_CODIGO','CODIGO_EXACTO','REGEX_DESCRIPCION')",
            name="ck_merc_regla_tipo_match",
        ),
        db.Index(
            "ix_merc_regla_prioridad",
            "prioridad",
            postgresql_where=db.text("activa"),
        ),
        {"schema": "core"},
    )

    id = db.Column(db.Integer, primary_key=True)
    tipo_match = db.Column(db.Text, nullable=False)
    patron = db.Column(db.Text, nullable=False)
    categoria_id = db.Column(
        db.SmallInteger,
        db.ForeignKey("core.mercaderia_categoria.id"),
        nullable=False,
    )
    prioridad = db.Column(db.Integer, nullable=False, default=100)
    activa = db.Column(db.Boolean, nullable=False, default=True)
    creado_en = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    categoria = db.relationship("MercaderiaCategoria")
