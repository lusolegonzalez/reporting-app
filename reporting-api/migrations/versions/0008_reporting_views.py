"""vistas materializadas para DDJJ Menudencias

Revision ID: 0008_reporting_views
Revises: 0007_salida
Create Date: 2026-04-29 00:30:00.000000

Crea las vistas materializadas en el schema reporting que alimentan
el reporte DDJJ Menudencias. Cada MV define un UNIQUE INDEX para
permitir REFRESH MATERIALIZED VIEW CONCURRENTLY.
"""
from alembic import op
import sqlalchemy as sa


revision = "0008_reporting_views"
down_revision = "0007_salida"
branch_labels = None
depends_on = None


def upgrade():
    # 1. Produccion de menudencias y decomisos por dia y codigo
    op.execute(
        sa.text(
            """
            CREATE MATERIALIZED VIEW reporting.mv_ddjj_menudencias_diaria AS
            SELECT
                s.fecha_emision                              AS fecha_faena,
                m.codigo                                     AS mercaderia_codigo,
                m.descripcion                                AS mercaderia_descripcion,
                cat.codigo                                   AS categoria,
                SUM(s.cantidad_cajas)::NUMERIC(18,3)         AS cajas,
                SUM(s.peso_kg)::NUMERIC(18,3)                AS kg_neto
            FROM core.salida s
            JOIN core.mercaderia m
              ON m.id = s.mercaderia_id
            JOIN core.mercaderia_categoria cat
              ON cat.id = m.categoria_id
            WHERE s.vigente = TRUE
              AND cat.codigo IN ('MENUDENCIA','DECOMISO')
            GROUP BY s.fecha_emision, m.codigo, m.descripcion, cat.codigo
            WITH NO DATA;
            """
        )
    )
    op.execute(
        sa.text(
            "CREATE UNIQUE INDEX ux_mv_ddjj_menud_pk "
            "ON reporting.mv_ddjj_menudencias_diaria "
            "(fecha_faena, mercaderia_codigo, categoria);"
        )
    )
    op.execute(
        sa.text(
            "CREATE INDEX ix_mv_ddjj_menud_fecha "
            "ON reporting.mv_ddjj_menudencias_diaria (fecha_faena);"
        )
    )

    # 2. Faena diaria (KPI cabezas)
    op.execute(
        sa.text(
            """
            CREATE MATERIALIZED VIEW reporting.mv_faena_diaria AS
            SELECT
                f.fecha_faena,
                SUM(COALESCE(f.cabezas,0))::INTEGER          AS cabezas,
                SUM(COALESCE(f.kg_estimados,0))::NUMERIC(18,3) AS kg_estimados,
                COUNT(DISTINCT f.id)                         AS faenas
            FROM core.faena f
            WHERE f.vigente = TRUE
            GROUP BY f.fecha_faena
            WITH NO DATA;
            """
        )
    )
    op.execute(
        sa.text(
            "CREATE UNIQUE INDEX ux_mv_faena_diaria "
            "ON reporting.mv_faena_diaria (fecha_faena);"
        )
    )

    # 3. Tropas por dia de faena (se muestra solo cuando rango = 1 dia)
    op.execute(
        sa.text(
            """
            CREATE MATERIALIZED VIEW reporting.mv_tropas_por_faena_diaria AS
            SELECT
                f.fecha_faena,
                t.numero_tropa,
                SUM(COALESCE(f.cabezas,0))::INTEGER AS cabezas
            FROM core.faena f
            JOIN core.subtropa st ON st.id = f.subtropa_id
            JOIN core.tropa    t  ON t.id  = st.tropa_id
            WHERE f.vigente = TRUE
            GROUP BY f.fecha_faena, t.numero_tropa
            WITH NO DATA;
            """
        )
    )
    op.execute(
        sa.text(
            "CREATE UNIQUE INDEX ux_mv_tropas_pk "
            "ON reporting.mv_tropas_por_faena_diaria (fecha_faena, numero_tropa);"
        )
    )
    op.execute(
        sa.text(
            "CREATE INDEX ix_mv_tropas_fecha "
            "ON reporting.mv_tropas_por_faena_diaria (fecha_faena);"
        )
    )

    # 4. Consistencia DDJJ (menudencias vs cabezas faenadas)
    op.execute(
        sa.text(
            """
            CREATE MATERIALIZED VIEW reporting.mv_consistencia_ddjj AS
            WITH menud AS (
                SELECT
                    fecha_faena,
                    SUM(cajas)   FILTER (WHERE categoria = 'MENUDENCIA') AS cajas_menudencias,
                    SUM(kg_neto) FILTER (WHERE categoria = 'MENUDENCIA') AS kg_menudencias
                FROM reporting.mv_ddjj_menudencias_diaria
                GROUP BY fecha_faena
            )
            SELECT
                COALESCE(f.fecha_faena, m.fecha_faena)        AS fecha_faena,
                COALESCE(f.cabezas, 0)                        AS cabezas_faenadas,
                COALESCE(m.cajas_menudencias, 0)              AS cajas_menudencias,
                COALESCE(m.kg_menudencias, 0)                 AS kg_menudencias,
                (COALESCE(m.cajas_menudencias, 0) > COALESCE(f.cabezas, 0))
                                                              AS alerta_excede_cabezas
            FROM reporting.mv_faena_diaria f
            FULL OUTER JOIN menud m
              ON m.fecha_faena = f.fecha_faena
            WITH NO DATA;
            """
        )
    )
    op.execute(
        sa.text(
            "CREATE UNIQUE INDEX ux_mv_consistencia "
            "ON reporting.mv_consistencia_ddjj (fecha_faena);"
        )
    )


def downgrade():
    op.execute(sa.text("DROP MATERIALIZED VIEW IF EXISTS reporting.mv_consistencia_ddjj"))
    op.execute(sa.text("DROP MATERIALIZED VIEW IF EXISTS reporting.mv_tropas_por_faena_diaria"))
    op.execute(sa.text("DROP MATERIALIZED VIEW IF EXISTS reporting.mv_faena_diaria"))
    op.execute(sa.text("DROP MATERIALIZED VIEW IF EXISTS reporting.mv_ddjj_menudencias_diaria"))
