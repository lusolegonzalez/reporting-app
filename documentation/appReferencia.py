#!/usr/bin/env python3"""Aplicación Flask mínima para el dashboard produccion-dia.

Este proyecto quedó reducido a un único dashboard operativo para facilitarel mantenimiento y el onboarding de nuevos desarrolladores."""

from future import annotations

import osfrom dataclasses import dataclassfrom datetime import date, datetime, timedeltafrom typing import Any

import pyodbcfrom dotenv import load_dotenvfrom flask import Flask, jsonify, render_template, request

load_dotenv()

app = Flask(name)

@dataclass(frozen=True)class SqlServerConfig:"""Configuración necesaria para conectarse a SQL Server."""

server: str
database: str
uid: str
pwd: str
port: int = 1433

def _build_sql_server_conn_str(config: SqlServerConfig) -> str:"""Construye un connection string compatible con Windows y Linux."""driver = os.getenv("MSSQL_DRIVER") or ("{ODBC Driver 18 for SQL Server}" if os.name == "nt" else "{FreeTDS}")driver_lower = driver.lower()

if os.name == "nt":
    return (
        f"DRIVER={driver};"
        f"SERVER={config.server},{config.port};"
        f"DATABASE={config.database};"
        f"UID={config.uid};PWD={config.pwd};"
        "Encrypt=no;"
        "TrustServerCertificate=yes;"
    )

if "odbc driver 18 for sql server" in driver_lower or "odbc driver 17 for sql server" in driver_lower:
    return (
        f"DRIVER={driver};"
        f"SERVER={config.server},{config.port};"
        f"DATABASE={config.database};"
        f"UID={config.uid};PWD={config.pwd};"
        "Encrypt=yes;"
        "TrustServerCertificate=yes;"
    )

return (
    f"DRIVER={driver};"
    f"SERVER={config.server};PORT={config.port};"
    f"DATABASE={config.database};"
    f"UID={config.uid};PWD={config.pwd};"
    "TDS_Version=8.0;"
)

QUATRO045_CONN_STR = _build_sql_server_conn_str(SqlServerConfig(server=os.getenv("QUATRO045_SERVER", ""),database=os.getenv("QUATRO045_DB", "TwinsDbQuatro045"),uid=os.getenv("QUATRO045_UID", ""),pwd=os.getenv("QUATRO045_PWD", ""),))

def _parse_iso_date(raw_value: str | None) -> date | None:"""Convierte YYYY-MM-DD a date."""value = (raw_value or "").strip()if not value:return Nonetry:return datetime.strptime(value, "%Y-%m-%d").date()except ValueError:return None

def _get_requested_date() -> date:"""Toma la fecha del query string o usa el día actual."""raw_date = request.args.get("fecha")if not raw_date:return date.today()

parsed = _parse_iso_date(raw_date)
if parsed is None:
    raise ValueError("Fecha inválida (use YYYY-MM-DD)")
return parsed

def _get_quatro045_connection() -> pyodbc.Connection:"""Abre una conexión nueva para evitar problemas de pooling compartido."""pyodbc.pooling = Falsereturn pyodbc.connect(QUATRO045_CONN_STR, timeout=8)

def _query_dicts(cursor: pyodbc.Cursor, sql: str, params: tuple[Any, ...]) -> list[dict[str, Any]]:"""Ejecuta una consulta y devuelve filas como diccionarios."""cursor.execute(sql, params)columns = [column[0] for column in cursor.description]return [dict(zip(columns, row)) for row in cursor.fetchall()]

def _normalize_emision_rows(raw_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:"""Adapta las filas de emisión al formato que usa la tabla del frontend."""normalized_rows: list[dict[str, Any]] = []

for row in raw_rows:
    cajas = float(row.get("Cajas") or 0)
    kg = float(row.get("Kg") or 0)
    promedio = (kg / cajas) if cajas > 0 else 0.0

    normalized_rows.append(
        {
            "codigo": (row.get("Codigo") or "").strip(),
            "descripcion": (row.get("Descripcion") or "").strip(),
            "prog": 0.0,
            "emitidos": round(kg, 3),
            "pendiente": 0.0,
            "cajas": int(round(cajas, 0)),
            "promedio_por_caja": round(promedio, 3),
            "origen": "TwinsDbQuatro045",
        }
    )

return normalized_rows

def _fetch_mediares_payload(fecha: date) -> dict[str, Any]:"""Obtiene la emisión de MEDIA RES y su serie horaria para el dashboard."""starts_media_res = "UPPER(LTRIM(RTRIM(ISNULL(m.sDescripcion,'')))) LIKE 'MEDIA RES%'"

sql_rows = f"""
    SELECT
      mv.dFecha                          AS FechaEmision,
      s.Mercaderia_Id,
      m.sCodigo                          AS Codigo,
      m.sDescripcion                     AS Descripcion,
      SUM(CAST(s.nCantidad AS float))    AS Cajas,
      SUM(CAST(s.iPeso AS float))/1000.0 AS Kg
    FROM movimientos.Movimientos mv
    JOIN movimientos.Salidas s
      ON s.Identificador_Id = mv.Identificador_Id
    LEFT JOIN configuracion.Mercaderias m
      ON m.Id = s.Mercaderia_Id
    WHERE mv.bEntrada = 0
      AND s.bActivo = 1
      AND s.bEliminado = 0
      AND mv.dFecha = ?
      AND {starts_media_res}
    GROUP BY mv.dFecha, s.Mercaderia_Id, m.sCodigo, m.sDescripcion
    ORDER BY Kg DESC;
"""

sql_timeseries = f"""
    ;WITH base AS (
      SELECT
        mv.dtCreado AS dtCreado,
        s.Movimiento_Id,
        s.Identificador_Id,
        CAST(s.nCantidad AS float) AS nCantidad,
        CAST(s.iPeso AS float)/1000.0 AS Kg,
        ISNULL(NULLIF(LTRIM(RTRIM(u.sCodigo)), ''), 'SIN') AS ClienteCod,
        ISNULL(NULLIF(LTRIM(RTRIM(u.sDescripcion)), ''), 'SIN') AS ClienteNombre,
        COALESCE(
          NULLIF(LTRIM(RTRIM(b.sCodBar)), ''),
          CONCAT('ID:', CAST(s.Identificador_Id AS varchar(30)))
        ) AS dedup_key
      FROM movimientos.Movimientos mv
      JOIN movimientos.Salidas s
        ON s.Identificador_Id = mv.Identificador_Id
      LEFT JOIN movimientos.Banderitas b
        ON b.Identificador_Id = s.Identificador_Id
       AND b.Movimiento_Id = s.Movimiento_Id
       AND b.bActivo = 1
      LEFT JOIN configuracion.Mercaderias m
        ON m.Id = s.Mercaderia_Id
      JOIN movimientos.Faena fae
        ON fae.Identificador_Id = s.Identificador_Id
       AND fae.bActivo = 1
      JOIN movimientos.DatosFrigo df
        ON df.Identificador_Id = fae.Identificador_Id
       AND df.bActivo = 1
       AND CONVERT(date, df.dFechaFaena) = ?
      LEFT JOIN hacienda.ListaDetalle ld
        ON ld.Id = fae.ListaDetalle_Id
      LEFT JOIN hacienda.IngresoHaciendaSubTropaDetalle ihstd
        ON ihstd.Id = ld.IngresoHaciendaSubTropaDetalle_Id
      LEFT JOIN hacienda.IngresoHaciendaSubTropa ihst
        ON ihst.Id = ihstd.IngresoHaciendaSubTropa_Id
      LEFT JOIN hacienda.IngresoHacienda ih
        ON ih.Id = ihst.IngresoHacienda_Id
      LEFT JOIN configuracion.Usuarios u
        ON u.Id = ih.Usuario_Id
      WHERE mv.bEntrada = 0
        AND s.bActivo = 1
        AND s.bEliminado = 0
        AND CONVERT(date, mv.dtCreado) = ?
        AND {starts_media_res}
    ),
    dedup AS (
      SELECT
        dtCreado,
        nCantidad,
        Kg,
        ClienteCod,
        ClienteNombre,
        ROW_NUMBER() OVER (
          PARTITION BY dedup_key
          ORDER BY dtCreado ASC, Movimiento_Id ASC
        ) AS rn
      FROM base
    )
    SELECT
      dtCreado,
      nCantidad,
      Kg,
      ClienteCod,
      ClienteNombre
    FROM dedup
    WHERE rn = 1
    ORDER BY dtCreado ASC;
"""

sql_timeseries_fallback = f"""
    ;WITH base AS (
      SELECT
        mv.dtCreado AS dtCreado,
        s.Movimiento_Id,
        s.Identificador_Id,
        CAST(s.nCantidad AS float) AS nCantidad,
        CAST(s.iPeso AS float)/1000.0 AS Kg,
        ISNULL(NULLIF(LTRIM(RTRIM(u.sCodigo)), ''), 'SIN') AS ClienteCod,
        ISNULL(NULLIF(LTRIM(RTRIM(u.sDescripcion)), ''), 'SIN') AS ClienteNombre,
        COALESCE(
          NULLIF(LTRIM(RTRIM(b.sCodBar)), ''),
          CONCAT('ID:', CAST(s.Identificador_Id AS varchar(30)))
        ) AS dedup_key
      FROM movimientos.Movimientos mv
      JOIN movimientos.Salidas s
        ON s.Identificador_Id = mv.Identificador_Id
      LEFT JOIN movimientos.Banderitas b
        ON b.Identificador_Id = s.Identificador_Id
       AND b.Movimiento_Id = s.Movimiento_Id
       AND b.bActivo = 1
      LEFT JOIN configuracion.Mercaderias m
        ON m.Id = s.Mercaderia_Id
      LEFT JOIN movimientos.Faena fae
        ON fae.Identificador_Id = s.Identificador_Id
       AND fae.bActivo = 1
      LEFT JOIN hacienda.ListaDetalle ld
        ON ld.Id = fae.ListaDetalle_Id
      LEFT JOIN hacienda.IngresoHaciendaSubTropaDetalle ihstd
        ON ihstd.Id = ld.IngresoHaciendaSubTropaDetalle_Id
      LEFT JOIN hacienda.IngresoHaciendaSubTropa ihst
        ON ihst.Id = ihstd.IngresoHaciendaSubTropa_Id
      LEFT JOIN hacienda.IngresoHacienda ih
        ON ih.Id = ihst.IngresoHacienda_Id
      LEFT JOIN configuracion.Usuarios u
        ON u.Id = ih.Usuario_Id
      WHERE mv.bEntrada = 0
        AND s.bActivo = 1
        AND s.bEliminado = 0
        AND CONVERT(date, mv.dtCreado) = ?
        AND {starts_media_res}
    ),
    dedup AS (
      SELECT
        dtCreado,
        nCantidad,
        Kg,
        ClienteCod,
        ClienteNombre,
        ROW_NUMBER() OVER (
          PARTITION BY dedup_key
          ORDER BY dtCreado ASC, Movimiento_Id ASC
        ) AS rn
      FROM base
    )
    SELECT
      dtCreado,
      nCantidad,
      Kg,
      ClienteCod,
      ClienteNombre
    FROM dedup
    WHERE rn = 1
    ORDER BY dtCreado ASC;
"""

with _get_quatro045_connection() as connection:
    cursor = connection.cursor()
    raw_rows = _query_dicts(cursor, sql_rows, (fecha,))

    cursor.execute(sql_timeseries, (fecha, fecha))
    raw_timeseries = cursor.fetchall()
    if not raw_timeseries and raw_rows:
        cursor.execute(sql_timeseries_fallback, (fecha,))
        raw_timeseries = cursor.fetchall()

buckets: dict[datetime, dict[str, Any]] = {}
total_mediares = 0.0
total_kg = 0.0

for dt_creado, cantidad, kg, cliente_cod, cliente_nombre in raw_timeseries:
    if dt_creado is None:
        continue

    mediares = float(cantidad or 0.0)
    kg_value = float(kg or 0.0)
    total_mediares += mediares
    total_kg += kg_value

    bucket_dt = dt_creado.replace(minute=(dt_creado.minute // 5) * 5, second=0, microsecond=0)
    bucket = buckets.setdefault(
        bucket_dt,
        {"bucket": bucket_dt, "mediares": 0.0, "kg": 0.0, "clientes": {}},
    )

    bucket["mediares"] += mediares
    bucket["kg"] += kg_value

    client_key = f"{(cliente_cod or 'SIN').strip()}|{(cliente_nombre or 'SIN').strip()}"
    client_agg = bucket["clientes"].setdefault(
        client_key,
        {
            "cod": (cliente_cod or "SIN").strip() or "SIN",
            "nombre": (cliente_nombre or "SIN").strip() or "SIN",
            "mediares": 0.0,
            "kg": 0.0,
        },
    )
    client_agg["mediares"] += mediares
    client_agg["kg"] += kg_value

timeseries: list[dict[str, Any]] = []
for bucket in [buckets[key] for key in sorted(buckets.keys())]:
    dominant_client = None
    if bucket["clientes"]:
        dominant_client = sorted(
            bucket["clientes"].values(),
            key=lambda client: (-float(client["mediares"]), -float(client["kg"]), client["nombre"], client["cod"]),
        )[0]

    mediares_bucket = float(bucket["mediares"])
    kg_bucket = float(bucket["kg"])
    # El frontend grafica velocidad por hora; escalamos el bucket de 5 minutos.
    factor_per_hour = 12.0

    client_code = (dominant_client or {}).get("cod", "SIN")
    client_name = (dominant_client or {}).get("nombre", "SIN")
    client_label = f"{client_code} - {client_name}" if client_code != "SIN" else client_name

    timeseries.append(
        {
            "bucket": bucket["bucket"].isoformat(timespec="minutes"),
            "mediares_hora": round(mediares_bucket * factor_per_hour, 3),
            "cabezas_hora": round((mediares_bucket / 2.0) * factor_per_hour, 3),
            "kg_hora": round(kg_bucket * factor_per_hour, 3),
            "cliente_cod": client_code,
            "cliente": client_name,
            "cliente_label": client_label,
        }
    )

return {
    "base": "TwinsDbQuatro045",
    "rows": raw_rows,
    "timeseries": timeseries,
    "total_mediares": round(total_mediares, 3),
    "total_cabezas": round(total_mediares / 2.0, 3),
    "total_kg": round(total_kg, 3),
}

def _fetch_faena_totals(fecha: date) -> dict[str, Any]:"""Obtiene totales de faena de Quatro045 para los KPIs principales."""next_day = fecha + timedelta(days=1)sql = """SELECTCOUNT(DISTINCT fae.Identificador_Id)         AS MediasFaena,SUM(CAST(sal.iPeso AS float))/1000.0         AS KgFaenaFROM movimientos.Faena fae WITH (NOLOCK)JOIN movimientos.DatosFrigo df WITH (NOLOCK)ON df.Identificador_Id = fae.Identificador_Id AND df.bActivo = 1JOIN movimientos.Salidas sal WITH (NOLOCK)ON sal.Identificador_Id = fae.Identificador_IdAND sal.bActivo = 1AND sal.bEliminado = 0WHERE fae.bActivo = 1AND df.dFechaFaena >= ?AND df.dFechaFaena < ?;"""

sql_fallback = """
    SELECT
      SUM(CAST(sal.nCantidad AS float))            AS MediasFaena,
      SUM(CAST(sal.iPeso AS float))/1000.0         AS KgFaena
    FROM movimientos.Movimientos mv WITH (NOLOCK)
    JOIN movimientos.Salidas sal WITH (NOLOCK)
      ON sal.Identificador_Id = mv.Identificador_Id
     AND sal.bActivo = 1
     AND sal.bEliminado = 0
    LEFT JOIN configuracion.Mercaderias m WITH (NOLOCK)
      ON m.Id = sal.Mercaderia_Id
    WHERE mv.bEntrada = 0
      AND mv.dFecha >= ?
      AND mv.dFecha < ?
      AND UPPER(LTRIM(RTRIM(ISNULL(m.sDescripcion,'')))) LIKE 'MEDIA RES%';
"""

with _get_quatro045_connection() as connection:
    cursor = connection.cursor()
    cursor.execute(sql, (fecha, next_day))
    row = cursor.fetchone()
    total_medias = int((row[0] or 0) if row else 0)
    total_kg = float((row[1] or 0.0) if row else 0.0)
    if total_medias == 0 and total_kg == 0.0:
        cursor.execute(sql_fallback, (fecha, next_day))
        row = cursor.fetchone()
        total_medias = int(round((row[0] or 0) if row else 0))
        total_kg = float((row[1] or 0.0) if row else 0.0)
return {
    "faena_total_medias": total_medias,
    "faena_total_cabezas": total_medias // 2,
    "faena_total_kg": round(total_kg, 3),
}

def _fetch_cabezas_por_usuario(fecha: date) -> dict[str, Any]:"""Agrupa las cabezas faenadas por usuario para el gráfico de barras."""sql = """SELECTISNULL(u.sCodigo, 'SIN')      AS CodUsu,ISNULL(u.sDescripcion, 'SIN') AS Usuario,CAST(COUNT(DISTINCT fae.Identificador_Id) / 2.0 AS int) AS CabezasFROM movimientos.Faena fae WITH (NOLOCK)JOIN movimientos.DatosFrigo df WITH (NOLOCK)ON df.Identificador_Id = fae.Identificador_IdAND df.bActivo = 1JOIN hacienda.ListaDetalle ld WITH (NOLOCK)ON ld.Id = fae.ListaDetalle_IdJOIN hacienda.IngresoHaciendaSubTropaDetalle ihstd WITH (NOLOCK)ON ihstd.Id = ld.IngresoHaciendaSubTropaDetalle_IdJOIN hacienda.IngresoHaciendaSubTropa ihst WITH (NOLOCK)ON ihst.Id = ihstd.IngresoHaciendaSubTropa_IdJOIN hacienda.IngresoHacienda ih WITH (NOLOCK)ON ih.Id = ihst.IngresoHacienda_IdLEFT JOIN configuracion.Usuarios u WITH (NOLOCK)ON u.Id = ih.Usuario_IdWHERE fae.bActivo = 1AND df.dFechaFaena = ?GROUP BY u.sCodigo, u.sDescripcionORDER BY Cabezas DESC;"""

sql_fallback = """
    SELECT
        ISNULL(u.sCodigo, 'SIN')      AS CodUsu,
        ISNULL(u.sDescripcion, 'SIN') AS Usuario,
        CAST(SUM(CAST(s.nCantidad AS float)) / 2.0 AS int) AS Cabezas
    FROM movimientos.Movimientos mv WITH (NOLOCK)
    JOIN movimientos.Salidas s WITH (NOLOCK)
      ON s.Identificador_Id = mv.Identificador_Id
     AND s.bActivo = 1
     AND s.bEliminado = 0
    LEFT JOIN configuracion.Mercaderias m WITH (NOLOCK)
      ON m.Id = s.Mercaderia_Id
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
    LEFT JOIN configuracion.Usuarios u WITH (NOLOCK)
      ON u.Id = ih.Usuario_Id
    WHERE mv.bEntrada = 0
      AND mv.dFecha = ?
      AND UPPER(LTRIM(RTRIM(ISNULL(m.sDescripcion,'')))) LIKE 'MEDIA RES%'
    GROUP BY u.sCodigo, u.sDescripcion
    HAVING SUM(CAST(s.nCantidad AS float)) > 0
    ORDER BY Cabezas DESC;
"""

with _get_quatro045_connection() as connection:
    cursor = connection.cursor()
    rows = _query_dicts(cursor, sql, (fecha,))
    if not rows:
        rows = _query_dicts(cursor, sql_fallback, (fecha,))

total_cabezas = sum(int(row.get("Cabezas") or 0) for row in rows)
return {
    "ok": True,
    "base": "TwinsDbQuatro045",
    "fecha": fecha.isoformat(),
    "total_cabezas": total_cabezas,
    "rows": rows,
}

@app.route("/")@app.route("/produccion-dia")def produccion_dia_page() -> str:"""Renderiza el dashboard principal."""return render_template("ordenes/produccion_dia.html", fecha=date.today().isoformat())

@app.route("/api/quatro045/emision-dia", methods=["GET"])def api_quatro045_emision_dia():"""Endpoint principal del dashboard de producción del día."""try:fecha = _get_requested_date()mediares_payload = _fetch_mediares_payload(fecha)faena_totals = _fetch_faena_totals(fecha)except ValueError as exc:return jsonify({"ok": False, "error": str(exc)}), 400except Exception as exc:app.logger.exception("Error consultando emisión del día")return jsonify({"ok": False, "error": str(exc)}), 500

normalized_rows = _normalize_emision_rows(mediares_payload["rows"])

return jsonify(
    {
        "ok": True,
        "base": "TwinsDbQuatro045",
        "fecha": fecha.isoformat(),
        "rows": normalized_rows,
        "mediares": mediares_payload,
        "emision_rows": mediares_payload["rows"],
        "timeseries": [
            {
                "bucket": point["bucket"],
                "cajas_hora": point["mediares_hora"],
                "kg_hora": point["kg_hora"],
            }
            for point in mediares_payload["timeseries"]
        ],
        **faena_totals,
        "total_cajas": faena_totals["faena_total_medias"],
        "total_cabezas": faena_totals["faena_total_cabezas"],
        "total_kg": faena_totals["faena_total_kg"],
    }
)

@app.route("/api/quatro045/cabezas-por-usuario", methods=["GET"])def api_quatro045_cabezas_por_usuario():"""Endpoint para el gráfico de cabezas por usuario."""try:fecha = _get_requested_date()payload = _fetch_cabezas_por_usuario(fecha)except ValueError as exc:return jsonify({"ok": False, "error": str(exc)}), 400except Exception as exc:app.logger.exception("Error consultando cabezas por usuario")return jsonify({"ok": False, "error": str(exc)}), 500

return jsonify(payload)

@app.route("/healthz", methods=["GET"])def healthcheck():"""Chequeo básico para systemd/Nginx."""return jsonify({"ok": True, "service": "produccion-dia"})

if name == "main":app.run(host="0.0.0.0", port=5000)