"""Step ETL: catalogo de operarios."""
from __future__ import annotations

import time
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.extensions import db
from app.models import Operario, StgTwinsOperario
from app.services.etl.source import TwinsSource
from app.services.etl.steps.base import StepResult


class OperariosStep:
    nombre = "operarios"
    tabla_destino = "core.operario"

    def run(
        self,
        *,
        ejecucion_id: int,
        source: TwinsSource,
        desde: date,
        hasta: date,
    ) -> StepResult:
        del desde, hasta
        result = StepResult(tabla_destino=self.tabla_destino)
        inicio = time.perf_counter()

        db.session.execute(
            text(
                "DELETE FROM staging.twins_operarios "
                "WHERE etl_ejecucion_id = :eid"
            ),
            {"eid": ejecucion_id},
        )

        filas: list[dict[str, Any]] = []
        for row in source.fetch_operarios():
            twins_id = row.get("twins_id")
            source_pk = str(twins_id) if twins_id is not None else f"row-{len(filas)}"
            filas.append(
                {
                    "etl_ejecucion_id": ejecucion_id,
                    "source_pk": source_pk,
                    "twins_id": twins_id,
                    "codigo": (row.get("codigo") or "").strip() or None,
                    "descripcion": (row.get("descripcion") or "").strip() or None,
                    "payload": row,
                }
            )
        result.filas_leidas = len(filas)

        if filas:
            db.session.execute(StgTwinsOperario.__table__.insert(), filas)

        ahora = datetime.now(timezone.utc)
        for fila in filas:
            twins_id = fila["twins_id"]
            if twins_id is None:
                result.filas_descartadas += 1
                result.errores.append((fila["source_pk"], "twins_id vacio"))
                continue
            stmt = (
                pg_insert(Operario.__table__)
                .values(
                    twins_id=twins_id,
                    codigo=fila["codigo"],
                    descripcion=fila["descripcion"],
                    vigente=True,
                    etl_ejecucion_id_ult=ejecucion_id,
                    actualizado_en=ahora,
                )
                .on_conflict_do_update(
                    index_elements=["twins_id"],
                    set_={
                        "codigo": text("EXCLUDED.codigo"),
                        "descripcion": text("EXCLUDED.descripcion"),
                        "vigente": True,
                        "etl_ejecucion_id_ult": ejecucion_id,
                        "actualizado_en": ahora,
                    },
                )
            )
            db.session.execute(stmt)
            result.filas_insertadas += 1

        db.session.commit()
        result.duracion_ms = int((time.perf_counter() - inicio) * 1000)
        return result
