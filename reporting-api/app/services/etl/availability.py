"""Disponibilidad de datos por rango en la base intermedia.

La cobertura de la base intermedia se deriva de `etl.ejecuciones_importacion`
(estados finales 'ok' y 'partial'). Es la unica metadata autoritativa que
sabe que rangos fueron efectivamente importados desde la fuente.

Funciones expuestas:
    - `find_missing_ranges(desde, hasta, origen)` -> lista de huecos (sub-rangos
      que aun no fueron cargados).
    - `find_active_execution(desde, hasta, origen)` -> ejecucion en curso/encolada
      que ya cubre el rango pedido (anti-duplicacion).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, timedelta

from app.extensions import db
from app.models import EjecucionImportacion


logger = logging.getLogger(__name__)

COBERTURA_ESTADOS = ("ok", "partial")
ACTIVOS_ESTADOS = ("queued", "running")


@dataclass(frozen=True)
class Rango:
    desde: date
    hasta: date

    def to_dict(self) -> dict[str, str]:
        return {"desde": self.desde.isoformat(), "hasta": self.hasta.isoformat()}


def _overlaps(desde: date, hasta: date) -> list[tuple[date, date]]:
    """Devuelve [(fecha_desde, fecha_hasta), ...] de ejecuciones que cubren parte del rango."""
    q = (
        db.session.query(EjecucionImportacion.fecha_desde, EjecucionImportacion.fecha_hasta)
        .filter(EjecucionImportacion.estado.in_(COBERTURA_ESTADOS))
        .filter(EjecucionImportacion.fecha_desde <= hasta)
        .filter(EjecucionImportacion.fecha_hasta >= desde)
    )
    return [(r[0], r[1]) for r in q.all()]


def _overlaps_for_origen(desde: date, hasta: date, origen: str) -> list[tuple[date, date]]:
    q = (
        db.session.query(EjecucionImportacion.fecha_desde, EjecucionImportacion.fecha_hasta)
        .filter(EjecucionImportacion.estado.in_(COBERTURA_ESTADOS))
        .filter(EjecucionImportacion.origen == origen)
        .filter(EjecucionImportacion.fecha_desde <= hasta)
        .filter(EjecucionImportacion.fecha_hasta >= desde)
    )
    return [(r[0], r[1]) for r in q.all()]


def _subtract_coverage(
    desde: date,
    hasta: date,
    covered: list[tuple[date, date]],
) -> list[Rango]:
    """Devuelve los sub-rangos de [desde, hasta] no cubiertos por `covered`."""
    if not covered:
        return [Rango(desde, hasta)]

    # Normalizar y mergear intervalos cubiertos
    norm = sorted(
        ((max(c[0], desde), min(c[1], hasta)) for c in covered),
        key=lambda r: r[0],
    )
    merged: list[list[date]] = []
    for a, b in norm:
        if a > b:
            continue
        if not merged or a > merged[-1][1] + timedelta(days=1):
            merged.append([a, b])
        else:
            merged[-1][1] = max(merged[-1][1], b)

    gaps: list[Rango] = []
    cursor = desde
    for a, b in merged:
        if cursor < a:
            gaps.append(Rango(cursor, a - timedelta(days=1)))
        cursor = max(cursor, b + timedelta(days=1))
    if cursor <= hasta:
        gaps.append(Rango(cursor, hasta))
    return gaps


def find_missing_ranges(desde: date, hasta: date, origen: str) -> list[Rango]:
    """Rangos del intervalo [desde, hasta] que aun NO estan cargados para `origen`."""
    if hasta < desde:
        return []
    covered = _overlaps_for_origen(desde, hasta, origen)
    cobertura_str = ",".join(f"{a}..{b}" for a, b in covered) if covered else "(ninguna)"
    gaps = _subtract_coverage(desde, hasta, covered)
    gaps_str = ",".join(f"{g.desde}..{g.hasta}" for g in gaps) if gaps else "(ninguno)"
    logger.info(
        "[ETL-availability] origen=%s desde=%s hasta=%s coberturas=[%s] huecos=[%s]",
        origen, desde, hasta, cobertura_str, gaps_str,
    )
    return gaps


def find_active_execution(
    desde: date,
    hasta: date,
    origen: str,
) -> EjecucionImportacion | None:
    """Devuelve una ejecucion encolada/en curso que ya cubre [desde, hasta], si existe.

    Usado para evitar disparar ETL duplicado para un rango equivalente o mas amplio.
    """
    activa = (
        db.session.query(EjecucionImportacion)
        .filter(EjecucionImportacion.estado.in_(ACTIVOS_ESTADOS))
        .filter(EjecucionImportacion.origen == origen)
        .filter(EjecucionImportacion.fecha_desde <= desde)
        .filter(EjecucionImportacion.fecha_hasta >= hasta)
        .order_by(EjecucionImportacion.id.desc())
        .first()
    )
    if activa is not None:
        logger.info(
            "[ETL-availability] active execution found id=%s estado=%s rango=%s..%s (cubre %s..%s)",
            activa.id, activa.estado, activa.fecha_desde, activa.fecha_hasta, desde, hasta,
        )
    else:
        logger.debug(
            "[ETL-availability] no active execution covers desde=%s hasta=%s origen=%s",
            desde, hasta, origen,
        )
    return activa


def find_any_active_execution(origen: str) -> EjecucionImportacion | None:
    """Cualquier ejecucion activa para `origen` (info para el cliente)."""
    return (
        db.session.query(EjecucionImportacion)
        .filter(EjecucionImportacion.estado.in_(ACTIVOS_ESTADOS))
        .filter(EjecucionImportacion.origen == origen)
        .order_by(EjecucionImportacion.id.desc())
        .first()
    )


__all__ = [
    "Rango",
    "COBERTURA_ESTADOS",
    "ACTIVOS_ESTADOS",
    "find_missing_ranges",
    "find_active_execution",
    "find_any_active_execution",
]
