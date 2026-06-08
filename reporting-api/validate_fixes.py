"""Script de validación post-fix.

Ejecuta el ETL completo para el caso de comparación (faena 2025-01-07 /
producción 2025-01-08), luego imprime las secciones clave del reporte
DDJJ_MENUDENCIAS y una tabla de diferencias contra el legacy correcto.

Uso desde reporting-api/:
    python validate_fixes.py [--dry-run]

  --dry-run  Sólo consulta las vistas (sin re-ejecutar el ETL).
             Útil si el ETL ya corrió y sólo querés ver el estado actual.

Caso testigo: faena 2025-07-01 / producción 2025-08-01 / 548 cabezas.
Legacy correcto (DDJJ manual julio 2025):
    Total: 984 cajas / 10525.65 kg
"""
from __future__ import annotations

import sys
from datetime import date
from decimal import Decimal

from dotenv import load_dotenv

load_dotenv()

DESDE = date(2025, 7, 1)
HASTA = date(2025, 8, 1)
FECHA_FAENA = date(2025, 7, 1)
FECHA_PROD = date(2025, 8, 1)

CABEZAS_LEGACY = 548.0

# Tabla completa de referencia legacy (código → (cajas, kg_neto)).
# Fuente: DDJJ manual julio 2025, hoja faena 07-01 / producción 08-01.
LEGACY: dict[str, tuple[float, float]] = {
    "IBMCF3010": (1,   20.00),
    "IBMCF3039": (4,   72.00),
    "IBMCF3220": (8,  144.00),
    "IBMCF3230": (7,  140.00),
    "IBMCF3400": (1,   20.00),
    "IBMCFB011": (52, 666.85),
    "IBMCFE010": (18, 194.85),
    "IBMCFE020": (31, 372.00),
    "IBMCFE030": (24, 313.95),
    "IBMCFE041": (19, 190.00),
    "IBMCFE042": (10, 120.00),
    "IBMCFE043": (32, 384.00),
    "IBMCFE060": (13, 156.00),
    "IBMCFE070": (56, 560.00),
    "IBMCFE081": (29, 290.00),
    "IBMCFE100": (10, 100.00),
    "IBMCFE140": (63, 630.00),
    "IBMCFE141": (16, 160.00),
    "IBMCFE180": (11, 110.00),
    "IBMCFE210": (291, 2910.00),
    "IBMCFE240": (29, 290.00),
    "IBMCFE300": (4,   48.00),
    "IBMCFE310": (34, 408.00),
    "IBMCFE320": (4,   48.00),
    "IBMCFE340": (6,   60.00),
    "IBMCFE370": (143, 1430.00),
    "IBMCPE170": (27, 270.00),
    "IBMCPE171": (20, 200.00),
    "IBMCPE179": (1,   18.00),
    "IBMCPE202": (20, 200.00),
}

LEGACY_TOTAL_CAJAS = sum(v[0] for v in LEGACY.values())   # 984
LEGACY_TOTAL_KG    = sum(v[1] for v in LEGACY.values())   # 10525.65

# Tolerancia para comparar kg (diferencias de redondeo son normales).
TOL_KG = 0.10


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

        actual: dict[str, tuple[float, float]] = {
            r[0]: (float(r[2]), float(r[3])) for r in rows_prod
        }

        print("=" * 70)
        print(f"PRODUCCIÓN (fecha_emision={FECHA_PROD} / fecha_faena Twins: {FECHA_FAENA})")
        print("=" * 70)
        print(f"  {'Código':<14} {'Cajas A':>8} {'Kg A':>10} {'Cajas L':>8} {'Kg L':>10}  Estado")
        print(f"  {'-'*14} {'-'*8} {'-'*10} {'-'*8} {'-'*10}  ------")

        total_cajas_a = 0.0
        total_kg_a = 0.0
        codigos_union = sorted(set(actual) | set(LEGACY))
        n_ok = n_diff = n_falta = n_extra = 0

        for cod in codigos_union:
            ca, ka = actual.get(cod, (0.0, 0.0))
            cl, kl = LEGACY.get(cod, (0.0, 0.0))
            total_cajas_a += ca
            total_kg_a += ka

            if cod not in LEGACY:
                estado = "EXTRA"
                n_extra += 1
            elif cod not in actual:
                estado = "FALTA"
                n_falta += 1
            elif abs(ca - cl) <= 1 and abs(ka - kl) <= TOL_KG:
                estado = "OK"
                n_ok += 1
            else:
                estado = f"DIFF  cajas {ca-cl:+.0f} / kg {ka-kl:+.2f}"
                n_diff += 1

            print(f"  {cod:<14} {ca:>8.0f} {ka:>10.2f} {cl:>8.0f} {kl:>10.2f}  {estado}")

        print(f"  {'TOTAL':<14} {total_cajas_a:>8.0f} {total_kg_a:>10.2f} "
              f"{LEGACY_TOTAL_CAJAS:>8.0f} {LEGACY_TOTAL_KG:>10.2f}")
        print()

        # ------------------------------------------------------------------
        # 4. Resumen de diferencias
        # ------------------------------------------------------------------
        print("=" * 70)
        print("RESUMEN DE DIFERENCIAS vs LEGACY")
        print("=" * 70)
        print(f"  Productos OK       : {n_ok}")
        print(f"  Productos con diff : {n_diff}")
        print(f"  Productos faltantes: {n_falta}")
        print(f"  Productos extra    : {n_extra}")
        diff_cajas = total_cajas_a - LEGACY_TOTAL_CAJAS
        diff_kg = total_kg_a - LEGACY_TOTAL_KG
        print(f"  Total cajas  actual={total_cajas_a:.0f}  legacy={LEGACY_TOTAL_CAJAS:.0f}  diff={diff_cajas:+.0f}")
        print(f"  Total kg     actual={total_kg_a:.2f}  legacy={LEGACY_TOTAL_KG:.2f}  diff={diff_kg:+.2f}")
        if n_falta == 0 and n_extra == 0 and n_diff == 0:
            print()
            print("  [OK] Todos los productos coinciden con el legacy.")
        else:
            print()
            print("  [!!] Quedan diferencias respecto al legacy. Ver tabla arriba.")
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
