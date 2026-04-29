"""catalogos de clasificacion de mercaderias

Revision ID: 0003_mercaderia_categorias
Revises: 0002_etl_schemas
Create Date: 2026-04-29 00:05:00.000000

Crea los catalogos en schema core que sostienen la clasificacion de
mercaderias para reporting (MENUDENCIA, DECOMISO, MEDIA_RES, OTRO) y
las reglas declarativas usadas por el ETL para asignar categoria
automaticamente.
"""
from alembic import op
import sqlalchemy as sa


revision = "0003_mercaderia_categorias"
down_revision = "0002_etl_schemas"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "mercaderia_categoria",
        sa.Column("id", sa.SmallInteger(), nullable=False),
        sa.Column("codigo", sa.Text(), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=False),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("codigo", name="uq_mercaderia_categoria_codigo"),
        schema="core",
    )
    # SmallInteger PK con autoincrement explicito (smallserial)
    op.execute(sa.text("CREATE SEQUENCE IF NOT EXISTS core.mercaderia_categoria_id_seq AS smallint"))
    op.execute(
        sa.text(
            "ALTER TABLE core.mercaderia_categoria "
            "ALTER COLUMN id SET DEFAULT nextval('core.mercaderia_categoria_id_seq')"
        )
    )
    op.execute(
        sa.text(
            "ALTER SEQUENCE core.mercaderia_categoria_id_seq "
            "OWNED BY core.mercaderia_categoria.id"
        )
    )

    op.bulk_insert(
        sa.table(
            "mercaderia_categoria",
            sa.column("codigo", sa.Text()),
            sa.column("descripcion", sa.Text()),
            schema="core",
        ),
        [
            {"codigo": "MENUDENCIA", "descripcion": "Menudencias"},
            {"codigo": "DECOMISO", "descripcion": "Decomisos"},
            {"codigo": "MEDIA_RES", "descripcion": "Media res"},
            {"codigo": "OTRO", "descripcion": "Sin clasificar"},
        ],
    )

    op.create_table(
        "mercaderia_clasificacion_regla",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tipo_match", sa.Text(), nullable=False),
        sa.Column("patron", sa.Text(), nullable=False),
        sa.Column("categoria_id", sa.SmallInteger(), nullable=False),
        sa.Column("prioridad", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("activa", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "creado_en",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "tipo_match IN ('PREFIJO_CODIGO','CODIGO_EXACTO','REGEX_DESCRIPCION')",
            name="ck_merc_regla_tipo_match",
        ),
        sa.ForeignKeyConstraint(
            ["categoria_id"],
            ["core.mercaderia_categoria.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        schema="core",
    )
    op.create_index(
        "ix_merc_regla_prioridad",
        "mercaderia_clasificacion_regla",
        ["prioridad"],
        schema="core",
        postgresql_where=sa.text("activa"),
    )

    # Seed inicial de reglas (hipotesis a validar con negocio).
    # Se resuelve categoria_id por subquery sobre el catalogo recien insertado.
    op.execute(
        sa.text(
            """
            INSERT INTO core.mercaderia_clasificacion_regla
                (tipo_match, patron, categoria_id, prioridad)
            SELECT v.tipo_match, v.patron, c.id, v.prioridad
            FROM (VALUES
                ('REGEX_DESCRIPCION', '^MEDIA RES',  'MEDIA_RES',  10),
                ('PREFIJO_CODIGO',    'D',           'DECOMISO',   20),
                ('PREFIJO_CODIGO',    'IBMCF',       'MENUDENCIA', 30),
                ('PREFIJO_CODIGO',    'IBMCH',       'MENUDENCIA', 30),
                ('PREFIJO_CODIGO',    'IBMCP',       'MENUDENCIA', 30),
                ('PREFIJO_CODIGO',    'IBMCC',       'MENUDENCIA', 30)
            ) AS v(tipo_match, patron, categoria_codigo, prioridad)
            JOIN core.mercaderia_categoria c
              ON c.codigo = v.categoria_codigo
            """
        )
    )


def downgrade():
    op.drop_index(
        "ix_merc_regla_prioridad",
        table_name="mercaderia_clasificacion_regla",
        schema="core",
    )
    op.drop_table("mercaderia_clasificacion_regla", schema="core")

    op.execute(sa.text("DROP TABLE IF EXISTS core.mercaderia_categoria"))
    op.execute(sa.text("DROP SEQUENCE IF EXISTS core.mercaderia_categoria_id_seq"))
