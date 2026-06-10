"""Clasifica la familia FBMC* como MENUDENCIA.

Las menudencias en Twins usan el patron `?BMC[CFHP]` (la 1ra letra distingue
fresco `I` vs elaborado/congelado `F`; las posiciones 2-4 = `BMC` y la 5ta
letra ∈ {C,F,H,P} es el marcador de menudencia). El seed original (0003) solo
cargo las variantes `IBMC*`. Faltaban las `FBMC*` (p.ej. FBMCFR110 CHINCHULIN),
que quedaban en `OTRO` y desaparecian de la DDJJ. Verificado contra el legacy:
17-09 incluye FBMCFR110 (11 cajas / 87.21 kg) y sin esta regla el total quedaba
corto exactamente en ese producto.

Las reglas se aplican en el ETL (paso mercaderias) sin pisar clasificaciones
MANUAL; las AUTO se reclasifican en la proxima corrida.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "0012_menudencia_fbmc"
down_revision = "0011_proceso_productivo"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        sa.text(
            """
            INSERT INTO core.mercaderia_clasificacion_regla
                (tipo_match, patron, categoria_id, prioridad)
            SELECT 'PREFIJO_CODIGO', v.patron, c.id, 30
            FROM (VALUES ('FBMCC'),('FBMCF'),('FBMCH'),('FBMCP')) AS v(patron)
            JOIN core.mercaderia_categoria c ON c.codigo = 'MENUDENCIA'
            WHERE NOT EXISTS (
                SELECT 1 FROM core.mercaderia_clasificacion_regla r
                 WHERE r.tipo_match = 'PREFIJO_CODIGO' AND r.patron = v.patron
            )
            """
        )
    )


def downgrade():
    op.execute(
        sa.text(
            "DELETE FROM core.mercaderia_clasificacion_regla "
            "WHERE tipo_match = 'PREFIJO_CODIGO' "
            "AND patron IN ('FBMCC','FBMCF','FBMCH','FBMCP')"
        )
    )
