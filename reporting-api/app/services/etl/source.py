"""Contrato de la fuente Twins.

El runner ETL no conoce pyodbc ni el dialecto SQL Server: solo consume
un objeto que implemente este Protocol. Esto permite tests con fuentes
en memoria y aislar el connector real cuando se agregue pyodbc.
"""
from __future__ import annotations

from datetime import date
from typing import Any, Iterable, Protocol


class TwinsSource(Protocol):
    """Origen de datos Twins. Devuelve filas como dicts."""

    def fetch_mercaderias(self) -> Iterable[dict[str, Any]]:
        """Catalogo completo de mercaderias (no requiere ventana)."""
        ...

    def fetch_operarios(self) -> Iterable[dict[str, Any]]:
        ...

    def fetch_tropas(self, desde: date, hasta: date) -> Iterable[dict[str, Any]]:
        ...

    def fetch_movimientos(self, desde: date, hasta: date) -> Iterable[dict[str, Any]]:
        ...

    def fetch_faena(self, desde: date, hasta: date) -> Iterable[dict[str, Any]]:
        ...

    def fetch_salidas(self, desde: date, hasta: date) -> Iterable[dict[str, Any]]:
        ...
