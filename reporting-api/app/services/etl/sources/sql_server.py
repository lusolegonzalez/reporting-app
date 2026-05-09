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
from datetime import date
from typing import Any, Iterable, Iterator

logger = logging.getLogger(__name__)


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
            cursor.timeout = self._query_timeout
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
        return self._query(sql)

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
        return self._query(sql)

    def fetch_tropas(self, desde: date, hasta: date) -> Iterable[dict[str, Any]]:
        sql = """
            SELECT
                ih.Id                                   AS twins_ingreso_hacienda_id,
                ihst.Id                                 AS twins_subtropa_id,
                ihstd.Id                                AS twins_subtropa_detalle_id,
                ld.Id                                   AS twins_lista_detalle_id,
                ih.sNumeroTropa                         AS numero_tropa,
                ihst.sNumero                            AS numero_subtropa,
                ih.nCabezas                             AS cabezas_declaradas,
                CONVERT(date, ih.dFechaIngreso)         AS fecha_ingreso,
                prov.sCodigo                            AS proveedor_codigo,
                prov.sDescripcion                       AS proveedor_nombre
            FROM hacienda.IngresoHacienda ih
            LEFT JOIN hacienda.IngresoHaciendaSubTropa        ihst  ON ihst.IngresoHacienda_Id = ih.Id
            LEFT JOIN hacienda.IngresoHaciendaSubTropaDetalle ihstd ON ihstd.IngresoHaciendaSubTropa_Id = ihst.Id
            LEFT JOIN hacienda.ListaDetalle                   ld    ON ld.IngresoHaciendaSubTropaDetalle_Id = ihstd.Id
            LEFT JOIN configuracion.Proveedores               prov  ON prov.Id = ih.Proveedor_Id
            WHERE CONVERT(date, ih.dFechaIngreso) BETWEEN ? AND ?
        """
        return self._query(sql, (desde, hasta))

    def fetch_movimientos(self, desde: date, hasta: date) -> Iterable[dict[str, Any]]:
        sql = """
            SELECT
                mv.Id                       AS twins_movimiento_id,
                mv.Identificador_Id         AS twins_identificador_id,
                CONVERT(date, mv.dFecha)    AS fecha_movimiento,
                mv.dtCreado                 AS fecha_creacion,
                mv.bEntrada                 AS es_entrada
            FROM movimientos.Movimientos mv
            WHERE mv.dFecha BETWEEN ? AND ?
        """
        return self._query(sql, (desde, hasta))

    def fetch_faena(self, desde: date, hasta: date) -> Iterable[dict[str, Any]]:
        sql = """
            SELECT
                fae.Id                          AS twins_faena_id,
                fae.Identificador_Id            AS twins_identificador_id,
                fae.ListaDetalle_Id             AS twins_lista_detalle_id,
                fae.Operario_Id                 AS twins_operario_id,
                CONVERT(date, df.dFechaFaena)   AS fecha_faena,
                fae.nCabezas                    AS cabezas,
                fae.iPesoEstimado               AS kg_estimados,
                fae.bActivo                     AS activa
            FROM movimientos.Faena fae
            JOIN movimientos.DatosFrigo df
              ON df.Identificador_Id = fae.Identificador_Id
             AND df.bActivo = 1
            WHERE CONVERT(date, df.dFechaFaena) BETWEEN ? AND ?
        """
        return self._query(sql, (desde, hasta))

    def fetch_salidas(self, desde: date, hasta: date) -> Iterable[dict[str, Any]]:
        sql = """
            SELECT
                s.Movimiento_Id              AS twins_movimiento_id,
                s.Identificador_Id           AS twins_identificador_id,
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
                fae.Operario_Id              AS twins_operario_id
            FROM movimientos.Salidas s
            JOIN movimientos.Movimientos mv
              ON mv.Identificador_Id = s.Identificador_Id
            LEFT JOIN movimientos.Banderitas b
              ON b.Identificador_Id = s.Identificador_Id
             AND b.Movimiento_Id   = s.Movimiento_Id
             AND b.bActivo = 1
            LEFT JOIN movimientos.Faena fae
              ON fae.Identificador_Id = s.Identificador_Id
             AND fae.bActivo = 1
            WHERE mv.bEntrada = 0
              AND CONVERT(date, mv.dFecha) BETWEEN ? AND ?
        """
        return self._query(sql, (desde, hasta))
