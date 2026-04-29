"""staging y core de tropas y subtropas

Revision ID: 0005_tropa_subtropa
Revises: 0004_mercaderia_operario
Create Date: 2026-04-29 00:15:00.000000

Crea staging.twins_tropas (forma compactada del join entre
ingreso_hacienda, subtropa, subtropa_detalle y lista_detalle de Twins)
y las tablas normalizadas core.tropa y core.subtropa.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0005_tropa_subtropa"
down_revision = "0004_mercaderia_operario"
branch_labels = None
depends_on = None


def upgrade():
    # ---------------- staging.twins_tropas ----------------
    op.create_table(
        "twins_tropas",
        sa.Column("etl_ejecucion_id", sa.Integer(), nullable=False),
        sa.Column("source_pk", sa.Text(), nullable=False),
        sa.Column("twins_ingreso_hacienda_id", sa.BigInteger(), nullable=True),
        sa.Column("twins_subtropa_id", sa.BigInteger(), nullable=True),
        sa.Column("twins_subtropa_detalle_id", sa.BigInteger(), nullable=True),
        sa.Column("twins_lista_detalle_id", sa.BigInteger(), nullable=True),
        sa.Column("numero_tropa", sa.Text(), nullable=True),
        sa.Column("numero_subtropa", sa.Text(), nullable=True),
        sa.Column("cabezas_declaradas", sa.Integer(), nullable=True),
        sa.Column("fecha_ingreso", sa.Date(), nullable=True),
        sa.Column("proveedor_codigo", sa.Text(), nullable=True),
        sa.Column("proveedor_nombre", sa.Text(), nullable=True),
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
            name="pk_stg_twins_tropas",
        ),
        schema="staging",
    )
    op.create_index(
        "ix_stg_tropas_ejecucion",
        "twins_tropas",
        ["etl_ejecucion_id"],
        schema="staging",
    )
    op.create_index(
        "ix_stg_tropas_subtropa",
        "twins_tropas",
        ["twins_subtropa_id"],
        schema="staging",
    )
    op.create_index(
        "ix_stg_tropas_lista_detalle",
        "twins_tropas",
        ["twins_lista_detalle_id"],
        schema="staging",
    )

    # ---------------- core.tropa ----------------
    op.create_table(
        "tropa",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("twins_ingreso_hacienda_id", sa.BigInteger(), nullable=False),
        sa.Column("numero_tropa", sa.Text(), nullable=False),
        sa.Column("fecha_ingreso", sa.Date(), nullable=True),
        sa.Column("proveedor_codigo", sa.Text(), nullable=True),
        sa.Column("proveedor_nombre", sa.Text(), nullable=True),
        sa.Column("etl_ejecucion_id_ult", sa.Integer(), nullable=True),
        sa.Column(
            "actualizado_en",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "twins_ingreso_hacienda_id",
            name="uq_tropa_twins_ingreso_hacienda_id",
        ),
        schema="core",
    )
    op.create_index("ix_tropa_numero", "tropa", ["numero_tropa"], schema="core")

    # ---------------- core.subtropa ----------------
    op.create_table(
        "subtropa",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("tropa_id", sa.BigInteger(), nullable=False),
        sa.Column("twins_subtropa_id", sa.BigInteger(), nullable=False),
        sa.Column("twins_lista_detalle_id", sa.BigInteger(), nullable=True),
        sa.Column("numero_subtropa", sa.Text(), nullable=True),
        sa.Column("cabezas_declaradas", sa.Integer(), nullable=True),
        sa.Column("etl_ejecucion_id_ult", sa.Integer(), nullable=True),
        sa.Column(
            "actualizado_en",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["tropa_id"], ["core.tropa.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "twins_subtropa_id",
            name="uq_subtropa_twins_subtropa_id",
        ),
        schema="core",
    )
    op.create_index("ix_subtropa_tropa", "subtropa", ["tropa_id"], schema="core")
    op.create_index(
        "ix_subtropa_lista_detalle",
        "subtropa",
        ["twins_lista_detalle_id"],
        schema="core",
    )


def downgrade():
    op.drop_index("ix_subtropa_lista_detalle", table_name="subtropa", schema="core")
    op.drop_index("ix_subtropa_tropa", table_name="subtropa", schema="core")
    op.drop_table("subtropa", schema="core")

    op.drop_index("ix_tropa_numero", table_name="tropa", schema="core")
    op.drop_table("tropa", schema="core")

    op.drop_index(
        "ix_stg_tropas_lista_detalle",
        table_name="twins_tropas",
        schema="staging",
    )
    op.drop_index(
        "ix_stg_tropas_subtropa",
        table_name="twins_tropas",
        schema="staging",
    )
    op.drop_index(
        "ix_stg_tropas_ejecucion",
        table_name="twins_tropas",
        schema="staging",
    )
    op.drop_table("twins_tropas", schema="staging")
