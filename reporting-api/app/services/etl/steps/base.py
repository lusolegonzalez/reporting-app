"""Definicion de un step ETL.

Un step es una unidad atomica que extrae filas de Twins, las apila en
staging y luego las normaliza a core. Cada step reporta sus contadores
para que el runner los persista en etl.ejecucion_tabla.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Protocol

from app.services.etl.source import TwinsSource


@dataclass
class StepResult:
    tabla_destino: str
    filas_leidas: int = 0
    filas_insertadas: int = 0
    filas_actualizadas: int = 0
    filas_descartadas: int = 0
    duracion_ms: int = 0
    errores: list[tuple[str | None, str]] = field(default_factory=list)
    """Cada error: (source_pk, mensaje)."""


class EtlStep(Protocol):
    nombre: str
    tabla_destino: str

    def run(
        self,
        *,
        ejecucion_id: int,
        source: TwinsSource,
        desde: date,
        hasta: date,
    ) -> StepResult:
        ...
