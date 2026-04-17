"""initial portable schema

Revision ID: 0001_initial_portable_schema
Revises:
Create Date: 2026-04-17
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0001_initial_portable_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Placeholder de migración inicial portable para SQL Server."""
    # Ajustá este archivo en base a tus modelos reales si tu repositorio
    # ya tenía una migración inicial distinta.
    pass


def downgrade() -> None:
    """Rollback placeholder."""
    pass
