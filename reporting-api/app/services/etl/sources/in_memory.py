"""Fuente Twins en memoria para tests/dev sin pyodbc."""
from __future__ import annotations

from datetime import date
from typing import Any, Iterable


class InMemoryTwinsSource:
    def __init__(
        self,
        *,
        mercaderias: list[dict[str, Any]] | None = None,
        operarios: list[dict[str, Any]] | None = None,
        tropas: list[dict[str, Any]] | None = None,
        movimientos: list[dict[str, Any]] | None = None,
        faena: list[dict[str, Any]] | None = None,
        salidas: list[dict[str, Any]] | None = None,
    ) -> None:
        self._mercaderias = mercaderias or []
        self._operarios = operarios or []
        self._tropas = tropas or []
        self._movimientos = movimientos or []
        self._faena = faena or []
        self._salidas = salidas or []

    def fetch_mercaderias(self) -> Iterable[dict[str, Any]]:
        return list(self._mercaderias)

    def fetch_operarios(self) -> Iterable[dict[str, Any]]:
        return list(self._operarios)

    def fetch_tropas(self, desde: date, hasta: date) -> Iterable[dict[str, Any]]:
        del desde, hasta
        return list(self._tropas)

    def fetch_movimientos(self, desde: date, hasta: date) -> Iterable[dict[str, Any]]:
        del desde, hasta
        return list(self._movimientos)

    def fetch_faena(self, desde: date, hasta: date) -> Iterable[dict[str, Any]]:
        del desde, hasta
        return list(self._faena)

    def fetch_salidas(self, desde: date, hasta: date) -> Iterable[dict[str, Any]]:
        del desde, hasta
        return list(self._salidas)
