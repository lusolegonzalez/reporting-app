"""Step ETL: tropas y subtropas."""
from __future__ import annotations

import time
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.extensions import db
from app.models import StgTwinsTropa, Subtropa, Tropa
from app.services.etl.source import TwinsSource
from app.services.etl.steps.base import StepResult


class TropasStep:
    nombre = "tropas"
    tabla_destino = "core.tropa+subtropa"

    def run(
        self,
        *,
        ejecucion_id: int,
        source: TwinsSource,
        desde: date,
        hasta: date,
    ) -> StepResult:
        result = StepResult(tabla_destino=self.tabla_destino)
        inicio = time.perf_counter()

        db.session.execute(
            text(
                "DELETE FROM staging.twins_tropas WHERE etl_ejecucion_id = :eid"
            ),
            {"eid": ejecucion_id},
        )

        filas: list[dict[str, Any]] = []
        for row in source.fetch_tropas(desde, hasta):
            ih = row.get("twins_ingreso_hacienda_id")
            sub = row.get("twins_subtropa_id")
            source_pk = (
                f"{ih}-{sub}" if ih is not None and sub is not None else f"row-{len(filas)}"
            )
            filas.append(
                {
                    "etl_ejecucion_id": ejecucion_id,
                    "source_pk": source_pk,
                    "twins_ingreso_hacienda_id": ih,
                    "twins_subtropa_id": sub,
                    "twins_subtropa_detalle_id": row.get("twins_subtropa_detalle_id"),
                    "twins_lista_detalle_id": row.get("twins_lista_detalle_id"),
                    "numero_tropa": (row.get("numero_tropa") or "").strip() or None,
                    "numero_subtropa": (row.get("numero_subtropa") or "").strip() or None,
                    "cabezas_declaradas": row.get("cabezas_declaradas"),
                    "fecha_ingreso": row.get("fecha_ingreso"),
                    "proveedor_codigo": (row.get("proveedor_codigo") or "").strip() or None,
                    "proveedor_nombre": (row.get("proveedor_nombre") or "").strip() or None,
                    "payload": row,
                }
            )
        result.filas_leidas = len(filas)

        if filas:
            db.session.execute(StgTwinsTropa.__table__.insert(), filas)

        ahora = datetime.now(timezone.utc)

        # 1) Upsert tropas (deduplicadas por twins_ingreso_hacienda_id)
        tropas_unicas: dict[int, dict[str, Any]] = {}
        for fila in filas:
            ih = fila["twins_ingreso_hacienda_id"]
            numero_tropa = fila["numero_tropa"]
            if ih is None or not numero_tropa:
                continue
            tropas_unicas.setdefault(
                int(ih),
                {
                    "twins_ingreso_hacienda_id": int(ih),
                    "numero_tropa": numero_tropa,
                    "fecha_ingreso": fila["fecha_ingreso"],
                    "proveedor_codigo": fila["proveedor_codigo"],
                    "proveedor_nombre": fila["proveedor_nombre"],
                    "etl_ejecucion_id_ult": ejecucion_id,
                    "actualizado_en": ahora,
                },
            )

        for valores in tropas_unicas.values():
            stmt = (
                pg_insert(Tropa.__table__)
                .values(**valores)
                .on_conflict_do_update(
                    index_elements=["twins_ingreso_hacienda_id"],
                    set_={
                        "numero_tropa": text("EXCLUDED.numero_tropa"),
                        "fecha_ingreso": text("EXCLUDED.fecha_ingreso"),
                        "proveedor_codigo": text("EXCLUDED.proveedor_codigo"),
                        "proveedor_nombre": text("EXCLUDED.proveedor_nombre"),
                        "etl_ejecucion_id_ult": ejecucion_id,
                        "actualizado_en": ahora,
                    },
                )
            )
            db.session.execute(stmt)

        # Resolvemos id local por twins_ingreso_hacienda_id para enlazar subtropas
        ids_tropa: dict[int, int] = {}
        if tropas_unicas:
            rows = db.session.execute(
                text(
                    "SELECT id, twins_ingreso_hacienda_id FROM core.tropa "
                    "WHERE twins_ingreso_hacienda_id = ANY(:ids)"
                ),
                {"ids": list(tropas_unicas.keys())},
            ).all()
            ids_tropa = {int(r[1]): int(r[0]) for r in rows}

        # 2) Upsert subtropas
        subtropas_vistas: set[int] = set()
        for fila in filas:
            sub = fila["twins_subtropa_id"]
            ih = fila["twins_ingreso_hacienda_id"]
            if sub is None or ih is None:
                result.filas_descartadas += 1
                result.errores.append(
                    (fila["source_pk"], "subtropa o ingreso_hacienda vacios")
                )
                continue
            tropa_id = ids_tropa.get(int(ih))
            if tropa_id is None:
                result.filas_descartadas += 1
                result.errores.append(
                    (fila["source_pk"], "tropa no resuelta para subtropa")
                )
                continue
            if int(sub) in subtropas_vistas:
                continue
            subtropas_vistas.add(int(sub))

            stmt = (
                pg_insert(Subtropa.__table__)
                .values(
                    tropa_id=tropa_id,
                    twins_subtropa_id=int(sub),
                    twins_lista_detalle_id=fila["twins_lista_detalle_id"],
                    numero_subtropa=fila["numero_subtropa"],
                    cabezas_declaradas=fila["cabezas_declaradas"],
                    etl_ejecucion_id_ult=ejecucion_id,
                    actualizado_en=ahora,
                )
                .on_conflict_do_update(
                    index_elements=["twins_subtropa_id"],
                    set_={
                        "tropa_id": tropa_id,
                        "twins_lista_detalle_id": text("EXCLUDED.twins_lista_detalle_id"),
                        "numero_subtropa": text("EXCLUDED.numero_subtropa"),
                        "cabezas_declaradas": text("EXCLUDED.cabezas_declaradas"),
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
