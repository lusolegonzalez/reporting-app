"""Capa backend de reportes: definicion, parametros y ejecucion.

Pieza clave de la capa de reporting:

- `ReportParameter`: descripcion estructurada de un parametro (tipo, requerido, etc.).
- `ReportRequest`: parametros validados de una corrida.
- `ReportAlerta`: alerta de validacion/consistencia.
- `ReportSection` / `ReportResponse`: respuesta estandarizada.
- `ReportDefinition`: contrato que cada reporte concreto debe implementar.

Los reportes concretos viven en submodulos (ej. `ddjj_menudencias.py`)
y se publican via `app.services.reports.registry.report_registry`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Iterable, Protocol


# ---------------------------------------------------------------------------
# Tipos de parametros y errores
# ---------------------------------------------------------------------------


class ReportValidationError(Exception):
    """Error de validacion de parametros del reporte (->400)."""

    def __init__(self, message: str, *, field: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.field = field


class ReportNotFoundError(Exception):
    """El codigo de reporte no esta registrado (->404)."""


class ReportPermissionError(Exception):
    """El usuario no tiene permiso para la operacion solicitada (->403)."""


@dataclass(frozen=True)
class ReportParameter:
    """Descripcion estructurada de un parametro de reporte."""

    nombre: str
    tipo: str  # "date" | "bool" | "string" | "int"
    requerido: bool = False
    descripcion: str | None = None
    valor_por_defecto: Any = None
    # Etiqueta legible para mostrar en la UI. Si es None, el frontend usa `nombre`.
    etiqueta: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "nombre": self.nombre,
            "tipo": self.tipo,
            "requerido": self.requerido,
            "descripcion": self.descripcion,
            "valor_por_defecto": self.valor_por_defecto,
            "etiqueta": self.etiqueta,
        }


@dataclass
class ReportAlerta:
    """Alerta de validacion / consistencia para mostrar al usuario."""

    nivel: str  # "info" | "warning" | "error"
    codigo: str
    mensaje: str

    def to_dict(self) -> dict[str, Any]:
        return {"nivel": self.nivel, "codigo": self.codigo, "mensaje": self.mensaje}


@dataclass
class ReportSection:
    """Una seccion del resultado (ej. "diaria", "decomisos", "mensual")."""

    codigo: str
    titulo: str
    columnas: list[dict[str, Any]] = field(default_factory=list)
    filas: list[dict[str, Any]] = field(default_factory=list)
    totales: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "codigo": self.codigo,
            "titulo": self.titulo,
            "columnas": self.columnas,
            "filas": self.filas,
            "totales": self.totales,
        }


@dataclass
class ReportRequest:
    """Request validado y normalizado para la ejecucion del reporte."""

    codigo_reporte: str
    parametros: dict[str, Any]
    raw_parametros: dict[str, Any] = field(default_factory=dict)


@dataclass
class ReportResponse:
    """Respuesta estandarizada de la ejecucion de un reporte."""

    codigo_reporte: str
    nombre_reporte: str
    parametros: dict[str, Any]
    secciones: list[ReportSection] = field(default_factory=list)
    alertas: list[ReportAlerta] = field(default_factory=list)
    # Banderas de exportacion permitida para el usuario actual.
    export_permitido: dict[str, bool] = field(
        default_factory=lambda: {"excel": False, "pdf": False}
    )
    generado_en: datetime = field(default_factory=lambda: datetime.utcnow())
    # Marca si el cuerpo trae datos reales o es solo estructura (placeholder).
    es_placeholder: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "codigo_reporte": self.codigo_reporte,
            "nombre_reporte": self.nombre_reporte,
            "parametros": _jsonable(self.parametros),
            "secciones": [s.to_dict() for s in self.secciones],
            "alertas": [a.to_dict() for a in self.alertas],
            "export_permitido": dict(self.export_permitido),
            "generado_en": self.generado_en.isoformat(),
            "es_placeholder": self.es_placeholder,
        }


def _jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


# ---------------------------------------------------------------------------
# Contrato de un reporte concreto
# ---------------------------------------------------------------------------


class ReportDefinition(Protocol):
    """Contrato que implementa cada reporte concreto.

    El servicio de reportes orquesta:
        1. parse_and_validate(raw)  -> ReportRequest (puede lanzar ReportValidationError)
        2. execute(request, ctx)    -> ReportResponse

    `execute` es lo que cada reporte concreto resuelve contra la base
    intermedia (PostgreSQL `core.*` / `reporting.*`). Mientras la query
    final no este cerrada, una implementacion puede devolver una respuesta
    `es_placeholder=True` con la estructura de secciones lista.
    """

    codigo: str
    nombre: str
    descripcion: str
    parametros: tuple[ReportParameter, ...]

    def parse_and_validate(self, raw: dict[str, Any]) -> ReportRequest: ...

    def execute(self, request: ReportRequest) -> ReportResponse: ...


# ---------------------------------------------------------------------------
# Helpers de parseo de parametros
# ---------------------------------------------------------------------------


def parse_date(value: Any, *, field_name: str, requerido: bool = True) -> date | None:
    if value in (None, ""):
        if requerido:
            raise ReportValidationError(f"{field_name} es requerido.", field=field_name)
        return None
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        raise ReportValidationError(f"{field_name} debe ser fecha YYYY-MM-DD.", field=field_name)
    try:
        return datetime.strptime(value.strip(), "%Y-%m-%d").date()
    except ValueError as exc:
        raise ReportValidationError(
            f"{field_name} invalida (formato YYYY-MM-DD).", field=field_name
        ) from exc


def parse_bool(value: Any, *, field_name: str, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int,)):
        return bool(value)
    if isinstance(value, str):
        v = value.strip().lower()
        if v in ("true", "1", "yes", "si", "sí"):
            return True
        if v in ("false", "0", "no"):
            return False
    raise ReportValidationError(f"{field_name} debe ser booleano.", field=field_name)
