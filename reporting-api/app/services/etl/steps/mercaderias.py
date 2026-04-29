"""Step ETL: catalogo de mercaderias.

Lee todas las mercaderias de Twins, las apila en staging.twins_mercaderias
para la ejecucion en curso, y las upserta en core.mercaderia clasificandolas
con las reglas activas (sin pisar clasificaciones manuales).
"""
from __future__ import annotations

import time
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.extensions import db
from app.models import Mercaderia, StgTwinsMercaderia
from app.services.etl.classifier import MercaderiaClassifier
from app.services.etl.source import TwinsSource
from app.services.etl.steps.base import StepResult


class MercaderiasStep:
    nombre = "mercaderias"
    tabla_destino = "core.mercaderia"

    def run(
        self,
        *,
        ejecucion_id: int,
        source: TwinsSource,
        desde: date,
        hasta: date,
    ) -> StepResult:
        del desde, hasta  # catalogo completo
        result = StepResult(tabla_destino=self.tabla_destino)
        inicio = time.perf_counter()

        # 1. Limpiar staging para esta ejecucion (idempotencia por reintento)
        db.session.execute(
            text(
                "DELETE FROM staging.twins_mercaderias "
                "WHERE etl_ejecucion_id = :eid"
            ),
            {"eid": ejecucion_id},
        )

        # 2. Cargar staging
        filas_staging: list[dict[str, Any]] = []
        for row in source.fetch_mercaderias():
            twins_id = row.get("twins_id")
            source_pk = str(twins_id) if twins_id is not None else f"row-{len(filas_staging)}"
            filas_staging.append(
                {
                    "etl_ejecucion_id": ejecucion_id,
                    "source_pk": source_pk,
                    "twins_id": twins_id,
                    "codigo": (row.get("codigo") or "").strip() or None,
                    "descripcion": (row.get("descripcion") or "").strip() or None,
                    "payload": row,
                }
            )
        result.filas_leidas = len(filas_staging)

        if filas_staging:
            db.session.execute(StgTwinsMercaderia.__table__.insert(), filas_staging)

        # 3. Upsert a core (preservando clasificacion MANUAL)
        classifier = MercaderiaClassifier.from_db()
        ahora = datetime.now(timezone.utc)

        for fila in filas_staging:
            twins_id = fila["twins_id"]
            codigo = fila["codigo"]
            descripcion = fila["descripcion"]
            if twins_id is None or not codigo or not descripcion:
                result.filas_descartadas += 1
                result.errores.append(
                    (fila["source_pk"], "twins_id/codigo/descripcion vacios")
                )
                continue

            categoria_id = classifier.clasificar(codigo, descripcion)

            stmt = (
                pg_insert(Mercaderia.__table__)
                .values(
                    twins_id=twins_id,
                    codigo=codigo,
                    descripcion=descripcion,
                    categoria_id=categoria_id,
                    origen_clasificacion="AUTO",
                    vigente=True,
                    etl_ejecucion_id_alta=ejecucion_id,
                    etl_ejecucion_id_ult=ejecucion_id,
                    creado_en=ahora,
                    actualizado_en=ahora,
                )
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=["twins_id"],
                set_={
                    "codigo": stmt.excluded.codigo,
                    "descripcion": stmt.excluded.descripcion,
                    # No pisar categoria si fue marcada como MANUAL
                    "categoria_id": text(
                        "CASE WHEN core.mercaderia.origen_clasificacion = 'MANUAL' "
                        "THEN core.mercaderia.categoria_id "
                        "ELSE EXCLUDED.categoria_id END"
                    ),
                    "vigente": True,
                    "etl_ejecucion_id_ult": stmt.excluded.etl_ejecucion_id_ult,
                    "actualizado_en": stmt.excluded.actualizado_en,
                },
            )
            res = db.session.execute(stmt)
            # xmax = 0 → INSERT; xmax != 0 → UPDATE. No es trivial detectarlo
            # con on_conflict_do_update; usamos rowcount como aproximacion:
            # rowcount=1 siempre. Distinguimos consultando si existia antes.
            # Para evitar otra query por fila, contabilizamos como "afectada"
            # y dejamos el detalle para auditoria por etl_ejecucion_id_alta.
            del res
            result.filas_insertadas += 1  # provisional: ver nota

        db.session.commit()
        result.duracion_ms = int((time.perf_counter() - inicio) * 1000)
        return result
