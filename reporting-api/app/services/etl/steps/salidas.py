"""Step ETL: salidas (lineas de emision)."""
from __future__ import annotations

import time
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.extensions import db
from app.models import Salida, StgTwinsSalida
from app.services.etl.source import TwinsSource
from app.services.etl.steps.base import StepResult


def _to_decimal(value: Any) -> Decimal:
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


class SalidasStep:
    nombre = "salidas"
    tabla_destino = "core.salida"

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
                "DELETE FROM staging.twins_salidas WHERE etl_ejecucion_id = :eid"
            ),
            {"eid": ejecucion_id},
        )

        filas: list[dict[str, Any]] = []
        for row in source.fetch_salidas(desde, hasta):
            mov = row.get("twins_movimiento_id")
            ident = row.get("twins_identificador_id")
            merc = row.get("twins_mercaderia_id")
            source_pk = f"{mov}-{ident}-{merc}" if (mov and ident) else f"row-{len(filas)}"
            filas.append(
                {
                    "etl_ejecucion_id": ejecucion_id,
                    "source_pk": source_pk,
                    "twins_movimiento_id": mov,
                    "twins_identificador_id": ident,
                    "twins_mercaderia_id": merc,
                    "cantidad": row.get("cantidad"),
                    "peso_gr": row.get("peso_gr"),
                    "activa": row.get("activa"),
                    "eliminada": row.get("eliminada"),
                    "dedup_key": (row.get("dedup_key") or "").strip() or None,
                    "fecha_emision": row.get("fecha_emision"),
                    "fecha_creacion": row.get("fecha_creacion"),
                    "twins_operario_id": row.get("twins_operario_id"),
                    "payload": row,
                }
            )
        result.filas_leidas = len(filas)

        if filas:
            db.session.execute(
                StgTwinsSalida.__table__.insert(),
                [
                    {
                        "etl_ejecucion_id": f["etl_ejecucion_id"],
                        "source_pk": f["source_pk"],
                        "twins_movimiento_id": f["twins_movimiento_id"],
                        "twins_identificador_id": f["twins_identificador_id"],
                        "twins_mercaderia_id": f["twins_mercaderia_id"],
                        "cantidad": f["cantidad"],
                        "peso_gr": f["peso_gr"],
                        "activa": f["activa"],
                        "eliminada": f["eliminada"],
                        "dedup_key": f["dedup_key"],
                        "payload": f["payload"],
                    }
                    for f in filas
                ],
            )

        # Resolver mercaderia_id, faena_id, operario_id
        merc_ids_twins = {f["twins_mercaderia_id"] for f in filas if f["twins_mercaderia_id"] is not None}
        merc_por_twins: dict[int, int] = {}
        if merc_ids_twins:
            rows = db.session.execute(
                text(
                    "SELECT id, twins_id FROM core.mercaderia WHERE twins_id = ANY(:ids)"
                ),
                {"ids": list(merc_ids_twins)},
            ).all()
            merc_por_twins = {int(r[1]): int(r[0]) for r in rows}

        ident_set = {f["twins_identificador_id"] for f in filas if f["twins_identificador_id"] is not None}
        faena_por_ident: dict[int, int] = {}
        if ident_set:
            rows = db.session.execute(
                text(
                    "SELECT id, twins_identificador_id FROM core.faena "
                    "WHERE twins_identificador_id = ANY(:ids)"
                ),
                {"ids": list(ident_set)},
            ).all()
            # Si hay varias faenas para el mismo identificador, tomamos la mas reciente
            for r in rows:
                faena_por_ident.setdefault(int(r[1]), int(r[0]))

        op_ids = {f["twins_operario_id"] for f in filas if f.get("twins_operario_id") is not None}
        operario_por_twins: dict[int, int] = {}
        if op_ids:
            rows = db.session.execute(
                text("SELECT id, twins_id FROM core.operario WHERE twins_id = ANY(:ids)"),
                {"ids": list(op_ids)},
            ).all()
            operario_por_twins = {int(r[1]): int(r[0]) for r in rows}

        ahora = datetime.now(timezone.utc)
        for fila in filas:
            mov = fila["twins_movimiento_id"]
            ident = fila["twins_identificador_id"]
            merc_twins = fila["twins_mercaderia_id"]
            fecha_em = fila["fecha_emision"]
            if mov is None or ident is None or merc_twins is None or fecha_em is None:
                result.filas_descartadas += 1
                result.errores.append((fila["source_pk"], "campos minimos vacios"))
                continue

            mercaderia_id = merc_por_twins.get(int(merc_twins))
            if mercaderia_id is None:
                result.filas_descartadas += 1
                result.errores.append(
                    (fila["source_pk"], f"mercaderia twins_id={merc_twins} no encontrada")
                )
                continue

            cantidad_cajas = _to_decimal(fila["cantidad"])
            peso_kg = _to_decimal(fila["peso_gr"]) / Decimal("1000")
            activa = bool(fila["activa"]) if fila["activa"] is not None else True
            eliminada = bool(fila["eliminada"]) if fila["eliminada"] is not None else False
            vigente = activa and not eliminada

            dedup_key = fila["dedup_key"] or f"ID:{ident}"
            twins_salida_pk = f"{mov}|{ident}|{merc_twins}"
            faena_id = faena_por_ident.get(int(ident))
            top = fila.get("twins_operario_id")
            operario_id = operario_por_twins.get(int(top)) if top is not None else None

            stmt = (
                pg_insert(Salida.__table__)
                .values(
                    twins_movimiento_id=int(mov),
                    twins_identificador_id=int(ident),
                    twins_salida_pk=twins_salida_pk,
                    fecha_emision=fecha_em,
                    fecha_creacion=fila["fecha_creacion"],
                    mercaderia_id=mercaderia_id,
                    cantidad_cajas=cantidad_cajas,
                    peso_kg=peso_kg,
                    faena_id=faena_id,
                    operario_id=operario_id,
                    dedup_key=dedup_key,
                    vigente=vigente,
                    etl_ejecucion_id_ult=ejecucion_id,
                    actualizado_en=ahora,
                )
                .on_conflict_do_update(
                    constraint="uq_salida_origen",
                    set_={
                        "fecha_emision": text("EXCLUDED.fecha_emision"),
                        "fecha_creacion": text("EXCLUDED.fecha_creacion"),
                        "mercaderia_id": text("EXCLUDED.mercaderia_id"),
                        "cantidad_cajas": text("EXCLUDED.cantidad_cajas"),
                        "peso_kg": text("EXCLUDED.peso_kg"),
                        "faena_id": text("EXCLUDED.faena_id"),
                        "operario_id": text("EXCLUDED.operario_id"),
                        "dedup_key": text("EXCLUDED.dedup_key"),
                        "vigente": text("EXCLUDED.vigente"),
                        "etl_ejecucion_id_ult": ejecucion_id,
                        "actualizado_en": ahora,
                    },
                )
            )
            try:
                db.session.execute(stmt)
                result.filas_insertadas += 1
            except Exception as exc:
                # Tipicamente choque con uq_salida_dedup (otra fila con mismo
                # fecha_emision + dedup_key). Lo anotamos y seguimos.
                db.session.rollback()
                result.filas_descartadas += 1
                result.errores.append((fila["source_pk"], f"upsert_failed: {exc!r}"))

        db.session.commit()

        # Relinker: salidas previas con faena_id NULL que ahora pueden resolverse
        relinked = db.session.execute(
            text(
                """
                UPDATE core.salida s
                SET faena_id = f.id,
                    actualizado_en = now()
                FROM core.faena f
                WHERE s.faena_id IS NULL
                  AND s.twins_identificador_id = f.twins_identificador_id
                  AND s.fecha_emision BETWEEN :desde AND :hasta
                """
            ),
            {"desde": desde, "hasta": hasta},
        )
        result.filas_actualizadas += relinked.rowcount or 0
        db.session.commit()

        result.duracion_ms = int((time.perf_counter() - inicio) * 1000)
        return result
