"""staging.twins_salidas y core.salida

Revision ID: 0007_salida
Revises: 0006_faena
Create Date: 2026-04-29 00:25:00.000000

Crea staging.twins_salidas (lineas de emision/salida de Twins) y la
tabla normalizada core.salida con dedup_key unica por fecha de
emision. faena_id queda como FK opcional para permitir resolucion
diferida cuando la faena aun no fue importada.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0007_salida"
down_revision = "0006_faena"
branch_labels = None
depends_on = None


def upgrade():
    # ---------------- staging.twins_salidas ----------------
    op.create_table(
        "twins_salidas",
        sa.Column("etl_ejecucion_id", sa.Integer(), nullable=False),
        sa.Column("source_pk", sa.Text(), nullable=False),
        sa.Column("twins_movimiento_id", sa.BigInteger(), nullable=True),
        sa.Column("twins_identificador_id", sa.BigInteger(), nullable=True),
        sa.Column("twins_mercaderia_id", sa.BigInteger(), nullable=True),
        sa.Column("cantidad", sa.Numeric(18, 3), nullable=True),
        sa.Column("peso_gr", sa.Numeric(18, 3), nullable=True),
        sa.Column("activa", sa.Boolean(), nullable=True),
        sa.Column("eliminada", sa.Boolean(), nullable=True),
        sa.Column("dedup_key", sa.Text(), nullable=True),
        sa.Column("payload", postgresql.JSONB(), nullable=True),
        sa.Column(
            "ingerido_en",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint(
            "etl_ejecucion_id",
            "source_pk",
            name="pk_stg_twins_salidas",
        ),
        schema="staging",
    )
    op.create_index(
        "ix_stg_salidas_ejecucion",
        "twins_salidas",
        ["etl_ejecucion_id"],
        schema="staging",
    )
    op.create_index(
        "ix_stg_salidas_identificador",
        "twins_salidas",
        ["twins_identificador_id"],
        schema="staging",
    )
    op.create_index(
        "ix_stg_salidas_mercaderia",
        "twins_salidas",
        ["twins_mercaderia_id"],
        schema="staging",
    )

    # ---------------- core.salida ----------------
    op.create_table(
        "salida",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("twins_movimiento_id", sa.BigInteger(), nullable=False),
        sa.Column("twins_identificador_id", sa.BigInteger(), nullable=False),
        sa.Column("twins_salida_pk", sa.Text(), nullable=False),
        sa.Column("fecha_emision", sa.Date(), nullable=False),
        sa.Column("fecha_creacion", sa.DateTime(timezone=False), nullable=True),
        sa.Column("mercaderia_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "cantidad_cajas",
            sa.Numeric(18, 3),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "peso_kg",
            sa.Numeric(18, 3),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("faena_id", sa.BigInteger(), nullable=True),
        sa.Column("operario_id", sa.BigInteger(), nullable=True),
        sa.Column("dedup_key", sa.Text(), nullable=False),
        sa.Column("vigente", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("etl_ejecucion_id_ult", sa.Integer(), nullable=True),
        sa.Column(
            "actualizado_en",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["mercaderia_id"], ["core.mercaderia.id"]),
        sa.ForeignKeyConstraint(["faena_id"], ["core.faena.id"]),
        sa.ForeignKeyConstraint(["operario_id"], ["core.operario.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("twins_salida_pk", name="uq_salida_origen"),
        sa.UniqueConstraint(
            "fecha_emision",
            "dedup_key",
            name="uq_salida_dedup",
        ),
        schema="core",
    )
    op.create_index("ix_salida_fecha", "salida", ["fecha_emision"], schema="core")
    op.create_index(
        "ix_salida_mercaderia",
        "salida",
        ["mercaderia_id"],
        schema="core",
    )
    op.create_index("ix_salida_faena", "salida", ["faena_id"], schema="core")
    op.create_index(
        "ix_salida_identificador",
        "salida",
        ["twins_identificador_id"],
        schema="core",
    )


def downgrade():
    op.drop_index("ix_salida_identificador", table_name="salida", schema="core")
    op.drop_index("ix_salida_faena", table_name="salida", schema="core")
    op.drop_index("ix_salida_mercaderia", table_name="salida", schema="core")
    op.drop_index("ix_salida_fecha", table_name="salida", schema="core")
    op.drop_table("salida", schema="core")

    op.drop_index(
        "ix_stg_salidas_mercaderia",
        table_name="twins_salidas",
        schema="staging",
    )
    op.drop_index(
        "ix_stg_salidas_identificador",
        table_name="twins_salidas",
        schema="staging",
    )
    op.drop_index(
        "ix_stg_salidas_ejecucion",
        table_name="twins_salidas",
        schema="staging",
    )
    op.drop_table("twins_salidas", schema="staging")
