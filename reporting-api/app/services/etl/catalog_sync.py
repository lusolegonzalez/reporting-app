"""Sincronizacion liviana del catalogo de procesos productivos.

Se activa unicamente cuando core.proceso_productivo esta vacia al momento
de servir el endpoint de catalogo/excluir_procesos. No ejecuta el ETL
completo, no crea registros EjecucionImportacion y no carga otras tablas.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.extensions import db
from app.models import ProcesoProductivo

logger = logging.getLogger(__name__)


def _build_default_source():
    from flask import current_app
    from app.services.etl.sources import InMemoryTwinsSource, SqlServerTwinsSource

    cfg = current_app.config
    if (cfg.get("MSSQL_SERVER") or "").strip():
        return SqlServerTwinsSource.from_flask_config(cfg)
    return InMemoryTwinsSource()


def sync_procesos_if_empty() -> int:
    """Puebla core.proceso_productivo si esta vacia. Devuelve cantidad de filas insertadas.

    No crea EjecucionImportacion ni ejecuta otros steps ETL.
    Si la tabla ya tiene datos no hace nada.
    """
    if db.session.query(ProcesoProductivo).count() > 0:
        return 0

    logger.info(
        "[catalogo] core.proceso_productivo vacia; sincronizando procesos desde source."
    )

    source = _build_default_source()
    ahora = datetime.now(timezone.utc)
    insertados = 0

    for row in source.fetch_procesos():
        twins_id = row.get("twins_id")
        if twins_id is None:
            continue
        stmt = (
            pg_insert(ProcesoProductivo.__table__)
            .values(
                twins_id=int(twins_id),
                codigo=(row.get("codigo") or "").strip(),
                descripcion=(row.get("descripcion") or "").strip(),
                vigente=True,
                etl_ejecucion_id_ult=None,
                actualizado_en=ahora,
            )
            .on_conflict_do_nothing(index_elements=["twins_id"])
        )
        db.session.execute(stmt)
        insertados += 1

    db.session.commit()
    logger.info("[catalogo] Procesos sincronizados: %d filas.", insertados)
    return insertados
