"""staging movimientos/faena y core.faena

Revision ID: 0006_faena
Revises: 0005_tropa_subtropa
Create Date: 2026-04-29 00:20:00.000000

Crea staging.twins_movimientos, staging.twins_faena y la tabla
normalizada core.faena. core.faena referencia a core.subtropa y a
core.operario; el vinculo subtropa se resuelve por twins_lista_detalle_id.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0006_faena"
down_revision = "0005_tropa_subtropa"
branch_labels = None
depends_on = None


def upgrade():
    # ---------------- staging.twins_movimientos ----------------
    op.create_table(
        "twins_movimientos",
        sa.Column("etl_ejecucion_id", sa.Integer(), nullable=False),
        sa.Column("source_pk", sa.Text(), nullable=False),
        sa.Column("twins_movimiento_id", sa.BigInteger(), nullable=True),
        sa.Column("twins_identificador_id", sa.BigInteger(), nullable=True),
        sa.Column("fecha_movimiento", sa.Date(), nullable=True),
        sa.Column("fecha_creacion", sa.DateTime(timezone=False), nullable=True),
        sa.Column("es_entrada", sa.Boolean(), nullable=True),
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
            name="pk_stg_twins_movimientos",
        ),
        schema="staging",
    )
    op.create_index(
        "ix_stg_movimientos_ejecucion",
        "twins_movimientos",
        ["etl_ejecucion_id"],
        schema="staging",
    )
    op.create_index(
        "ix_stg_movimientos_fecha",
        "twins_movimientos",
        ["fecha_movimiento"],
        schema="staging",
    )
    op.create_index(
        "ix_stg_movimientos_identificador",
        "twins_movimientos",
        ["twins_identificador_id"],
        schema="staging",
    )

    # ---------------- staging.twins_faena ----------------
    op.create_table(
        "twins_faena",
        sa.Column("etl_ejecucion_id", sa.Integer(), nullable=False),
        sa.Column("source_pk", sa.Text(), nullable=False),
        sa.Column("twins_faena_id", sa.BigInteger(), nullable=True),
        sa.Column("twins_identificador_id", sa.BigInteger(), nullable=True),
        sa.Column("twins_lista_detalle_id", sa.BigInteger(), nullable=True),
        sa.Column("twins_operario_id", sa.BigInteger(), nullable=True),
        sa.Column("fecha_faena", sa.Date(), nullable=True),
        sa.Column("cabezas", sa.Integer(), nullable=True),
        sa.Column("kg_estimados", sa.Numeric(18, 3), nullable=True),
        sa.Column("activa", sa.Boolean(), nullable=True),
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
            name="pk_stg_twins_faena",
        ),
        schema="staging",
    )
    op.create_index(
        "ix_stg_faena_ejecucion",
        "twins_faena",
        ["etl_ejecucion_id"],
        schema="staging",
    )
    op.create_index(
        "ix_stg_faena_fecha",
        "twins_faena",
        ["fecha_faena"],
        schema="staging",
    )
    op.create_index(
        "ix_stg_faena_identificador",
        "twins_faena",
        ["twins_identificador_id"],
        schema="staging",
    )

    # ---------------- core.faena ----------------
    op.create_table(
        "faena",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("twins_faena_id", sa.BigInteger(), nullable=False),
        sa.Column("twins_identificador_id", sa.BigInteger(), nullable=False),
        sa.Column("fecha_faena", sa.Date(), nullable=False),
        sa.Column("subtropa_id", sa.BigInteger(), nullable=True),
        sa.Column("operario_id", sa.BigInteger(), nullable=True),
        sa.Column("cabezas", sa.Integer(), nullable=True),
        sa.Column("kg_estimados", sa.Numeric(18, 3), nullable=True),
        sa.Column("vigente", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("etl_ejecucion_id_ult", sa.Integer(), nullable=True),
        sa.Column(
            "actualizado_en",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["subtropa_id"], ["core.subtropa.id"]),
        sa.ForeignKeyConstraint(["operario_id"], ["core.operario.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("twins_faena_id", name="uq_faena_twins_faena_id"),
        schema="core",
    )
    op.create_index("ix_faena_fecha", "faena", ["fecha_faena"], schema="core")
    op.create_index(
        "ix_faena_identificador",
        "faena",
        ["twins_identificador_id"],
        schema="core",
    )
    op.create_index("ix_faena_subtropa", "faena", ["subtropa_id"], schema="core")


def downgrade():
    op.drop_index("ix_faena_subtropa", table_name="faena", schema="core")
    op.drop_index("ix_faena_identificador", table_name="faena", schema="core")
    op.drop_index("ix_faena_fecha", table_name="faena", schema="core")
    op.drop_table("faena", schema="core")

    op.drop_index(
        "ix_stg_faena_identificador",
        table_name="twins_faena",
        schema="staging",
    )
    op.drop_index("ix_stg_faena_fecha", table_name="twins_faena", schema="staging")
    op.drop_index("ix_stg_faena_ejecucion", table_name="twins_faena", schema="staging")
    op.drop_table("twins_faena", schema="staging")

    op.drop_index(
        "ix_stg_movimientos_identificador",
        table_name="twins_movimientos",
        schema="staging",
    )
    op.drop_index(
        "ix_stg_movimientos_fecha",
        table_name="twins_movimientos",
        schema="staging",
    )
    op.drop_index(
        "ix_stg_movimientos_ejecucion",
        table_name="twins_movimientos",
        schema="staging",
    )
    op.drop_table("twins_movimientos", schema="staging")
