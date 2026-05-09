"""Reporte DDJJ Menudencias.

Estructura backend del reporte. La consulta final NO esta cerrada todavia:
mientras tanto, `execute` devuelve la estructura de secciones esperada con
filas vacias y marca `es_placeholder=True`. Cuando se cierre la query SQL,
solo hay que reemplazar el cuerpo de `_build_secciones`.

Secciones esperadas (ver `documentation/reporte ejemplo.md`):
    - "diaria"    : Produccion del dia (fecha_desde == fecha_hasta).
    - "decomisos" : Decomisos del rango.
    - "mensual"   : Acumulado mensual del rango.

Parametros:
    - fecha_desde   (date, requerido)
    - fecha_hasta   (date, requerido)
    - mostrar_tropas (bool, default False) -> solo aplica al diario.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from app.services.reports.base import (
    ReportAlerta,
    ReportParameter,
    ReportRequest,
    ReportResponse,
    ReportSection,
    ReportValidationError,
    parse_bool,
    parse_date,
)


CODIGO = "DDJJ_MENUDENCIAS"
NOMBRE = "Declaración Jurada Menudencias"
DESCRIPCION = (
    "Reporte de producción en carácter de declaración jurada (SENASA). "
    "Combina producción de menudencias y decomisos con cabezas faenadas."
)

# Limite duro para evitar rangos absurdos. Se puede mover a config si hace falta.
MAX_DIAS_RANGO = 366


_COLUMNAS_PRODUCCION = [
    {"key": "codigo", "titulo": "Código Producto", "tipo": "string"},
    {"key": "descripcion", "titulo": "Descripción", "tipo": "string"},
    {"key": "cajas", "titulo": "Cajas", "tipo": "number"},
    {"key": "kg_neto", "titulo": "Kg. Neto", "tipo": "number"},
]


class DdjjMenudenciasReport:
    codigo = CODIGO
    nombre = NOMBRE
    descripcion = DESCRIPCION
    parametros: tuple[ReportParameter, ...] = (
        ReportParameter(
            nombre="fecha_desde",
            tipo="date",
            requerido=True,
            descripcion="Fecha de faena - inicio del rango (YYYY-MM-DD).",
        ),
        ReportParameter(
            nombre="fecha_hasta",
            tipo="date",
            requerido=True,
            descripcion="Fecha de faena - fin del rango (YYYY-MM-DD).",
        ),
        ReportParameter(
            nombre="mostrar_tropas",
            tipo="bool",
            requerido=False,
            valor_por_defecto=False,
            descripcion="Incluir listado de tropas. Solo aplica si el rango es de un único día.",
        ),
    )

    # ----- parse + validate -----
    def parse_and_validate(self, raw: dict[str, Any]) -> ReportRequest:
        fecha_desde = parse_date(raw.get("fecha_desde"), field_name="fecha_desde", requerido=True)
        fecha_hasta = parse_date(raw.get("fecha_hasta"), field_name="fecha_hasta", requerido=True)
        mostrar_tropas = parse_bool(raw.get("mostrar_tropas"), field_name="mostrar_tropas", default=False)

        assert fecha_desde is not None and fecha_hasta is not None  # asegurado arriba

        if fecha_hasta < fecha_desde:
            raise ReportValidationError(
                "fecha_hasta debe ser mayor o igual a fecha_desde.",
                field="fecha_hasta",
            )

        if (fecha_hasta - fecha_desde).days + 1 > MAX_DIAS_RANGO:
            raise ReportValidationError(
                f"El rango excede el máximo permitido ({MAX_DIAS_RANGO} días).",
                field="fecha_hasta",
            )

        # Regla de negocio relevada: tropas solo en el reporte diario.
        es_diario = fecha_desde == fecha_hasta
        if mostrar_tropas and not es_diario:
            mostrar_tropas = False  # se ignora silenciosamente; se reporta como alerta

        return ReportRequest(
            codigo_reporte=self.codigo,
            parametros={
                "fecha_desde": fecha_desde,
                "fecha_hasta": fecha_hasta,
                "mostrar_tropas": mostrar_tropas,
            },
            raw_parametros=dict(raw),
        )

    # ----- execute -----
    def execute(self, request: ReportRequest) -> ReportResponse:
        fecha_desde: date = request.parametros["fecha_desde"]
        fecha_hasta: date = request.parametros["fecha_hasta"]
        mostrar_tropas: bool = request.parametros["mostrar_tropas"]
        raw_mostrar_tropas = parse_bool(
            request.raw_parametros.get("mostrar_tropas"),
            field_name="mostrar_tropas",
            default=False,
        )

        alertas: list[ReportAlerta] = []

        # Alertas de validacion / consistencia (estructura lista para conectar
        # los chequeos reales contra core/reporting cuando exista la query final).
        if raw_mostrar_tropas and fecha_desde != fecha_hasta:
            alertas.append(
                ReportAlerta(
                    nivel="warning",
                    codigo="TROPAS_SOLO_DIARIO",
                    mensaje=(
                        "Las tropas solo se muestran en reportes de un único día. "
                        "Se ignoró 'mostrar_tropas' para el rango solicitado."
                    ),
                )
            )

        # Placeholder de chequeo de consistencia menudencias vs cabezas:
        # cuando se conecte la query, comparar produccion vs cabezas faenadas
        # del periodo y emitir alertas si la relacion sale de un rango razonable.
        # Se deja la entrada estructurada para no inventar logica no confirmada.
        alertas.append(
            ReportAlerta(
                nivel="info",
                codigo="CONSISTENCIA_PENDIENTE",
                mensaje=(
                    "Validación de consistencia menudencias vs cabezas faenadas "
                    "no implementada todavía: se conectará al cerrar la consulta SQL."
                ),
            )
        )

        secciones = self._build_secciones(
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            mostrar_tropas=mostrar_tropas,
        )

        return ReportResponse(
            codigo_reporte=self.codigo,
            nombre_reporte=self.nombre,
            parametros={
                "fecha_desde": fecha_desde,
                "fecha_hasta": fecha_hasta,
                "mostrar_tropas": mostrar_tropas,
            },
            secciones=secciones,
            alertas=alertas,
            es_placeholder=True,
        )

    # ----- estructura de secciones -----
    def _build_secciones(
        self,
        *,
        fecha_desde: date,
        fecha_hasta: date,
        mostrar_tropas: bool,
    ) -> list[ReportSection]:
        es_diario = fecha_desde == fecha_hasta

        seccion_diaria = ReportSection(
            codigo="diaria",
            titulo=f"Producción del día {fecha_desde.isoformat()}" if es_diario else "Producción diaria",
            columnas=list(_COLUMNAS_PRODUCCION),
            filas=[],
            totales={"cabezas_faenadas": 0, "cajas": 0, "kg_neto": 0.0, "tropas": []},
        )
        if mostrar_tropas and es_diario:
            seccion_diaria.totales["tropas"] = []  # listo para llenar con numeros de tropa

        seccion_decomisos = ReportSection(
            codigo="decomisos",
            titulo=f"Decomisos {fecha_desde.isoformat()} a {fecha_hasta.isoformat()}",
            columnas=list(_COLUMNAS_PRODUCCION),
            filas=[],
            totales={"cabezas_faenadas": 0, "cajas": 0, "kg_neto": 0.0},
        )

        seccion_mensual = ReportSection(
            codigo="mensual",
            titulo=f"Acumulado del rango {fecha_desde.isoformat()} a {fecha_hasta.isoformat()}",
            columnas=list(_COLUMNAS_PRODUCCION),
            filas=[],
            totales={"cabezas_faenadas": 0, "cajas": 0, "kg_neto": 0.0},
        )

        return [seccion_diaria, seccion_decomisos, seccion_mensual]
