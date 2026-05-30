"""Fuente Twins real contra SQL Server, en modo SOLO LECTURA.

Implementa el contrato `TwinsSource` usando pyodbc. El connector se
configura por variables de entorno (ver `BaseConfig.MSSQL_*`) y nunca
ejecuta DDL/DML: se rechaza cualquier sentencia que no comience con
`SELECT` o `WITH` (CTE -> SELECT).

Las consultas que viven aca son intencionalmente simples y acotadas a
los catalogos / movimientos minimos que necesita la base intermedia.
La logica final del reporte DDJJ Menudencias NO vive aca.
"""
from __future__ import annotations

import logging
from contextlib import contextmanager
from datetime import date, timedelta
from typing import Any, Iterable, Iterator

logger = logging.getLogger(__name__)


def _log_result(method: str, filas: int, desde: date | None = None, hasta: date | None = None) -> None:
    """Logging de diagnóstico: nombre del método, ventana y filas devueltas."""
    if desde is not None:
        logger.info("[ETL-source] %s | desde=%s hasta=%s | filas=%d", method, desde, hasta, filas)
    else:
        logger.info("[ETL-source] %s | filas=%d", method, filas)


# ---------------------------------------------------------------------------
# Helpers de conexion
# ---------------------------------------------------------------------------


def _build_conn_str(cfg: dict[str, Any]) -> str:
    """Arma el connection string ODBC desde el dict de configuracion Flask."""
    parts = [
        f"DRIVER={cfg['MSSQL_DRIVER']}",
        f"SERVER={cfg['MSSQL_SERVER']},{cfg['MSSQL_PORT']}",
        f"DATABASE={cfg['MSSQL_DATABASE']}",
        f"UID={cfg['MSSQL_UID']}",
        f"PWD={cfg['MSSQL_PWD']}",
        f"Encrypt={cfg['MSSQL_ENCRYPT']}",
        f"TrustServerCertificate={cfg['MSSQL_TRUST_SERVER_CERTIFICATE']}",
        # Sugerencia de read-only al servidor (efectiva si hay AG con replica
        # de lectura; en server stand-alone no hace dano).
        "ApplicationIntent=ReadOnly",
    ]
    return ";".join(parts) + ";"


def _assert_select(sql: str) -> None:
    """Defensa en profundidad: rechaza cualquier cosa que no sea SELECT/CTE."""
    head = sql.lstrip().lstrip(";").lstrip().lower()
    if not (head.startswith("select") or head.startswith("with")):
        raise RuntimeError("SqlServerTwinsSource solo permite consultas SELECT.")


# ---------------------------------------------------------------------------
# Source
# ---------------------------------------------------------------------------


class SqlServerTwinsSource:
    """Origen Twins (SQL Server) en modo solo lectura.

    Cada metodo abre una conexion nueva (sin pooling de pyodbc) y la cierra
    al terminar. Es deliberadamente sencillo: el dataset esperado por
    consulta es acotado por la ventana `desde/hasta`.
    """

    def __init__(
        self,
        *,
        conn_str: str,
        login_timeout: int = 10,
        query_timeout: int = 60,
    ) -> None:
        self._conn_str = conn_str
        self._login_timeout = int(login_timeout)
        self._query_timeout = int(query_timeout)

    # ----- factory desde Flask config -----
    @classmethod
    def from_flask_config(cls, config) -> "SqlServerTwinsSource":
        if not config.get("MSSQL_SERVER") or not config.get("MSSQL_UID"):
            raise RuntimeError(
                "SQL Server origen no esta configurado (MSSQL_SERVER/MSSQL_UID vacios)."
            )
        cfg = {
            "MSSQL_DRIVER": config["MSSQL_DRIVER"],
            "MSSQL_SERVER": config["MSSQL_SERVER"],
            "MSSQL_PORT": config["MSSQL_PORT"],
            "MSSQL_DATABASE": config["MSSQL_DATABASE"],
            "MSSQL_UID": config["MSSQL_UID"],
            "MSSQL_PWD": config["MSSQL_PWD"],
            "MSSQL_ENCRYPT": config["MSSQL_ENCRYPT"],
            "MSSQL_TRUST_SERVER_CERTIFICATE": config["MSSQL_TRUST_SERVER_CERTIFICATE"],
        }
        return cls(
            conn_str=_build_conn_str(cfg),
            login_timeout=config["MSSQL_LOGIN_TIMEOUT"],
            query_timeout=config["MSSQL_QUERY_TIMEOUT"],
        )

    # ----- infra interna -----
    @contextmanager
    def _connect(self) -> Iterator[Any]:
        try:
            import pyodbc  # import diferido: pyodbc puede no estar instalado en dev/CI
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "pyodbc no esta instalado. Agregalo a requirements para usar la fuente real."
            ) from exc

        pyodbc.pooling = False
        conn = pyodbc.connect(self._conn_str, timeout=self._login_timeout, readonly=True)
        try:
            conn.autocommit = True  # solo lectura, no abrimos transacciones implicitas
            yield conn
        finally:
            try:
                conn.close()
            except Exception:  # pragma: no cover
                logger.exception("Error cerrando conexion SQL Server")

    def _query(self, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        _assert_select(sql)
        with self._connect() as conn:
            cursor = conn.cursor()
            # cursor.timeout = self._query_timeout
            cursor.execute(sql, params)
            cols = [c[0] for c in cursor.description]
            return [dict(zip(cols, row)) for row in cursor.fetchall()]

    # ----- contrato TwinsSource -----
    def fetch_mercaderias(self) -> Iterable[dict[str, Any]]:
        sql = """
            SELECT
                m.Id            AS twins_id,
                m.sCodigo       AS codigo,
                m.sDescripcion  AS descripcion
            FROM configuracion.Mercaderias m
        """
        rows = self._query(sql)
        _log_result("fetch_mercaderias", len(rows))
        return rows

    def fetch_operarios(self) -> Iterable[dict[str, Any]]:
        # En Twins los operarios suelen vivir en configuracion.Usuarios.
        # Si en el cliente real es otra tabla, alcanza con tocar este SELECT.
        sql = """
            SELECT
                u.Id            AS twins_id,
                u.sCodigo       AS codigo,
                u.sDescripcion  AS descripcion
            FROM configuracion.Usuarios u
        """
        rows = self._query(sql)
        _log_result("fetch_operarios", len(rows))
        return rows

    def fetch_tropas(self, desde: date, hasta: date) -> Iterable[dict[str, Any]]:
        hasta_excl = hasta + timedelta(days=1)

        # Diagnóstico: máximo disponible en ambas columnas de fecha relevantes.
        diag = self._query(
            "SELECT"
            " MAX(CONVERT(date, df.dFechaFaena)) AS max_fae,"
            " MAX(CONVERT(date, mv.dFecha)) AS max_mv"
            " FROM movimientos.Faena fae WITH (NOLOCK)"
            " JOIN movimientos.DatosFrigo df WITH (NOLOCK)"
            "   ON df.Identificador_Id = fae.Identificador_Id AND df.bActivo = 1"
            " JOIN movimientos.Movimientos mv WITH (NOLOCK)"
            "   ON mv.Identificador_Id = fae.Identificador_Id AND mv.bEntrada = 0"
            " WHERE fae.bActivo = 1"
        )
        if diag:
            logger.warning(
                "[ETL-source] fetch_tropas | rango pedido: %s\u2192%s"
                " | MAX dFechaFaena en DatosFrigo: %s"
                " | MAX dFecha en Movimientos: %s",
                desde, hasta, diag[0].get("max_fae"), diag[0].get("max_mv"),
            )

        # Path 1: Faena + DatosFrigo (eje df.dFechaFaena) con LEFT JOINs para
        # toda la cadena hacienda.  Idéntico al fallback de _fetch_cabezas_por_usuario
        # en appReferencia.py: si fae.ListaDetalle_Id es NULL, igual devuelve la fila
        # con campos hacienda en NULL en vez de eliminarla con INNER JOIN.
        sql_datosfigo = """
            SELECT
                ih.Id                           AS twins_ingreso_hacienda_id,
                ihst.Id                         AS twins_subtropa_id,
                ihstd.Id                        AS twins_subtropa_detalle_id,
                fae.ListaDetalle_Id             AS twins_lista_detalle_id,
                CAST(ih.iTropa AS varchar(30))  AS numero_tropa,
                CAST(ihst.Id AS varchar(30))    AS numero_subtropa,
                NULL                            AS cabezas_declaradas,
                CONVERT(date, df.dFechaFaena)   AS fecha_ingreso,
                NULL                            AS proveedor_codigo,
                NULL                            AS proveedor_nombre
            FROM movimientos.Faena fae WITH (NOLOCK)
            JOIN movimientos.DatosFrigo df WITH (NOLOCK)
              ON df.Identificador_Id = fae.Identificador_Id
             AND df.bActivo = 1
            LEFT JOIN hacienda.ListaDetalle ld WITH (NOLOCK)
              ON ld.Id = fae.ListaDetalle_Id
            LEFT JOIN hacienda.IngresoHaciendaSubTropaDetalle ihstd WITH (NOLOCK)
              ON ihstd.Id = ld.IngresoHaciendaSubTropaDetalle_Id
            LEFT JOIN hacienda.IngresoHaciendaSubTropa ihst WITH (NOLOCK)
              ON ihst.Id = ihstd.IngresoHaciendaSubTropa_Id
            LEFT JOIN hacienda.IngresoHacienda ih WITH (NOLOCK)
              ON ih.Id = ihst.IngresoHacienda_Id
            WHERE fae.bActivo = 1
              AND df.dFechaFaena >= ? AND df.dFechaFaena < ?
        """
        rows = self._query(sql_datosfigo, (desde, hasta_excl))
        _log_result("fetch_tropas[df.dFechaFaena]", len(rows), desde, hasta)
        if rows:
            return rows

        # Path 2 (fallback): usa mv.dFecha como eje.
        # Idéntico al fallback de _fetch_cabezas_por_usuario en appReferencia.py:
        # Movimientos → Salidas (INNER) → Faena (LEFT) → cadena hacienda (LEFT).
        # Cubre el caso en que DatosFrigo no tiene filas en el rango pero
        # Movimientos/Salidas sí.
        logger.warning(
            "[ETL-source] fetch_tropas | df.dFechaFaena dio 0 filas para %s\u2192%s."
            " Probando fallback por mv.dFecha.",
            desde, hasta,
        )
        sql_mv = """
            SELECT DISTINCT
                ih.Id                           AS twins_ingreso_hacienda_id,
                ihst.Id                         AS twins_subtropa_id,
                ihstd.Id                        AS twins_subtropa_detalle_id,
                fae.ListaDetalle_Id             AS twins_lista_detalle_id,
                CAST(ih.iTropa AS varchar(30))  AS numero_tropa,
                CAST(ihst.Id AS varchar(30))    AS numero_subtropa,
                NULL                            AS cabezas_declaradas,
                CONVERT(date, mv.dFecha)        AS fecha_ingreso,
                NULL                            AS proveedor_codigo,
                NULL                            AS proveedor_nombre
            FROM movimientos.Movimientos mv WITH (NOLOCK)
            JOIN movimientos.Salidas s WITH (NOLOCK)
              ON s.Identificador_Id = mv.Identificador_Id
             AND s.bActivo = 1
             AND s.bEliminado = 0
            LEFT JOIN movimientos.Faena fae WITH (NOLOCK)
              ON fae.Identificador_Id = s.Identificador_Id
             AND fae.bActivo = 1
            LEFT JOIN hacienda.ListaDetalle ld WITH (NOLOCK)
              ON ld.Id = fae.ListaDetalle_Id
            LEFT JOIN hacienda.IngresoHaciendaSubTropaDetalle ihstd WITH (NOLOCK)
              ON ihstd.Id = ld.IngresoHaciendaSubTropaDetalle_Id
            LEFT JOIN hacienda.IngresoHaciendaSubTropa ihst WITH (NOLOCK)
              ON ihst.Id = ihstd.IngresoHaciendaSubTropa_Id
            LEFT JOIN hacienda.IngresoHacienda ih WITH (NOLOCK)
              ON ih.Id = ihst.IngresoHacienda_Id
            WHERE mv.bEntrada = 0
              AND mv.dFecha >= ? AND mv.dFecha < ?
        """
        rows_mv = self._query(sql_mv, (desde, hasta_excl))
        _log_result("fetch_tropas[mv.dFecha]", len(rows_mv), desde, hasta)
        return rows_mv

    def fetch_movimientos(self, desde: date, hasta: date) -> Iterable[dict[str, Any]]:
        # mv.dFecha: se filtra con >= / < para evitar CONVERT en columna.
        hasta_excl = hasta + timedelta(days=1)
        sql = """
            SELECT
                mv.Id                       AS twins_movimiento_id,
                mv.Identificador_Id         AS twins_identificador_id,
                CONVERT(date, mv.dFecha)    AS fecha_movimiento,
                mv.dtCreado                 AS fecha_creacion,
                mv.bEntrada                 AS es_entrada
            FROM movimientos.Movimientos mv
            WHERE mv.dFecha >= ? AND mv.dFecha < ?
        """
        rows = self._query(sql, (desde, hasta_excl))
        _log_result("fetch_movimientos", len(rows), desde, hasta)
        return rows

    def fetch_faena(self, desde: date, hasta: date) -> Iterable[dict[str, Any]]:
        hasta_excl = hasta + timedelta(days=1)

        # Diagnóstico: máximo disponible en ambas columnas de fecha relevantes.
        diag = self._query(
            "SELECT"
            " MAX(CONVERT(date, df.dFechaFaena)) AS max_fae,"
            " MAX(CONVERT(date, mv.dFecha)) AS max_mv"
            " FROM movimientos.Faena fae WITH (NOLOCK)"
            " JOIN movimientos.DatosFrigo df WITH (NOLOCK)"
            "   ON df.Identificador_Id = fae.Identificador_Id AND df.bActivo = 1"
            " JOIN movimientos.Movimientos mv WITH (NOLOCK)"
            "   ON mv.Identificador_Id = fae.Identificador_Id AND mv.bEntrada = 0"
            " WHERE fae.bActivo = 1"
        )
        if diag:
            logger.warning(
                "[ETL-source] fetch_faena | rango pedido: %s\u2192%s"
                " | MAX dFechaFaena: %s | MAX dFecha (mv): %s",
                desde, hasta, diag[0].get("max_fae"), diag[0].get("max_mv"),
            )

        # Path primario: Faena + DatosFrigo, filtrado por dFechaFaena.
        # Sigue exactamente la lógica de _fetch_faena_totals en appReferencia.py.
        sql_datosfigo = """
            SELECT
                fae.Identificador_Id            AS twins_faena_id,
                fae.Identificador_Id            AS twins_identificador_id,
                fae.ListaDetalle_Id             AS twins_lista_detalle_id,
                NULL                            AS twins_operario_id,
                CONVERT(date, df.dFechaFaena)   AS fecha_faena,
                1                               AS cabezas,
                NULL                            AS kg_estimados,
                fae.bActivo                     AS activa
            FROM movimientos.Faena fae WITH (NOLOCK)
            JOIN movimientos.DatosFrigo df WITH (NOLOCK)
              ON df.Identificador_Id = fae.Identificador_Id
             AND df.bActivo = 1
            WHERE fae.bActivo = 1
              AND df.dFechaFaena >= ? AND df.dFechaFaena < ?
        """
        rows = self._query(sql_datosfigo, (desde, hasta_excl))
        _log_result("fetch_faena[df.dFechaFaena]", len(rows), desde, hasta)
        if rows:
            return rows

        # Fallback: usa mv.dFecha como eje (Movimientos bEntrada=0 + Faena LEFT JOIN).
        # Cubre el caso en que DatosFrigo no tiene registros en el rango solicitado
        # pero Movimientos/Faena sí, situación que ocurre cuando dFechaFaena y dFecha
        # no caen en la misma ventana temporal.
        logger.warning(
            "[ETL-source] fetch_faena | df.dFechaFaena dio 0 filas para %s\u2192%s."
            " Probando fallback por mv.dFecha.",
            desde, hasta,
        )
        sql_mv = """
            SELECT DISTINCT
                fae.Identificador_Id            AS twins_faena_id,
                fae.Identificador_Id            AS twins_identificador_id,
                fae.ListaDetalle_Id             AS twins_lista_detalle_id,
                NULL                            AS twins_operario_id,
                CONVERT(date, mv.dFecha)        AS fecha_faena,
                1                               AS cabezas,
                NULL                            AS kg_estimados,
                fae.bActivo                     AS activa
            FROM movimientos.Movimientos mv WITH (NOLOCK)
            JOIN movimientos.Faena fae WITH (NOLOCK)
              ON fae.Identificador_Id = mv.Identificador_Id
             AND fae.bActivo = 1
            WHERE mv.bEntrada = 0
              AND mv.dFecha >= ? AND mv.dFecha < ?
        """
        rows_mv = self._query(sql_mv, (desde, hasta_excl))
        _log_result("fetch_faena[mv.dFecha]", len(rows_mv), desde, hasta)
        return rows_mv

    def fetch_salidas(self, desde: date, hasta: date) -> Iterable[dict[str, Any]]:
        hasta_excl = hasta + timedelta(days=1)

        # Diagnóstico: máximo dFecha disponible en Movimientos (bEntrada=0).
        diag = self._query(
            "SELECT MAX(CONVERT(date, mv.dFecha)) AS max_mv"
            " FROM movimientos.Movimientos mv WITH (NOLOCK)"
            " WHERE mv.bEntrada = 0"
        )
        if diag:
            logger.warning(
                "[ETL-source] fetch_salidas | rango pedido: %s\u2192%s"
                " | MAX dFecha en Movimientos (bEntrada=0): %s",
                desde, hasta, diag[0].get("max_mv"),
            )

        # Path: Movimientos → Salidas → Banderitas (LEFT).
        # Idéntico a _fetch_mediares_payload / timeseries en appReferencia.py.
        # Join desde Movimientos (no desde Salidas) para que el índice sobre
        # mv.dFecha sea efectivo, igual que en la referencia.
        sql = """
            SELECT
                s.Movimiento_Id              AS twins_movimiento_id,
                mv.Identificador_Id          AS twins_identificador_id,
                s.Mercaderia_Id              AS twins_mercaderia_id,
                s.nCantidad                  AS cantidad,
                s.iPeso                      AS peso_gr,
                s.bActivo                    AS activa,
                s.bEliminado                 AS eliminada,
                COALESCE(
                    NULLIF(LTRIM(RTRIM(b.sCodBar)), ''),
                    CONCAT('ID:', CAST(s.Identificador_Id AS varchar(30)))
                )                            AS dedup_key,
                CONVERT(date, mv.dFecha)     AS fecha_emision,
                mv.dtCreado                  AS fecha_creacion,
                NULL                         AS twins_operario_id
            FROM movimientos.Movimientos mv WITH (NOLOCK)
            JOIN movimientos.Salidas s WITH (NOLOCK)
              ON s.Movimiento_Id = mv.Id
            LEFT JOIN movimientos.Banderitas b WITH (NOLOCK)
              ON b.Identificador_Id = s.Identificador_Id
             AND b.Movimiento_Id = s.Movimiento_Id
             AND b.bActivo = 1
            WHERE mv.bEntrada = 0
              AND s.bActivo = 1
              AND s.bEliminado = 0
              AND mv.dFecha >= ? AND mv.dFecha < ?
        """
        rows = self._query(sql, (desde, hasta_excl))
        _log_result("fetch_salidas", len(rows), desde, hasta)
        return rows
