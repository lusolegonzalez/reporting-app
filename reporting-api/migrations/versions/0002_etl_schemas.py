"""etl schemas y tablas de trazabilidad por ejecucion

Revision ID: 0002_etl_schemas
Revises: 0001_initial
Create Date: 2026-04-29 00:00:00.000000

Crea los schemas base de la arquitectura de reporting (staging, core,
reporting, etl) y las tablas de trazabilidad por-tabla y de errores
asociadas a cada ejecucion ETL. Las ejecuciones siguen registrandose
en public.ejecuciones_importacion (creada en 0001_initial).
"""
from alembic import op
import sqlalchemy as sa


revision = "0002_etl_schemas"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


SCHEMAS = ("staging", "core", "reporting", "etl")


def upgrade():
    for schema in SCHEMAS:
        op.execute(sa.text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"'))

    op.create_table(
        "ejecucion_tabla",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("ejecucion_id", sa.Integer(), nullable=False),
        sa.Column("tabla_destino", sa.Text(), nullable=False),
        sa.Column("filas_leidas", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("filas_insertadas", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("filas_actualizadas", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("filas_descartadas", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("duracion_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "creado_en",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["ejecucion_id"],
            ["public.ejecuciones_importacion.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        schema="etl",
    )
    op.create_index(
        "ix_etl_ejecucion_tabla_ejecucion",
        "ejecucion_tabla",
        ["ejecucion_id"],
        schema="etl",
    )

    op.create_table(
        "ejecucion_error",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("ejecucion_id", sa.Integer(), nullable=False),
        sa.Column("tabla_destino", sa.Text(), nullable=False),
        sa.Column("source_pk", sa.Text(), nullable=True),
        sa.Column("mensaje", sa.Text(), nullable=False),
        sa.Column("payload", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column(
            "ocurrido_en",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["ejecucion_id"],
            ["public.ejecuciones_importacion.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        schema="etl",
    )
    op.create_index(
        "ix_etl_ejecucion_error_ejecucion",
        "ejecucion_error",
        ["ejecucion_id"],
        schema="etl",
    )


def downgrade():
    op.drop_index(
        "ix_etl_ejecucion_error_ejecucion",
        table_name="ejecucion_error",
        schema="etl",
    )
    op.drop_table("ejecucion_error", schema="etl")

    op.drop_index(
        "ix_etl_ejecucion_tabla_ejecucion",
        table_name="ejecucion_tabla",
        schema="etl",
    )
    op.drop_table("ejecucion_tabla", schema="etl")

    # Schemas se eliminan solo si quedaron vacios; reporting/core/staging
    # pueden contener objetos creados en migraciones posteriores.
    for schema in reversed(SCHEMAS):
        op.execute(sa.text(f'DROP SCHEMA IF EXISTS "{schema}" RESTRICT'))
