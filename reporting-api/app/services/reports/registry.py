"""Registry de reportes disponibles."""
from __future__ import annotations

from typing import Iterable

from app.services.reports.base import ReportDefinition, ReportNotFoundError


class ReportRegistry:
    def __init__(self) -> None:
        self._items: dict[str, ReportDefinition] = {}

    def register(self, report: ReportDefinition) -> None:
        codigo = report.codigo.strip().upper()
        if not codigo:
            raise ValueError("ReportDefinition.codigo vacio.")
        self._items[codigo] = report

    def get(self, codigo: str) -> ReportDefinition:
        item = self._items.get((codigo or "").strip().upper())
        if item is None:
            raise ReportNotFoundError(f"Reporte {codigo!r} no registrado.")
        return item

    def all(self) -> Iterable[ReportDefinition]:
        return list(self._items.values())


report_registry = ReportRegistry()


def _bootstrap() -> None:
    """Registra los reportes concretos disponibles."""
    from app.services.reports.ddjj_menudencias import DdjjMenudenciasReport

    report_registry.register(DdjjMenudenciasReport())


_bootstrap()
