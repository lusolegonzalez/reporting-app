"""auditorias_consultas_reportes: agregar duracion_ms

Revision ID: 0010_auditoria_duracion_ms
Revises: 0009_roles_reportes_permisos_exp
Create Date: 2026-04-30 00:00:01.000000
"""
from alembic import op
import sqlalchemy as sa


revision = "0010_auditoria_duracion_ms"
down_revision = "0009_roles_reportes_permisos_exp"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "auditorias_consultas_reportes",
        sa.Column("duracion_ms", sa.Integer(), nullable=True),
    )


def downgrade():
    op.drop_column("auditorias_consultas_reportes", "duracion_ms")
