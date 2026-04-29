"""staging y core de mercaderias y operarios

Revision ID: 0004_mercaderia_operario
Revises: 0003_mercaderia_categorias
Create Date: 2026-04-29 00:10:00.000000

Crea las tablas de staging para mercaderias y operarios provenientes
de Twins, y sus contrapartes normalizadas en core. core.mercaderia
referencia core.mercaderia_categoria (asignada por reglas durante el
ETL o manualmente).
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0004_mercaderia_operario"
down_revision = "0003_mercaderia_categorias"
branch_labels = None
depends_on = None


def upgrade():
    # ---------------- staging.twins_mercaderias ----------------
    op.create_table(
        "twins_mercaderias",
        sa.Column("etl_ejecucion_id", sa.Integer(), nullable=False),
        sa.Column("source_pk", sa.Text(), nullable=False),
        sa.Column("twins_id", sa.BigInteger(), nullable=True),
        sa.Column("codigo", sa.Text(), nullable=True),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("payload", postgresql.JSONB(), nullable=True),
        sa.Column("row_hash", sa.Text(), nullable=True),
        sa.Column(
            "ingerido_en",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint(
            "etl_ejecucion_id",
            "source_pk",
            name="pk_stg_twins_mercaderias",
        ),
        schema="staging",
    )
    op.create_index(
        "ix_stg_mercaderias_ejecucion",
        "twins_mercaderias",
        ["etl_ejecucion_id"],
        schema="staging",
    )

    # ---------------- staging.twins_operarios ----------------
    op.create_table(
        "twins_operarios",
        sa.Column("etl_ejecucion_id", sa.Integer(), nullable=False),
        sa.Column("source_pk", sa.Text(), nullable=False),
        sa.Column("twins_id", sa.BigInteger(), nullable=True),
        sa.Column("codigo", sa.Text(), nullable=True),
        sa.Column("descripcion", sa.Text(), nullable=True),
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
            name="pk_stg_twins_operarios",
        ),
        schema="staging",
    )
    op.create_index(
        "ix_stg_operarios_ejecucion",
        "twins_operarios",
        ["etl_ejecucion_id"],
        schema="staging",
    )

    # ---------------- core.mercaderia ----------------
    op.create_table(
        "mercaderia",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("twins_id", sa.BigInteger(), nullable=False),
        sa.Column("codigo", sa.Text(), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=False),
        sa.Column("categoria_id", sa.SmallInteger(), nullable=False),
        sa.Column(
            "origen_clasificacion",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'AUTO'"),
        ),
        sa.Column("vigente", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("etl_ejecucion_id_alta", sa.Integer(), nullable=True),
        sa.Column("etl_ejecucion_id_ult", sa.Integer(), nullable=True),
        sa.Column(
            "creado_en",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "actualizado_en",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "origen_clasificacion IN ('AUTO','MANUAL')",
            name="ck_mercaderia_origen_clasificacion",
        ),
        sa.ForeignKeyConstraint(
            ["categoria_id"],
            ["core.mercaderia_categoria.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("twins_id", name="uq_mercaderia_twins_id"),
        schema="core",
    )
    op.create_index("ix_mercaderia_codigo", "mercaderia", ["codigo"], schema="core")
    op.create_index(
        "ix_mercaderia_categoria",
        "mercaderia",
        ["categoria_id"],
        schema="core",
    )

    # ---------------- core.operario ----------------
    op.create_table(
        "operario",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("twins_id", sa.BigInteger(), nullable=False),
        sa.Column("codigo", sa.Text(), nullable=True),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("vigente", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("etl_ejecucion_id_ult", sa.Integer(), nullable=True),
        sa.Column(
            "actualizado_en",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("twins_id", name="uq_operario_twins_id"),
        schema="core",
    )


def downgrade():
    op.drop_table("operario", schema="core")

    op.drop_index("ix_mercaderia_categoria", table_name="mercaderia", schema="core")
    op.drop_index("ix_mercaderia_codigo", table_name="mercaderia", schema="core")
    op.drop_table("mercaderia", schema="core")

    op.drop_index(
        "ix_stg_operarios_ejecucion",
        table_name="twins_operarios",
        schema="staging",
    )
    op.drop_table("twins_operarios", schema="staging")

    op.drop_index(
        "ix_stg_mercaderias_ejecucion",
        table_name="twins_mercaderias",
        schema="staging",
    )
    op.drop_table("twins_mercaderias", schema="staging")
