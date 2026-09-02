"""Step ETL: faena y movimientos."""
from __future__ import annotations

import logging
import time
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.extensions import db
from app.models import Faena, StgTwinsFaena, StgTwinsMovimiento
from app.services.etl.source import TwinsSource
from app.services.etl.steps.base import StepResult

logger = logging.getLogger(__name__)

# Topes para no inundar etl.ejecucion_error / el log ante un dia patologico.
_MAX_ERRORES_DUPLICADOS = 20
_MAX_MUESTRA_RELOCALIZACION = 10


def _clave_material(fila: dict[str, Any]) -> tuple[Any, ...]:
    """Datos que, si difieren entre dos filas de la misma media, la hacen ambigua."""
    return (
        fila["fecha_faena"],
        fila["twins_lista_detalle_id"],
        fila["cabezas"],
        fila["activa"],
    )


class FaenaStep:
    nombre = "faena"
    tabla_destino = "core.faena"

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
                "DELETE FROM staging.twins_faena WHERE etl_ejecucion_id = :eid"
            ),
            {"eid": ejecucion_id},
        )
        db.session.execute(
            text(
                "DELETE FROM staging.twins_movimientos WHERE etl_ejecucion_id = :eid"
            ),
            {"eid": ejecucion_id},
        )

        # 1) Movimientos a staging (informativos para auditoria/reproduccion)
        movimientos_filas: list[dict[str, Any]] = []
        for row in source.fetch_movimientos(desde, hasta):
            mov = row.get("twins_movimiento_id")
            ident = row.get("twins_identificador_id")
            source_pk = (
                f"{mov}-{ident}" if mov is not None and ident is not None
                else f"row-{len(movimientos_filas)}"
            )
            movimientos_filas.append(
                {
                    "etl_ejecucion_id": ejecucion_id,
                    "source_pk": source_pk,
                    "twins_movimiento_id": mov,
                    "twins_identificador_id": ident,
                    "fecha_movimiento": row.get("fecha_movimiento"),
                    "fecha_creacion": row.get("fecha_creacion"),
                    "es_entrada": row.get("es_entrada"),
                    "payload": row,
                }
            )
        if movimientos_filas:
            db.session.execute(StgTwinsMovimiento.__table__.insert(), movimientos_filas)

        # 2) Faena a staging + core
        filas: list[dict[str, Any]] = []
        for row in source.fetch_faena(desde, hasta):
            fid = row.get("twins_faena_id")
            source_pk = str(fid) if fid is not None else f"row-{len(filas)}"
            filas.append(
                {
                    "etl_ejecucion_id": ejecucion_id,
                    "source_pk": source_pk,
                    "twins_faena_id": fid,
                    "twins_identificador_id": row.get("twins_identificador_id"),
                    "twins_lista_detalle_id": row.get("twins_lista_detalle_id"),
                    "twins_operario_id": row.get("twins_operario_id"),
                    "fecha_faena": row.get("fecha_faena"),
                    "cabezas": row.get("cabezas"),
                    "kg_estimados": row.get("kg_estimados"),
                    "activa": row.get("activa"),
                    "payload": row,
                }
            )
        result.filas_leidas = len(filas)

        if filas:
            db.session.execute(StgTwinsFaena.__table__.insert(), filas)

        # Resolver subtropa_id por twins_lista_detalle_id y operario_id por twins_id
        lista_detalles = {
            f["twins_lista_detalle_id"] for f in filas
            if f["twins_lista_detalle_id"] is not None
        }
        subtropa_por_ld: dict[int, int] = {}
        if lista_detalles:
            rows = db.session.execute(
                text(
                    "SELECT id, twins_lista_detalle_id FROM core.subtropa "
                    "WHERE twins_lista_detalle_id = ANY(:ids)"
                ),
                {"ids": list(lista_detalles)},
            ).all()
            subtropa_por_ld = {int(r[1]): int(r[0]) for r in rows}

        op_ids = {f["twins_operario_id"] for f in filas if f["twins_operario_id"] is not None}
        operario_por_twins: dict[int, int] = {}
        if op_ids:
            rows = db.session.execute(
                text("SELECT id, twins_id FROM core.operario WHERE twins_id = ANY(:ids)"),
                {"ids": list(op_ids)},
            ).all()
            operario_por_twins = {int(r[1]): int(r[0]) for r in rows}

        # Dedup por twins_faena_id (= Identificador_Id). El join Faena x DatosFrigo
        # puede devolver la misma media mas de una vez, asi que duplicar no es
        # sintoma de nada por si solo: se retiene la primera fila y solo importa
        # si la repetida trae datos distintos. Antes este descarte era mudo (ni
        # contador ni log), por eso una corrida con perdida terminaba en 'ok'.
        retenidos: dict[int, dict[str, Any]] = {}
        duplicados_benignos = 0
        conflictos: list[tuple[str | None, str]] = []

        for fila in filas:
            fid = fila["twins_faena_id"]
            ident = fila["twins_identificador_id"]
            fecha = fila["fecha_faena"]
            if fid is None or ident is None or fecha is None:
                result.filas_descartadas += 1
                result.errores.append((fila["source_pk"], "campos minimos vacios"))
                continue

            fid = int(fid)
            previo = retenidos.get(fid)
            if previo is None:
                retenidos[fid] = fila
                continue

            result.filas_descartadas += 1
            if _clave_material(previo) == _clave_material(fila):
                duplicados_benignos += 1
            else:
                conflictos.append(
                    (
                        fila["source_pk"],
                        "duplicado conflictivo: retenido "
                        f"{_clave_material(previo)} vs descartado {_clave_material(fila)}",
                    )
                )

        # Duplicados benignos: contador + una linea resumida. Nunca van a
        # result.errores, porque eso degradaria a 'partial' una corrida sana.
        if duplicados_benignos:
            logger.info(
                "[ETL-faena] %d duplicados benignos descartados sobre %d filas leidas"
                " (misma media, mismos datos); no afectan el estado de la corrida.",
                duplicados_benignos, len(filas),
            )

        # Duplicados conflictivos: la fila que se retiene es arbitraria (gana la
        # primera del cursor), asi que la corrida SI debe quedar 'partial'.
        if conflictos:
            logger.warning(
                "[ETL-faena] %d duplicados CONFLICTIVOS: la misma media llega con"
                " fecha_faena o datos distintos y se retiene una arbitrariamente.",
                len(conflictos),
            )
            result.errores.extend(conflictos[:_MAX_ERRORES_DUPLICADOS])
            if len(conflictos) > _MAX_ERRORES_DUPLICADOS:
                result.errores.append(
                    (
                        None,
                        f"duplicados conflictivos: {len(conflictos)} en total,"
                        f" se registran los primeros {_MAX_ERRORES_DUPLICADOS}",
                    )
                )

        # Deteccion de relocalizacion: medias que ya existen en core con OTRA
        # fecha_faena. El upsert las va a mover (unique global sobre
        # twins_faena_id + EXCLUDED.fecha_faena). Es legitimo si la fuente
        # corrigio la fecha, por eso solo se loguea y no se marca error. Sirve
        # para que un caso como el del 2026-07-24 (46 medias movidas al 25/07
        # por el viejo fallback de mv.dFecha) quede visible en el log.
        if retenidos:
            existentes = db.session.execute(
                text(
                    "SELECT twins_faena_id, fecha_faena FROM core.faena "
                    "WHERE twins_faena_id = ANY(:ids)"
                ),
                {"ids": list(retenidos.keys())},
            ).all()
            reubicadas = [
                (int(r[0]), r[1], retenidos[int(r[0])]["fecha_faena"])
                for r in existentes
                if r[1] != retenidos[int(r[0])]["fecha_faena"]
            ]
            if reubicadas:
                muestra = ", ".join(
                    f"{fid}:{antes}->{despues}"
                    for fid, antes, despues in reubicadas[:_MAX_MUESTRA_RELOCALIZACION]
                )
                logger.warning(
                    "[ETL-faena] %d medias cambian de fecha_faena en este upsert."
                    " Es esperable si la fuente corrigio la fecha; si se repite,"
                    " revisar el origen. Muestra: %s",
                    len(reubicadas), muestra,
                )

        ahora = datetime.now(timezone.utc)
        for fila in retenidos.values():
            fid = int(fila["twins_faena_id"])
            ident = fila["twins_identificador_id"]
            fecha = fila["fecha_faena"]

            ld = fila["twins_lista_detalle_id"]
            subtropa_id = subtropa_por_ld.get(int(ld)) if ld is not None else None
            top = fila["twins_operario_id"]
            operario_id = operario_por_twins.get(int(top)) if top is not None else None

            stmt = (
                pg_insert(Faena.__table__)
                .values(
                    twins_faena_id=int(fid),
                    twins_identificador_id=int(ident),
                    fecha_faena=fecha,
                    subtropa_id=subtropa_id,
                    operario_id=operario_id,
                    cabezas=fila["cabezas"],
                    kg_estimados=fila["kg_estimados"],
                    vigente=bool(fila["activa"]) if fila["activa"] is not None else True,
                    etl_ejecucion_id_ult=ejecucion_id,
                    actualizado_en=ahora,
                )
                .on_conflict_do_update(
                    index_elements=["twins_faena_id"],
                    set_={
                        "twins_identificador_id": text("EXCLUDED.twins_identificador_id"),
                        "fecha_faena": text("EXCLUDED.fecha_faena"),
                        "subtropa_id": text("EXCLUDED.subtropa_id"),
                        "operario_id": text("EXCLUDED.operario_id"),
                        "cabezas": text("EXCLUDED.cabezas"),
                        "kg_estimados": text("EXCLUDED.kg_estimados"),
                        "vigente": text("EXCLUDED.vigente"),
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
