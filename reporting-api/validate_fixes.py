"""Script de validación post-fix.

Ejecuta el ETL completo para el caso de comparación (faena 2025-01-07 /
producción 2025-01-08), luego imprime las secciones clave del reporte
DDJJ_MENUDENCIAS para contrastar contra el CSV de referencia.

Uso desde reporting-api/:
    python validate_fixes.py [--dry-run]

  --dry-run  Sólo consulta las vistas (sin re-ejecutar el ETL).
             Útil si el ETL ya corrió y sólo querés ver el estado actual.
"""
from __future__ import annotations

import sys
from datetime import date

from dotenv import load_dotenv

load_dotenv()

DESDE = date(2025, 1, 7)
HASTA = date(2025, 1, 8)
FECHA_FAENA = date(2025, 1, 7)
FECHA_PROD = date(2025, 1, 8)
PRODUCTO_CLAVE = "IBMCFE030"

# Valores de referencia del CSV de comparación (valores INCORRECTOS del sistema viejo)
REF_CAJAS_WRONG = 3210
REF_KG_WRONG = 2847.390
# Valores esperados correctos (produccion 2025-01-08, faena 2025-01-07)
REF_CAJAS_OK = 24
REF_KG_OK = 313.95


def _run_etl(app):
    """Ejecuta el ETL usando SQL Server real para el rango DESDE→HASTA."""
    from app.services.etl.runner import run_etl
    from app.services.etl.sources.sql_server import SqlServerTwinsSource
    from flask import current_app

    with app.app_context():
        cfg = current_app.config
        if not (cfg.get("MSSQL_SERVER") or "").strip():
            print("[!] MSSQL_SERVER no configurado — imposible conectar a Twins.")
            print("    Asegurate de tener el .env con las credenciales de SQL Server.")
            sys.exit(1)

        print(f"Conectando a {cfg['MSSQL_SERVER']} / {cfg['MSSQL_DATABASE']} …")
        try:
            source = SqlServerTwinsSource.from_flask_config(cfg)
        except Exception as exc:
            print(f"[!] Error al crear SqlServerTwinsSource: {exc}")
            sys.exit(1)

        print(f"Ejecutando ETL: {DESDE} → {HASTA} …\n")
        try:
            resumen = run_etl(
                source=source,
                desde=DESDE,
                hasta=HASTA,
                origen="TwinsDbQuatro045",
            )
        except Exception as exc:
            print(f"[!] ETL falló: {exc}")
            sys.exit(1)

        print(f"ETL finalizado — ejecucion_id={resumen.ejecucion_id}  estado={resumen.estado}")
        for paso in resumen.pasos:
            ok = paso.filas_insertadas
            err = paso.filas_descartadas
            print(f"  {paso.tabla_destino:<30}  +{ok}  err={err}")
            if paso.errores:
                for pk, msg in paso.errores[:3]:
                    print(f"    ⚠  {pk}: {msg}")
                if len(paso.errores) > 3:
                    print(f"    … y {len(paso.errores) - 3} más")
        print()


def _print_report(app):
    """Consulta las MVs y muestra las secciones relevantes del reporte."""
    from sqlalchemy import text
    from app.extensions import db

    with app.app_context():
        # ------------------------------------------------------------------
        # 1. Tropas
        # ------------------------------------------------------------------
        rows_tropas = db.session.execute(
            text(
                "SELECT numero_tropa, cabezas "
                "FROM reporting.mv_tropas_por_faena_diaria "
                "WHERE fecha_faena = :f "
                "ORDER BY numero_tropa"
            ),
            {"f": FECHA_FAENA},
        ).fetchall()

        print("=" * 60)
        print(f"TROPAS (fecha_faena={FECHA_FAENA})")
        print("=" * 60)
        if rows_tropas:
            for r in rows_tropas:
                print(f"  Tropa {r[0]:<12}  medias={r[1]}")
            # Mostrar cuántas tropas y si los números parecen correctos
            primeros = [r[0] for r in rows_tropas[:5]]
            son_secuenciales = all(t.isdigit() and int(t) < 20000 for t in primeros)
            if son_secuenciales:
                print("\n  [!] Los números de tropa parecen IDs de BD (ej. 16161).")
                print("      Verificar que nNroTropa existe en IngresoHacienda.")
            else:
                print(f"\n  [OK] {len(rows_tropas)} tropas con números reales.")
        else:
            print("  (sin filas — la MV no tiene datos para esta fecha_faena)")
        print()

        # ------------------------------------------------------------------
        # 2. Faena / cabezas
        # ------------------------------------------------------------------
        row_faena = db.session.execute(
            text(
                "SELECT cabezas FROM reporting.mv_faena_diaria "
                "WHERE fecha_faena = :f"
            ),
            {"f": FECHA_FAENA},
        ).fetchone()

        medias = row_faena[0] if row_faena else 0
        cabezas = float(medias) / 2
        print(f"CABEZAS (medias={medias})  →  cabezas={cabezas}")
        print(f"  Referencia: 548.0  |  Actual: {cabezas}")
        print()

        # ------------------------------------------------------------------
        # 3. Producción de menudencias
        # ------------------------------------------------------------------
        rows_prod = db.session.execute(
            text(
                "SELECT mercaderia_codigo, mercaderia_descripcion, "
                "       SUM(cajas)::numeric(18,3) AS cajas, "
                "       SUM(kg_neto)::numeric(18,3) AS kg "
                "FROM reporting.mv_ddjj_menudencias_diaria "
                "WHERE fecha_faena = :f "
                "  AND categoria = 'MENUDENCIA' "
                "GROUP BY mercaderia_codigo, mercaderia_descripcion "
                "ORDER BY mercaderia_codigo"
            ),
            {"f": FECHA_PROD},
        ).fetchall()

        print("=" * 60)
        print(f"PRODUCCIÓN (fecha_emision={FECHA_PROD}  — fecha_faena en Twins: {FECHA_FAENA})")
        print("=" * 60)
        print(f"  {'Código':<14} {'Cajas':>10} {'Kg':>12}  {'⚑' if True else ''}")
        print(f"  {'-'*14} {'-'*10} {'-'*12}")
        total_cajas = 0
        total_kg = 0
        for r in rows_prod:
            codigo, desc, cajas, kg = r[0], r[1], float(r[2]), float(r[3])
            total_cajas += cajas
            total_kg += kg
            marker = " ← IBMCFE030" if codigo == PRODUCTO_CLAVE else ""
            print(f"  {codigo:<14} {cajas:>10.3f} {kg:>12.3f}{marker}")
        print(f"  {'TOTAL':<14} {total_cajas:>10.3f} {total_kg:>12.3f}")
        print()

        # ------------------------------------------------------------------
        # 4. Validación específica IBMCFE030
        # ------------------------------------------------------------------
        row_clave = next((r for r in rows_prod if r[0] == PRODUCTO_CLAVE), None)
        print("=" * 60)
        print(f"VALIDACIÓN {PRODUCTO_CLAVE} (Lengua Corte Suizo)")
        print("=" * 60)
        if row_clave:
            cajas = float(row_clave[2])
            kg = float(row_clave[3])
            print(f"  Cajas actuales   : {cajas:.3f}")
            print(f"  Cajas esperadas  : {REF_CAJAS_OK:.3f}")
            print(f"  Cajas incorrectas: {REF_CAJAS_WRONG:.3f}  (valor sistema viejo)")
            print(f"  Kg actuales      : {kg:.3f}")
            print(f"  Kg esperados     : {REF_KG_OK:.3f}")
            print(f"  Kg incorrectos   : {REF_KG_WRONG:.3f}  (valor sistema viejo)")
            cajas_ok = abs(cajas - REF_CAJAS_OK) <= 1
            kg_ok    = abs(kg - REF_KG_OK) < 0.1
            if cajas_ok and kg_ok:
                print("  [OK] Cajas y Kg coinciden con el valor funcional esperado.")
            else:
                diff_c = cajas - REF_CAJAS_OK
                diff_k = kg - REF_KG_OK
                print(f"  [!]  Desvío: cajas {diff_c:+.1f}  |  kg {diff_k:+.3f}")
        else:
            print(f"  (producto {PRODUCTO_CLAVE} no encontrado en la MV para {FECHA_PROD})")
        print()


def main():
    dry_run = "--dry-run" in sys.argv

    from app import create_app
    app = create_app()

    if not dry_run:
        _run_etl(app)
    else:
        print("[dry-run] Omitiendo ETL — sólo consultando vistas actuales.\n")

    _print_report(app)


if __name__ == "__main__":
    main()
