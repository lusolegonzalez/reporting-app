"""Orquestador del proceso ETL.

Crea una EjecucionImportacion, toma un advisory lock para evitar
concurrencia, ejecuta los steps registrados, persiste contadores y
errores por tabla destino, y al final refresca las vistas
materializadas de reporting.
"""
from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Callable

from flask import Flask, current_app
from sqlalchemy import text

from app.extensions import db
from app.models import EjecucionError, EjecucionImportacion, EjecucionTabla
from app.services.etl.refresher import refresh_reporting_views
from app.services.etl.source import TwinsSource
from app.services.etl.steps.base import EtlStep, StepResult
from app.services.etl.steps.faena import FaenaStep
from app.services.etl.steps.mercaderias import MercaderiasStep
from app.services.etl.steps.operarios import OperariosStep
from app.services.etl.steps.salidas import SalidasStep
from app.services.etl.steps.tropas import TropasStep

logger = logging.getLogger(__name__)

# Clave arbitraria para pg_try_advisory_lock; cualquier int de 64 bits sirve.
_ETL_ADVISORY_LOCK_KEY = 7263514091


@dataclass
class EjecucionResumen:
    ejecucion_id: int
    estado: str
    pasos: list[StepResult]


class EtlAlreadyRunning(RuntimeError):
    """Otra corrida ETL ya esta en curso."""


def default_steps() -> list[EtlStep]:
    """Steps que componen una corrida estandar (orden importa)."""
    return [
        MercaderiasStep(),
        OperariosStep(),
        TropasStep(),
        FaenaStep(),
        SalidasStep(),
    ]


def run_etl(
    *,
    source: TwinsSource,
    desde: date,
    hasta: date,
    origen: str = "TwinsDbQuatro045",
    created_by_user_id: int | None = None,
    steps: list[EtlStep] | None = None,
    refrescar_reporting: bool = True,
    ejecucion_id: int | None = None,
) -> EjecucionResumen:
    if hasta < desde:
        raise ValueError("hasta debe ser >= desde")

    pasos = steps if steps is not None else default_steps()

    if ejecucion_id is not None:
        ejecucion = db.session.get(EjecucionImportacion, ejecucion_id)
        if ejecucion is None:
            raise ValueError(f"EjecucionImportacion id={ejecucion_id} no existe")
        ejecucion.estado = "running"
        db.session.commit()
    else:
        ejecucion = EjecucionImportacion(
            origen=origen,
            fecha_desde=desde,
            fecha_hasta=hasta,
            estado="running",
            created_by_user_id=created_by_user_id,
        )
        db.session.add(ejecucion)
        db.session.commit()
    ejecucion_id = int(ejecucion.id)

    lock_acquired = bool(
        db.session.execute(
            text("SELECT pg_try_advisory_lock(:k)"),
            {"k": _ETL_ADVISORY_LOCK_KEY},
        ).scalar()
    )
    if not lock_acquired:
        ejecucion.estado = "error"
        ejecucion.observaciones = "Otra corrida ETL ya esta en curso."
        db.session.commit()
        raise EtlAlreadyRunning("Otra corrida ETL ya esta en curso.")

    resultados: list[StepResult] = []
    estado_final = "ok"
    step_fatal_msg: str | None = None

    try:
        for step in pasos:
            try:
                resultado = step.run(
                    ejecucion_id=ejecucion_id,
                    source=source,
                    desde=desde,
                    hasta=hasta,
                )
            except Exception as exc:  # step fallido completo -> tratamos como error
                logger.exception("Step %s fallo", step.nombre)
                db.session.rollback()
                resultado = StepResult(tabla_destino=step.tabla_destino)
                resultado.errores.append((None, f"step_failed: {exc!r}"))
                estado_final = "error"
                if step_fatal_msg is None:
                    step_fatal_msg = f"{step.nombre}: {type(exc).__name__}: {exc}"

            db.session.add(
                EjecucionTabla(
                    ejecucion_id=ejecucion_id,
                    tabla_destino=resultado.tabla_destino,
                    filas_leidas=resultado.filas_leidas,
                    filas_insertadas=resultado.filas_insertadas,
                    filas_actualizadas=resultado.filas_actualizadas,
                    filas_descartadas=resultado.filas_descartadas,
                    duracion_ms=resultado.duracion_ms,
                )
            )
            for source_pk, mensaje in resultado.errores:
                db.session.add(
                    EjecucionError(
                        ejecucion_id=ejecucion_id,
                        tabla_destino=resultado.tabla_destino,
                        source_pk=source_pk,
                        mensaje=mensaje,
                    )
                )
            if resultado.errores and estado_final == "ok":
                estado_final = "partial"

            resultados.append(resultado)

        db.session.commit()

        if refrescar_reporting and estado_final != "error":
            try:
                refresh_reporting_views()
            except Exception as exc:
                logger.exception("Fallo el refresh de reporting")
                db.session.add(
                    EjecucionError(
                        ejecucion_id=ejecucion_id,
                        tabla_destino="reporting.*",
                        source_pk=None,
                        mensaje=f"refresh_failed: {exc!r}",
                    )
                )
                estado_final = "partial"
                db.session.commit()

    finally:
        db.session.execute(
            text("SELECT pg_advisory_unlock(:k)"),
            {"k": _ETL_ADVISORY_LOCK_KEY},
        )
        ejecucion.estado = estado_final
        if step_fatal_msg and (
            not ejecucion.observaciones
            or "Pasos ejecutados" in (ejecucion.observaciones or "")
        ):
            ejecucion.observaciones = f"step_fatal: {step_fatal_msg}"
        else:
            ejecucion.observaciones = (
                ejecucion.observaciones
                or f"Pasos ejecutados: {len(resultados)} | Finalizada {datetime.now(timezone.utc).isoformat()}"
            )
        db.session.commit()

    return EjecucionResumen(
        ejecucion_id=ejecucion_id,
        estado=estado_final,
        pasos=resultados,
    )


# ---------------------------------------------------------------------------
# Ejecucion asincronica (on-demand desde el flujo de reportes)
# ---------------------------------------------------------------------------


def queue_etl_async(
    *,
    desde: date,
    hasta: date,
    origen: str = "TwinsDbQuatro045",
    created_by_user_id: int | None = None,
    source_factory: Callable[[], TwinsSource],
    app: Flask | None = None,
) -> int:
    """Crea la EjecucionImportacion en estado 'queued' y lanza un thread daemon.

    Devuelve `ejecucion_id` inmediatamente. El thread:
        - construye la TwinsSource (con app context),
        - llama `run_etl(..., ejecucion_id=...)` reusando el registro creado.

    Si el ETL falla con excepcion no controlada, se marca la ejecucion como
    'error' con observaciones.
    """
    if hasta < desde:
        raise ValueError("hasta debe ser >= desde")

    flask_app = app if app is not None else current_app._get_current_object()  # type: ignore[attr-defined]

    ejecucion = EjecucionImportacion(
        origen=origen,
        fecha_desde=desde,
        fecha_hasta=hasta,
        estado="queued",
        created_by_user_id=created_by_user_id,
        observaciones="Encolada por flujo de reporte (auto).",
    )
    db.session.add(ejecucion)
    db.session.commit()
    ejecucion_id = int(ejecucion.id)
    logger.info(
        "[ETL-async] queued ejecucion_id=%s origen=%s desde=%s hasta=%s user_id=%s",
        ejecucion_id, origen, desde, hasta, created_by_user_id,
    )

    def _worker(app_ref: Flask, ejec_id: int, d_desde: date, d_hasta: date, d_origen: str) -> None:
        with app_ref.app_context():
            try:
                logger.info(
                    "[ETL-async] start ejecucion_id=%s origen=%s desde=%s hasta=%s",
                    ejec_id, d_origen, d_desde, d_hasta,
                )
                source = source_factory()
                resumen = run_etl(
                    source=source,
                    desde=d_desde,
                    hasta=d_hasta,
                    origen=d_origen,
                    ejecucion_id=ejec_id,
                )
                logger.info(
                    "[ETL-async] done ejecucion_id=%s estado=%s pasos=%d",
                    ejec_id, resumen.estado, len(resumen.pasos),
                )
            except Exception as exc:  # noqa: BLE001
                app_ref.logger.exception(
                    "[ETL-async] FAILED ejecucion_id=%s origen=%s desde=%s hasta=%s",
                    ejec_id, d_origen, d_desde, d_hasta,
                )
                try:
                    db.session.rollback()
                    ej = db.session.get(EjecucionImportacion, ejec_id)
                    if ej is not None and ej.estado in ("queued", "running"):
                        ej.estado = "error"
                        ej.observaciones = f"async_failed: {type(exc).__name__}: {exc}"
                        db.session.commit()
                except Exception:  # noqa: BLE001
                    app_ref.logger.exception(
                        "[ETL-async] no se pudo marcar ejecucion %s como error", ejec_id,
                    )

    t = threading.Thread(
        target=_worker,
        args=(flask_app, ejecucion_id, desde, hasta, origen),
        name=f"etl-async-{ejecucion_id}",
        daemon=True,
    )
    t.start()
    return ejecucion_id

