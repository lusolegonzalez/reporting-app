"""Reporte DDJJ Menudencias.

Las secciones se pueblan desde las vistas materializadas del schema
`reporting` (refrescadas por el ETL):
    - reporting.mv_ddjj_menudencias_diaria  (filtrada por fecha de produccion)
    - reporting.mv_faena_diaria             (filtrada por fecha de faena)
    - reporting.mv_tropas_por_faena_diaria  (filtrada por fecha de faena)
    - reporting.mv_consistencia_ddjj        (solo si ambos rangos coinciden)

Secciones (ver `documentation/reporte ejemplo.md`):
    - "diaria"    : Produccion de menudencias del dia (solo cuando el rango
                    de fecha de faena es de un unico dia).
    - "decomisos" : Decomisos agregados por codigo (rango de produccion).
    - "mensual"   : Acumulado de menudencias por codigo (solo cuando el rango
                    de fecha de faena cubre mas de un dia).

Parametros (rangos independientes; ver Excel modelo SENASA):
    - fecha_produccion_desde / fecha_produccion_hasta : aplican a la salida /
      emision de menudencias y decomisos (cajas y kg).
    - fecha_faena_desde / fecha_faena_hasta : aplican a la faena (cabezas
      faenadas y tropas).
    - mostrar_tropas (bool, default False) : solo cuando rango faena = 1 dia.

Cabezas: en la fuente cada registro de faena representa una "media res"
(2 medias reses = 1 cabeza), por lo que las cabezas mostradas y exportadas
se calculan como SUM(medias) / 2 (redondeado).
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

# 2 medias reses = 1 cabeza. La fuente (movimientos.Faena de Twins) registra
# una fila por media res; el ETL la carga con cabezas=1. Para la DDJJ hay que
# dividir por 2 para obtener cabezas reales. Se reporta fraccionario (0.5)
# cuando la cantidad de medias es impar; no se redondea ni se trunca.
_MEDIAS_POR_CABEZA = 2


def _medias_a_cabezas(medias: int | float | Decimal | None) -> float:
    if medias is None:
        return 0.0
    return float(medias) / _MEDIAS_POR_CABEZA


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
            nombre="fecha_produccion_desde",
            tipo="date",
            requerido=True,
            etiqueta="Producción · desde",
            descripcion="Fecha de produccion (emision de salida) - inicio del rango (YYYY-MM-DD).",
        ),
        ReportParameter(
            nombre="fecha_produccion_hasta",
            tipo="date",
            requerido=True,
            etiqueta="Producción · hasta",
            descripcion="Fecha de produccion (emision de salida) - fin del rango (YYYY-MM-DD).",
        ),
        ReportParameter(
            nombre="fecha_faena_desde",
            tipo="date",
            requerido=True,
            etiqueta="Faena · desde",
            descripcion="Fecha de faena - inicio del rango (YYYY-MM-DD).",
        ),
        ReportParameter(
            nombre="fecha_faena_hasta",
            tipo="date",
            requerido=True,
            etiqueta="Faena · hasta",
            descripcion="Fecha de faena - fin del rango (YYYY-MM-DD).",
        ),
        ReportParameter(
            nombre="mostrar_tropas",
            tipo="bool",
            requerido=False,
            valor_por_defecto=False,
            etiqueta="Mostrar tropas",
            descripcion="Incluir listado de tropas. Solo aplica si el rango de fecha de faena es de un único día.",
        ),
    )

    # ----- parse + validate -----
    def parse_and_validate(self, raw: dict[str, Any]) -> ReportRequest:
        prod_desde = parse_date(raw.get("fecha_produccion_desde"), field_name="fecha_produccion_desde", requerido=True)
        prod_hasta = parse_date(raw.get("fecha_produccion_hasta"), field_name="fecha_produccion_hasta", requerido=True)
        faena_desde = parse_date(raw.get("fecha_faena_desde"), field_name="fecha_faena_desde", requerido=True)
        faena_hasta = parse_date(raw.get("fecha_faena_hasta"), field_name="fecha_faena_hasta", requerido=True)
        mostrar_tropas = parse_bool(raw.get("mostrar_tropas"), field_name="mostrar_tropas", default=False)

        assert prod_desde is not None and prod_hasta is not None
        assert faena_desde is not None and faena_hasta is not None

        for desde, hasta, campo in (
            (prod_desde, prod_hasta, "fecha_produccion_hasta"),
            (faena_desde, faena_hasta, "fecha_faena_hasta"),
        ):
            if hasta < desde:
                raise ReportValidationError(
                    f"{campo} debe ser mayor o igual a su 'desde'.",
                    field=campo,
                )
            if (hasta - desde).days + 1 > MAX_DIAS_RANGO:
                raise ReportValidationError(
                    f"El rango excede el máximo permitido ({MAX_DIAS_RANGO} días).",
                    field=campo,
                )

        # Regla de negocio: tropas solo cuando faena es un unico dia.
        es_diario_faena = faena_desde == faena_hasta
        if mostrar_tropas and not es_diario_faena:
            mostrar_tropas = False  # se ignora; se reporta como alerta

        return ReportRequest(
            codigo_reporte=self.codigo,
            parametros={
                "fecha_produccion_desde": prod_desde,
                "fecha_produccion_hasta": prod_hasta,
                "fecha_faena_desde": faena_desde,
                "fecha_faena_hasta": faena_hasta,
                "mostrar_tropas": mostrar_tropas,
            },
            raw_parametros=dict(raw),
        )

    # ----- rango ETL requerido -----
    def loaded_range_requerido(self, request: ReportRequest) -> tuple[date, date] | None:
        """Indica el rango de fechas que debe estar cargado en la base intermedia
        antes de poder ejecutar el reporte. Si falta, el endpoint de reportes
        dispara el ETL on-demand antes de ejecutar.

        Se devuelve el rango envolvente (min desde, max hasta) que cubre tanto
        produccion como faena, porque el ETL trae faena+salidas en una sola
        corrida y necesitamos cobertura sobre la union.
        """
        p = request.parametros
        desde = min(p["fecha_produccion_desde"], p["fecha_faena_desde"])
        hasta = max(p["fecha_produccion_hasta"], p["fecha_faena_hasta"])
        return (desde, hasta)

    # ----- execute -----
    def execute(self, request: ReportRequest) -> ReportResponse:
        prod_desde: date = request.parametros["fecha_produccion_desde"]
        prod_hasta: date = request.parametros["fecha_produccion_hasta"]
        faena_desde: date = request.parametros["fecha_faena_desde"]
        faena_hasta: date = request.parametros["fecha_faena_hasta"]
        mostrar_tropas: bool = request.parametros["mostrar_tropas"]
        raw_mostrar_tropas = parse_bool(
            request.raw_parametros.get("mostrar_tropas"),
            field_name="mostrar_tropas",
            default=False,
        )

        alertas: list[ReportAlerta] = []

        if raw_mostrar_tropas and faena_desde != faena_hasta:
            alertas.append(
                ReportAlerta(
                    nivel="warning",
                    codigo="TROPAS_SOLO_DIARIO",
                    mensaje=(
                        "Las tropas solo se muestran cuando el rango de fecha de faena "
                        "es de un único día. Se ignoró 'mostrar_tropas'."
                    ),
                )
            )

        # Alerta informativa: los rangos de produccion y faena no se solapan.
        # No bloquea la ejecucion; sirve para avisar al usuario que la lectura
        # cruzada (cabezas vs cajas) puede no ser comparable.
        if prod_hasta < faena_desde or faena_hasta < prod_desde:
            alertas.append(
                ReportAlerta(
                    nivel="warning",
                    codigo="RANGOS_SIN_SOLAPAMIENTO",
                    mensaje=(
                        "Los rangos de fecha de producción y fecha de faena no se solapan. "
                        "El reporte se ejecuta igualmente, pero los totales de cabezas "
                        "y cajas corresponden a períodos distintos."
                    ),
                )
            )

        secciones, dias_excedidos = self._build_secciones(
            prod_desde=prod_desde,
            prod_hasta=prod_hasta,
            faena_desde=faena_desde,
            faena_hasta=faena_hasta,
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
                "fecha_produccion_desde": prod_desde,
                "fecha_produccion_hasta": prod_hasta,
                "fecha_faena_desde": faena_desde,
                "fecha_faena_hasta": faena_hasta,
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
        prod_desde: date,
        prod_hasta: date,
        faena_desde: date,
        faena_hasta: date,
        mostrar_tropas: bool,
    ) -> tuple[list[ReportSection], list[date]]:
        es_diario = faena_desde == faena_hasta

        # ---- Faena (medias reses) por dia en el rango de FAENA ----
        faena_rows = db.session.execute(
            sa.text(
                """
                SELECT fecha_faena, cabezas AS medias_reses, kg_estimados
                  FROM reporting.mv_faena_diaria
                 WHERE fecha_faena BETWEEN :desde AND :hasta
                """
            ),
            {"desde": faena_desde, "hasta": faena_hasta},
        ).mappings().all()
        # cabezas_por_dia: ya convertido (medias / 2, fraccionario si impar)
        cabezas_por_dia: dict[date, float] = {
            r["fecha_faena"]: _medias_a_cabezas(r["medias_reses"]) for r in faena_rows
        }
        cabezas_total_rango = sum(cabezas_por_dia.values())

        # ---- Produccion por codigo (MENUDENCIA + DECOMISO) en el rango de PRODUCCION ----
        # Nota: en mv_ddjj_menudencias_diaria la columna "fecha_faena" mapea en
        # realidad a core.salida.fecha_emision (= fecha de produccion).
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
            {"desde": prod_desde, "hasta": prod_hasta},
        ).mappings().all()

        # ---- Seccion DIARIA: solo cuando rango de faena = 1 dia ----
        seccion_diaria: ReportSection | None = None
        if es_diario:
            filas_diaria: list[dict[str, Any]] = []
            cajas_diaria = Decimal("0")
            kg_diaria = Decimal("0")
            # Las filas del dia se toman del rango de produccion para soportar
            # el caso del Excel modelo: faena del dia X, produccion del dia X+1.
            dia_rows = db.session.execute(
                sa.text(
                    """
                    SELECT mercaderia_codigo,
                           MAX(mercaderia_descripcion) AS mercaderia_descripcion,
                           SUM(cajas)   AS cajas,
                           SUM(kg_neto) AS kg_neto
                      FROM reporting.mv_ddjj_menudencias_diaria
                     WHERE fecha_faena BETWEEN :desde AND :hasta
                       AND categoria = 'MENUDENCIA'
                     GROUP BY mercaderia_codigo
                     ORDER BY mercaderia_codigo
                    """
                ),
                {"desde": prod_desde, "hasta": prod_hasta},
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
            if mostrar_tropas:
                tropas_rows = db.session.execute(
                    sa.text(
                        """
                        SELECT numero_tropa, cabezas AS medias_reses
                          FROM reporting.mv_tropas_por_faena_diaria
                         WHERE fecha_faena = :fecha
                         ORDER BY numero_tropa
                        """
                    ),
                    {"fecha": faena_desde},
                ).mappings().all()
                tropas = [
                    {
                        "numero_tropa": r["numero_tropa"],
                        "cabezas": _medias_a_cabezas(r["medias_reses"]),
                    }
                    for r in tropas_rows
                ]

            cabezas_diaria = cabezas_por_dia.get(faena_desde, 0.0)
            seccion_diaria = ReportSection(
                codigo="diaria",
                titulo=(
                    f"Producción del día (faena {faena_desde.isoformat()}"
                    + (
                        f" / producción {prod_desde.isoformat()})"
                        if prod_desde == prod_hasta and prod_desde != faena_desde
                        else (
                            f" / producción {prod_desde.isoformat()} a {prod_hasta.isoformat()})"
                            if prod_desde != prod_hasta
                            else ")"
                        )
                    )
                ),
                columnas=list(_COLUMNAS_PRODUCCION),
                filas=filas_diaria,
                totales={
                    "cabezas_faenadas": cabezas_diaria,
                    "cajas": _num(cajas_diaria),
                    "kg_neto": _num(kg_diaria),
                    "tropas": tropas,
                },
            )

        # ---- Seccion DECOMISOS: agregado por codigo (rango de produccion) ----
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
            titulo=(
                f"Decomisos · producción {prod_desde.isoformat()} a {prod_hasta.isoformat()}"
                f" / faena {faena_desde.isoformat()} a {faena_hasta.isoformat()}"
            ),
            columnas=list(_COLUMNAS_PRODUCCION),
            filas=filas_decomisos,
            totales={
                "cabezas_faenadas": cabezas_total_rango,
                "cajas": _num(cajas_decom),
                "kg_neto": _num(kg_decom),
            },
        )

        # ---- Seccion MENSUAL: acumulado MENUDENCIA por codigo (rango produccion) ----
        # Solo aplica cuando el rango de faena cubre mas de un dia.
        seccion_mensual: ReportSection | None = None
        if not es_diario:
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
                titulo=(
                    f"Acumulado · producción {prod_desde.isoformat()} a {prod_hasta.isoformat()}"
                    f" / faena {faena_desde.isoformat()} a {faena_hasta.isoformat()}"
                ),
                columnas=list(_COLUMNAS_PRODUCCION),
                filas=filas_mensual,
                totales={
                    "cabezas_faenadas": cabezas_total_rango,
                    "cajas": _num(cajas_mensual),
                    "kg_neto": _num(kg_mensual),
                },
            )

        # ---- Consistencia: dias con cajas > cabezas faenadas ----
        # La MV `mv_consistencia_ddjj` cruza dia-a-dia faena vs produccion bajo
        # el supuesto de que ambas caen el mismo dia. Cuando los rangos
        # difieren ese supuesto no se sostiene, asi que solo aplicamos el
        # chequeo si ambos rangos son identicos. Ademas, la MV compara contra
        # medias reses (no cabezas), por lo que se recalcula aqui con /2.
        dias_excedidos: list[date] = []
        if prod_desde == faena_desde and prod_hasta == faena_hasta:
            consist_rows = db.session.execute(
                sa.text(
                    """
                    SELECT fecha_faena, cabezas_faenadas AS medias_reses, cajas_menudencias
                      FROM reporting.mv_consistencia_ddjj
                     WHERE fecha_faena BETWEEN :desde AND :hasta
                     ORDER BY fecha_faena
                    """
                ),
                {"desde": faena_desde, "hasta": faena_hasta},
            ).mappings().all()
            for r in consist_rows:
                cabezas_reales = _medias_a_cabezas(r["medias_reses"])
                cajas = float(r["cajas_menudencias"] or 0)
                if cajas > cabezas_reales:
                    dias_excedidos.append(r["fecha_faena"])

        secciones: list[ReportSection] = []
        if seccion_diaria is not None:
            secciones.append(seccion_diaria)
        secciones.append(seccion_decomisos)
        if seccion_mensual is not None:
            secciones.append(seccion_mensual)

        return secciones, dias_excedidos


def _num(value: Decimal | int | float | None) -> float:
    if value is None:
        return 0.0
    if isinstance(value, Decimal):
        return float(value)
    return float(value)
