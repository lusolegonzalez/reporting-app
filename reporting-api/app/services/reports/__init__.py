"""Capa backend de reporting (definicion + registry + reportes concretos)."""
from app.services.reports.base import (
    ReportAlerta,
    ReportDefinition,
    ReportNotFoundError,
    ReportParameter,
    ReportPermissionError,
    ReportRequest,
    ReportResponse,
    ReportSection,
    ReportValidationError,
)
from app.services.reports.registry import report_registry

__all__ = [
    "ReportAlerta",
    "ReportDefinition",
    "ReportNotFoundError",
    "ReportParameter",
    "ReportPermissionError",
    "ReportRequest",
    "ReportResponse",
    "ReportSection",
    "ReportValidationError",
    "report_registry",
]
