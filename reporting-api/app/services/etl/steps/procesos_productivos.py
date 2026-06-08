"""Step ETL: procesos productivos (configuracion.Procesos en Twins)."""
from __future__ import annotations

import logging
import time
from datetime import date, datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.extensions import db
from app.models import ProcesoProductivo
from app.services.etl.source import TwinsSource
from app.services.etl.steps.base import StepResult


class ProcesosProductivosStep:
    """Carga el catalogo de procesos productivos desde configuracion.Procesos en Twins."""

    nombre = "procesos_productivos"
    tabla_destino = "core.proceso_productivo"

    def run(
        self,
        *,
        ejecucion_id: int,
        source: TwinsSource,
        desde: date,
        hasta: date,
    ) -> StepResult:
        del desde, hasta  # El catalogo es global, no depende de ventana temporal.
        result = StepResult(tabla_destino=self.tabla_destino)
        inicio = time.perf_counter()

        filas: list[dict[str, Any]] = []
        for row in source.fetch_procesos():
            twins_id = row.get("twins_id")
            if twins_id is None:
                result.filas_descartadas += 1
                continue
            filas.append(
                {
                    "twins_id": int(twins_id),
                    "codigo": (row.get("codigo") or "").strip(),
                    "descripcion": (row.get("descripcion") or "").strip(),
                }
            )

        result.filas_leidas = len(filas)

        if not filas:
            result.duracion_seg = time.perf_counter() - inicio
            return result

        ahora = datetime.now(timezone.utc)
        for fila in filas:
            stmt = (
                pg_insert(ProcesoProductivo.__table__)
                .values(
                    twins_id=fila["twins_id"],
                    codigo=fila["codigo"],
                    descripcion=fila["descripcion"],
                    vigente=True,
                    etl_ejecucion_id_ult=ejecucion_id,
                    actualizado_en=ahora,
                )
                .on_conflict_do_update(
                    index_elements=["twins_id"],
                    set_={
                        "codigo": fila["codigo"],
                        "descripcion": fila["descripcion"],
                        "vigente": True,
                        "etl_ejecucion_id_ult": ejecucion_id,
                        "actualizado_en": ahora,
                    },
                )
            )
            db.session.execute(stmt)
            result.filas_insertadas += 1

        db.session.flush()
        result.duracion_seg = time.perf_counter() - inicio
        logger.info(
            "[ETL] ProcesosProductivosStep: %d procesos upserted en %.2fs",
            result.filas_insertadas,
            result.duracion_seg,
        )
        return result
