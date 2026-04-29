from datetime import datetime, timezone

from sqlalchemy.dialects.postgresql import JSONB

from app.extensions import db


class StgTwinsMercaderia(db.Model):
    __tablename__ = "twins_mercaderias"
    __table_args__ = (
        db.Index("ix_stg_mercaderias_ejecucion", "etl_ejecucion_id"),
        db.PrimaryKeyConstraint(
            "etl_ejecucion_id",
            "source_pk",
            name="pk_stg_twins_mercaderias",
        ),
        {"schema": "staging"},
    )

    etl_ejecucion_id = db.Column(db.Integer, nullable=False)
    source_pk = db.Column(db.Text, nullable=False)
    twins_id = db.Column(db.BigInteger, nullable=True)
    codigo = db.Column(db.Text, nullable=True)
    descripcion = db.Column(db.Text, nullable=True)
    payload = db.Column(JSONB, nullable=True)
    row_hash = db.Column(db.Text, nullable=True)
    ingerido_en = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )


class StgTwinsOperario(db.Model):
    __tablename__ = "twins_operarios"
    __table_args__ = (
        db.Index("ix_stg_operarios_ejecucion", "etl_ejecucion_id"),
        db.PrimaryKeyConstraint(
            "etl_ejecucion_id",
            "source_pk",
            name="pk_stg_twins_operarios",
        ),
        {"schema": "staging"},
    )

    etl_ejecucion_id = db.Column(db.Integer, nullable=False)
    source_pk = db.Column(db.Text, nullable=False)
    twins_id = db.Column(db.BigInteger, nullable=True)
    codigo = db.Column(db.Text, nullable=True)
    descripcion = db.Column(db.Text, nullable=True)
    payload = db.Column(JSONB, nullable=True)
    ingerido_en = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )


class StgTwinsTropa(db.Model):
    __tablename__ = "twins_tropas"
    __table_args__ = (
        db.Index("ix_stg_tropas_ejecucion", "etl_ejecucion_id"),
        db.Index("ix_stg_tropas_subtropa", "twins_subtropa_id"),
        db.Index("ix_stg_tropas_lista_detalle", "twins_lista_detalle_id"),
        db.PrimaryKeyConstraint(
            "etl_ejecucion_id",
            "source_pk",
            name="pk_stg_twins_tropas",
        ),
        {"schema": "staging"},
    )

    etl_ejecucion_id = db.Column(db.Integer, nullable=False)
    source_pk = db.Column(db.Text, nullable=False)
    twins_ingreso_hacienda_id = db.Column(db.BigInteger, nullable=True)
    twins_subtropa_id = db.Column(db.BigInteger, nullable=True)
    twins_subtropa_detalle_id = db.Column(db.BigInteger, nullable=True)
    twins_lista_detalle_id = db.Column(db.BigInteger, nullable=True)
    numero_tropa = db.Column(db.Text, nullable=True)
    numero_subtropa = db.Column(db.Text, nullable=True)
    cabezas_declaradas = db.Column(db.Integer, nullable=True)
    fecha_ingreso = db.Column(db.Date, nullable=True)
    proveedor_codigo = db.Column(db.Text, nullable=True)
    proveedor_nombre = db.Column(db.Text, nullable=True)
    payload = db.Column(JSONB, nullable=True)
    ingerido_en = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )


class StgTwinsMovimiento(db.Model):
    __tablename__ = "twins_movimientos"
    __table_args__ = (
        db.Index("ix_stg_movimientos_ejecucion", "etl_ejecucion_id"),
        db.Index("ix_stg_movimientos_fecha", "fecha_movimiento"),
        db.Index("ix_stg_movimientos_identificador", "twins_identificador_id"),
        db.PrimaryKeyConstraint(
            "etl_ejecucion_id",
            "source_pk",
            name="pk_stg_twins_movimientos",
        ),
        {"schema": "staging"},
    )

    etl_ejecucion_id = db.Column(db.Integer, nullable=False)
    source_pk = db.Column(db.Text, nullable=False)
    twins_movimiento_id = db.Column(db.BigInteger, nullable=True)
    twins_identificador_id = db.Column(db.BigInteger, nullable=True)
    fecha_movimiento = db.Column(db.Date, nullable=True)
    fecha_creacion = db.Column(db.DateTime(timezone=False), nullable=True)
    es_entrada = db.Column(db.Boolean, nullable=True)
    payload = db.Column(JSONB, nullable=True)
    ingerido_en = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )


class StgTwinsFaena(db.Model):
    __tablename__ = "twins_faena"
    __table_args__ = (
        db.Index("ix_stg_faena_ejecucion", "etl_ejecucion_id"),
        db.Index("ix_stg_faena_fecha", "fecha_faena"),
        db.Index("ix_stg_faena_identificador", "twins_identificador_id"),
        db.PrimaryKeyConstraint(
            "etl_ejecucion_id",
            "source_pk",
            name="pk_stg_twins_faena",
        ),
        {"schema": "staging"},
    )

    etl_ejecucion_id = db.Column(db.Integer, nullable=False)
    source_pk = db.Column(db.Text, nullable=False)
    twins_faena_id = db.Column(db.BigInteger, nullable=True)
    twins_identificador_id = db.Column(db.BigInteger, nullable=True)
    twins_lista_detalle_id = db.Column(db.BigInteger, nullable=True)
    twins_operario_id = db.Column(db.BigInteger, nullable=True)
    fecha_faena = db.Column(db.Date, nullable=True)
    cabezas = db.Column(db.Integer, nullable=True)
    kg_estimados = db.Column(db.Numeric(18, 3), nullable=True)
    activa = db.Column(db.Boolean, nullable=True)
    payload = db.Column(JSONB, nullable=True)
    ingerido_en = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )


class StgTwinsSalida(db.Model):
    __tablename__ = "twins_salidas"
    __table_args__ = (
        db.Index("ix_stg_salidas_ejecucion", "etl_ejecucion_id"),
        db.Index("ix_stg_salidas_identificador", "twins_identificador_id"),
        db.Index("ix_stg_salidas_mercaderia", "twins_mercaderia_id"),
        db.PrimaryKeyConstraint(
            "etl_ejecucion_id",
            "source_pk",
            name="pk_stg_twins_salidas",
        ),
        {"schema": "staging"},
    )

    etl_ejecucion_id = db.Column(db.Integer, nullable=False)
    source_pk = db.Column(db.Text, nullable=False)
    twins_movimiento_id = db.Column(db.BigInteger, nullable=True)
    twins_identificador_id = db.Column(db.BigInteger, nullable=True)
    twins_mercaderia_id = db.Column(db.BigInteger, nullable=True)
    cantidad = db.Column(db.Numeric(18, 3), nullable=True)
    peso_gr = db.Column(db.Numeric(18, 3), nullable=True)
    activa = db.Column(db.Boolean, nullable=True)
    eliminada = db.Column(db.Boolean, nullable=True)
    dedup_key = db.Column(db.Text, nullable=True)
    payload = db.Column(JSONB, nullable=True)
    ingerido_en = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
