"""core.proceso_productivo + core.salida.twins_procesos_id

Revision ID: 0011_proceso_productivo
Revises: 0010_auditoria_duracion_ms
Create Date: 2026-06-03 00:00:00.000000

1. Crea la tabla core.proceso_productivo, que almacena el catalogo de procesos
   productivos de Twins. La fuente correcta en esta instalacion es
   configuracion.Procesos (Id, sCodigo, sDescripcion). El campo twins_id
   guarda configuracion.Procesos.Id.

2. Agrega la columna twins_procesos_id a core.salida. Esta columna almacena
   el Procesos_Id del movimiento asociado a la salida, obtenido via la cadena
   Movimientos.Salidas.Movimiento_Id -> Movimientos.Movimientos.Procesos_Id.
   Permite filtrar salidas por proceso productivo sin JOIN a SQL Server.
"""
from alembic import op
import sqlalchemy as sa


revision = "0011_proceso_productivo"
down_revision = "0010_auditoria_duracion_ms"
branch_labels = None
depends_on = None


def upgrade():
    # 1. Catalogo de procesos productivos (fuente: configuracion.Procesos en Twins)
    op.create_table(
        "proceso_productivo",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("twins_id", sa.BigInteger(), nullable=False),
        sa.Column("codigo", sa.Text(), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=False),
        sa.Column("vigente", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("etl_ejecucion_id_ult", sa.Integer(), nullable=True),
        sa.Column(
            "actualizado_en",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("twins_id", name="uq_proceso_productivo_twins_id"),
        schema="core",
    )
    op.create_index(
        "ix_proceso_productivo_twins_id",
        "proceso_productivo",
        ["twins_id"],
        schema="core",
    )

    # 2. Columna proceso en core.salida para filtrado de reportes
    # Nullable porque los registros existentes no tendran el dato hasta
    # que se reprocese el ETL sobre el rango afectado.
    op.add_column(
        "salida",
        sa.Column("twins_procesos_id", sa.BigInteger(), nullable=True),
        schema="core",
    )
    op.create_index(
        "ix_salida_proceso",
        "salida",
        ["twins_procesos_id"],
        schema="core",
    )


def downgrade():
    op.drop_index("ix_salida_proceso", table_name="salida", schema="core")
    op.drop_column("salida", "twins_procesos_id", schema="core")
    op.drop_index(
        "ix_proceso_productivo_twins_id",
        table_name="proceso_productivo",
        schema="core",
    )
    op.drop_table("proceso_productivo", schema="core")
