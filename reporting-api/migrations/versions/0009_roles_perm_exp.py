"""roles_reportes_permisos: agregar puede_exp

Revision ID: 0009_roles_reportes_permisos_exp
Revises: 0008_reporting_views
Create Date: 2026-04-30 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = "0009_roles_reportes_permisos_exp"
down_revision = "0008_reporting_views"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column(
        "roles_reportes_permisos",
        sa.Column(
            "puede_exportar",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    # Quitamos el server_default una vez backfilleado: el default vive en el modelo.
    op.alter_column("roles_reportes_permisos", "puede_exportar", server_default=None)


def downgrade():
    op.drop_column("roles_reportes_permisos", "puede_exportar")
