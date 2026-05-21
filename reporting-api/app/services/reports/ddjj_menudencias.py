"""Reporte DDJJ Menudencias.

Las secciones se pueblan desde las vistas materializadas del schema
`reporting` (refrescadas por el ETL):
    - reporting.mv_ddjj_menudencias_diaria
    - reporting.mv_faena_diaria
    - reporting.mv_tropas_por_faena_diaria
    - reporting.mv_consistencia_ddjj

Secciones (ver `documentation/reporte ejemplo.md`):
    - "diaria"    : Produccion de menudencias del dia (solo cuando fecha_desde == fecha_hasta).
    - "decomisos" : Decomisos agregados por codigo en el rango.
    - "mensual"   : Acumulado de menudencias por codigo en el rango.

Parametros:
    - fecha_desde   (date, requerido)
    - fecha_hasta   (date, requerido)
    - mostrar_tropas (bool, default False) -> solo aplica al diario.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

import sqlalchemy as sa

from app.extensions import db
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
        # se evalua mas abajo contra reporting.mv_consistencia_ddjj.

        secciones, dias_excedidos = self._build_secciones(
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            mostrar_tropas=mostrar_tropas,
        )

        if dias_excedidos:
            fechas_str = ", ".join(d.isoformat() for d in dias_excedidos[:5])
            mas = "" if len(dias_excedidos) <= 5 else f" (+{len(dias_excedidos) - 5} mas)"
            alertas.append(
                ReportAlerta(
                    nivel="warning",
                    codigo="EXCEDE_CABEZAS",
                    mensaje=(
                        "Hay dias en los que la cantidad de cajas de menudencias "
                        f"supera a las cabezas faenadas: {fechas_str}{mas}."
                    ),
                )
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
            es_placeholder=False,
        )

    # ----- estructura de secciones -----
    def _build_secciones(
        self,
        *,
        fecha_desde: date,
        fecha_hasta: date,
        mostrar_tropas: bool,
    ) -> tuple[list[ReportSection], list[date]]:
        es_diario = fecha_desde == fecha_hasta

        # ---- Faena (cabezas) por dia en el rango ----
        faena_rows = db.session.execute(
            sa.text(
                """
                SELECT fecha_faena, cabezas, kg_estimados
                  FROM reporting.mv_faena_diaria
                 WHERE fecha_faena BETWEEN :desde AND :hasta
                """
            ),
            {"desde": fecha_desde, "hasta": fecha_hasta},
        ).mappings().all()
        cabezas_por_dia: dict[date, int] = {r["fecha_faena"]: int(r["cabezas"] or 0) for r in faena_rows}
        cabezas_total_rango = sum(cabezas_por_dia.values())

        # ---- Produccion por codigo (MENUDENCIA + DECOMISO) en el rango ----
        prod_rows = db.session.execute(
            sa.text(
                """
                SELECT mercaderia_codigo,
                       MAX(mercaderia_descripcion) AS mercaderia_descripcion,
                       categoria,
                       SUM(cajas)   AS cajas,
                       SUM(kg_neto) AS kg_neto
                  FROM reporting.mv_ddjj_menudencias_diaria
                 WHERE fecha_faena BETWEEN :desde AND :hasta
                 GROUP BY mercaderia_codigo, categoria
                 ORDER BY mercaderia_codigo
                """
            ),
            {"desde": fecha_desde, "hasta": fecha_hasta},
        ).mappings().all()

        # ---- Seccion DIARIA: solo se pobla cuando rango = 1 dia ----
        filas_diaria: list[dict[str, Any]] = []
        cajas_diaria = Decimal("0")
        kg_diaria = Decimal("0")
        if es_diario:
            dia_rows = db.session.execute(
                sa.text(
                    """
                    SELECT mercaderia_codigo,
                           mercaderia_descripcion,
                           cajas,
                           kg_neto
                      FROM reporting.mv_ddjj_menudencias_diaria
                     WHERE fecha_faena = :fecha
                       AND categoria = 'MENUDENCIA'
                     ORDER BY mercaderia_codigo
                    """
                ),
                {"fecha": fecha_desde},
            ).mappings().all()
            for r in dia_rows:
                cajas = r["cajas"] or Decimal("0")
                kg = r["kg_neto"] or Decimal("0")
                cajas_diaria += cajas
                kg_diaria += kg
                filas_diaria.append(
                    {
                        "codigo": r["mercaderia_codigo"],
                        "descripcion": r["mercaderia_descripcion"],
                        "cajas": _num(cajas),
                        "kg_neto": _num(kg),
                    }
                )

        tropas: list[dict[str, Any]] = []
        if mostrar_tropas and es_diario:
            tropas_rows = db.session.execute(
                sa.text(
                    """
                    SELECT numero_tropa, cabezas
                      FROM reporting.mv_tropas_por_faena_diaria
                     WHERE fecha_faena = :fecha
                     ORDER BY numero_tropa
                    """
                ),
                {"fecha": fecha_desde},
            ).mappings().all()
            tropas = [
                {"numero_tropa": r["numero_tropa"], "cabezas": int(r["cabezas"] or 0)}
                for r in tropas_rows
            ]

        cabezas_diaria = cabezas_por_dia.get(fecha_desde, 0) if es_diario else 0
        titulo_diaria = (
            f"Producción del día {fecha_desde.isoformat()}" if es_diario else "Producción diaria"
        )
        seccion_diaria = ReportSection(
            codigo="diaria",
            titulo=titulo_diaria,
            columnas=list(_COLUMNAS_PRODUCCION),
            filas=filas_diaria,
            totales={
                "cabezas_faenadas": cabezas_diaria,
                "cajas": _num(cajas_diaria),
                "kg_neto": _num(kg_diaria),
                "tropas": tropas,
            },
        )

        # ---- Seccion DECOMISOS: agregado por codigo en el rango ----
        filas_decomisos: list[dict[str, Any]] = []
        cajas_decom = Decimal("0")
        kg_decom = Decimal("0")
        for r in prod_rows:
            if r["categoria"] != "DECOMISO":
                continue
            cajas = r["cajas"] or Decimal("0")
            kg = r["kg_neto"] or Decimal("0")
            cajas_decom += cajas
            kg_decom += kg
            filas_decomisos.append(
                {
                    "codigo": r["mercaderia_codigo"],
                    "descripcion": r["mercaderia_descripcion"],
                    "cajas": _num(cajas),
                    "kg_neto": _num(kg),
                }
            )
        seccion_decomisos = ReportSection(
            codigo="decomisos",
            titulo=f"Decomisos {fecha_desde.isoformat()} a {fecha_hasta.isoformat()}",
            columnas=list(_COLUMNAS_PRODUCCION),
            filas=filas_decomisos,
            totales={
                "cabezas_faenadas": cabezas_total_rango,
                "cajas": _num(cajas_decom),
                "kg_neto": _num(kg_decom),
            },
        )

        # ---- Seccion MENSUAL: acumulado MENUDENCIA por codigo en el rango ----
        filas_mensual: list[dict[str, Any]] = []
        cajas_mensual = Decimal("0")
        kg_mensual = Decimal("0")
        for r in prod_rows:
            if r["categoria"] != "MENUDENCIA":
                continue
            cajas = r["cajas"] or Decimal("0")
            kg = r["kg_neto"] or Decimal("0")
            cajas_mensual += cajas
            kg_mensual += kg
            filas_mensual.append(
                {
                    "codigo": r["mercaderia_codigo"],
                    "descripcion": r["mercaderia_descripcion"],
                    "cajas": _num(cajas),
                    "kg_neto": _num(kg),
                }
            )
        seccion_mensual = ReportSection(
            codigo="mensual",
            titulo=f"Acumulado del rango {fecha_desde.isoformat()} a {fecha_hasta.isoformat()}",
            columnas=list(_COLUMNAS_PRODUCCION),
            filas=filas_mensual,
            totales={
                "cabezas_faenadas": cabezas_total_rango,
                "cajas": _num(cajas_mensual),
                "kg_neto": _num(kg_mensual),
            },
        )

        # ---- Consistencia: dias con cajas > cabezas faenadas ----
        consist_rows = db.session.execute(
            sa.text(
                """
                SELECT fecha_faena
                  FROM reporting.mv_consistencia_ddjj
                 WHERE fecha_faena BETWEEN :desde AND :hasta
                   AND alerta_excede_cabezas = TRUE
                 ORDER BY fecha_faena
                """
            ),
            {"desde": fecha_desde, "hasta": fecha_hasta},
        ).mappings().all()
        dias_excedidos = [r["fecha_faena"] for r in consist_rows]

        return [seccion_diaria, seccion_decomisos, seccion_mensual], dias_excedidos


def _num(value: Decimal | int | float | None) -> float:
    if value is None:
        return 0.0
    if isinstance(value, Decimal):
        return float(value)
    return float(value)
