"""Script de validación post-fix (multi-caso).

Para cada caso testigo ejecuta el ETL (faena+salidas) sobre el rango que
cubre faena y producción, refresca las vistas materializadas y compara la
producción de menudencias contra el legacy DDJJ correcto.

Uso desde reporting-api/:
    python validate_fixes.py [--dry-run]

  --dry-run  Sólo consulta las vistas (sin re-ejecutar el ETL ni refrescar).
             Útil si el ETL ya corrió y sólo querés ver el estado actual.

Casos testigo (faena → producción) y total legacy esperado:
    15-10 : faena 2025-10-15 / prod 2025-10-16 ->   826 cajas /  9055.75 kg
    17-09 : faena 2025-09-17 / prod 2025-09-18 ->  1001 cajas / 10870.51 kg
    21-01 : faena 2025-01-21 / prod 2025-01-22 ->   518 cajas /  5759.55 kg
"""
from __future__ import annotations

import sys
from datetime import date

from dotenv import load_dotenv

load_dotenv()

# Tolerancias (redondeo): cajas exactas (±1) y kg ±0.10.
TOL_CAJAS = 1
TOL_KG = 0.10


# Cada caso: etiqueta, fecha_faena, fecha_produccion, tabla legacy {codigo: (cajas, kg)}.
CASES: list[dict] = [
    {
        "label": "15-10",
        "faena": date(2025, 10, 15),
        "prod": date(2025, 10, 16),
        "legacy": {
            "IBMCF3039": (1, 18), "IBMCF3090": (53, 689), "IBMCF3161": (13, 208),
            "IBMCF3180": (8, 112), "IBMCF3230": (4, 80), "IBMCF3250": (3, 48),
            "IBMCFC020": (32, 384), "IBMCFC221": (5, 60), "IBMCFE010": (5, 50),
            "IBMCFE030": (19, 239), "IBMCFE041": (30, 300), "IBMCFE042": (10, 120),
            "IBMCFE043": (31, 372), "IBMCFE050": (2, 25.95), "IBMCFE060": (6, 72),
            "IBMCFE070": (42, 420), "IBMCFE081": (18, 180), "IBMCFE100": (11, 110),
            "IBMCFE140": (26, 260), "IBMCFE141": (11, 110), "IBMCFE210": (223, 2230),
            "IBMCFE300": (6, 72), "IBMCFE310": (61, 732), "IBMCFE320": (6, 72),
            "IBMCFE340": (12, 120), "IBMCFE370": (37, 370), "IBMCFE371": (42, 420),
            "IBMCFE410": (3, 36), "IBMCHE010": (63, 699.8), "IBMCPE170": (13, 130),
            "IBMCPE171": (16, 160), "IBMCPE179": (2, 36), "IBMCPE202": (12, 120),
        },
    },
    {
        "label": "17-09",
        "faena": date(2025, 9, 17),
        "prod": date(2025, 9, 18),
        "legacy": {
            "FBMCFR110": (11, 87.211), "IBMCF3039": (5, 90), "IBMCF3090": (67, 871),
            "IBMCF3161": (17, 272), "IBMCF3180": (14, 196), "IBMCF3230": (8, 160),
            "IBMCFC020": (19, 228), "IBMCFC221": (8, 96), "IBMCFE010": (26, 260),
            "IBMCFE030": (28, 330.4), "IBMCFE041": (20, 200), "IBMCFE042": (12, 144),
            "IBMCFE043": (34, 408), "IBMCFE050": (1, 12.1), "IBMCFE060": (9, 108),
            "IBMCFE070": (49, 490), "IBMCFE081": (24, 240), "IBMCFE100": (22, 220),
            "IBMCFE140": (38, 380), "IBMCFE141": (14, 140), "IBMCFE210": (310, 3100),
            "IBMCFE300": (4, 48), "IBMCFE310": (37, 444), "IBMCFE320": (5, 60),
            "IBMCFE340": (6, 60), "IBMCFE370": (20, 200), "IBMCFE371": (67, 670),
            "IBMCFE410": (3, 36), "IBMCHE010": (59, 647.8), "IBMCPE170": (19, 190),
            "IBMCPE171": (25, 250), "IBMCPE179": (4, 72), "IBMCPE202": (16, 160),
        },
    },
    {
        "label": "21-01",
        "faena": date(2025, 1, 21),
        "prod": date(2025, 1, 22),
        "legacy": {
            "IBMCF3020": (8, 128), "IBMCF3039": (2, 36), "IBMCF3090": (46, 598),
            "IBMCF3161": (9, 144), "IBMCF3180": (6, 84), "IBMCF3220": (3, 54),
            "IBMCF3230": (4, 80), "IBMCF3400": (1, 20), "IBMCFB011": (34, 422.7),
            "IBMCFE030": (15, 178.85), "IBMCFE041": (10, 100), "IBMCFE042": (6, 72),
            "IBMCFE043": (16, 192), "IBMCFE060": (9, 108), "IBMCFE070": (28, 280),
            "IBMCFE081": (17, 170), "IBMCFE100": (3, 30), "IBMCFE140": (30, 300),
            "IBMCFE141": (8, 80), "IBMCFE210": (146, 1460), "IBMCFE240": (11, 110),
            "IBMCFE300": (3, 36), "IBMCFE310": (17, 204), "IBMCFE320": (2, 24),
            "IBMCFE340": (2, 20), "IBMCFE370": (54, 540), "IBMCPE170": (6, 60),
            "IBMCPE171": (13, 130), "IBMCPE179": (1, 18), "IBMCPE202": (8, 80),
        },
    },
]


def _run_etl_for(app, desde: date, hasta: date) -> None:
    from app.services.etl.runner import run_etl
    from app.services.etl.sources.sql_server import SqlServerTwinsSource
    from flask import current_app

    with app.app_context():
        cfg = current_app.config
        if not (cfg.get("MSSQL_SERVER") or "").strip():
            print("[!] MSSQL_SERVER no configurado — imposible conectar a Twins.")
            sys.exit(1)
        try:
            source = SqlServerTwinsSource.from_flask_config(cfg)
        except Exception as exc:
            print(f"[!] Error al crear SqlServerTwinsSource: {exc}")
            sys.exit(1)
        print(f"  ETL {desde} → {hasta} …")
        try:
            resumen = run_etl(source=source, desde=desde, hasta=hasta, origen="TwinsDbQuatro045")
        except Exception as exc:
            print(f"  [!] ETL falló: {exc}")
            sys.exit(1)
        print(f"  ETL ok (ejecucion_id={resumen.ejecucion_id}, estado={resumen.estado})")


def _check_case(app, case: dict) -> bool:
    from sqlalchemy import text
    from app.extensions import db

    legacy: dict[str, tuple[float, float]] = case["legacy"]
    leg_cajas = sum(v[0] for v in legacy.values())
    leg_kg = sum(v[1] for v in legacy.values())

    with app.app_context():
        rows = db.session.execute(
            text(
                "SELECT mercaderia_codigo, "
                "       SUM(cajas)::numeric(18,3) AS cajas, "
                "       SUM(kg_neto)::numeric(18,3) AS kg "
                "FROM reporting.mv_ddjj_menudencias_diaria "
                "WHERE fecha_faena = :f AND categoria = 'MENUDENCIA' "
                "GROUP BY mercaderia_codigo"
            ),
            {"f": case["prod"]},
        ).fetchall()
        actual = {r[0]: (float(r[1]), float(r[2])) for r in rows}

    print("=" * 72)
    print(f"CASO {case['label']}  (faena {case['faena']} / prod {case['prod']})")
    print("=" * 72)
    print(f"  {'Código':<12} {'CajasA':>7} {'KgA':>9} {'CajasL':>7} {'KgL':>9}  Estado")
    n_ok = n_diff = n_falta = n_extra = 0
    tot_ca = tot_ka = 0.0
    for cod in sorted(set(actual) | set(legacy)):
        ca, ka = actual.get(cod, (0.0, 0.0))
        cl, kl = legacy.get(cod, (0.0, 0.0))
        tot_ca += ca
        tot_ka += ka
        if cod not in legacy:
            estado, n_extra = "EXTRA", n_extra + 1
        elif cod not in actual:
            estado, n_falta = "FALTA", n_falta + 1
        elif abs(ca - cl) <= TOL_CAJAS and abs(ka - kl) <= TOL_KG:
            estado, n_ok = "OK", n_ok + 1
        else:
            estado, n_diff = f"DIFF cajas {ca-cl:+.0f} / kg {ka-kl:+.2f}", n_diff + 1
        if estado != "OK":
            print(f"  {cod:<12} {ca:>7.0f} {ka:>9.2f} {cl:>7.0f} {kl:>9.2f}  {estado}")
    print(f"  {'TOTAL':<12} {tot_ca:>7.0f} {tot_ka:>9.2f} {leg_cajas:>7.0f} {leg_kg:>9.2f}")
    print(f"  OK={n_ok}  DIFF={n_diff}  FALTA={n_falta}  EXTRA={n_extra}")
    ok = (n_diff == 0 and n_falta == 0 and n_extra == 0
          and abs(tot_ca - leg_cajas) <= TOL_CAJAS and abs(tot_ka - leg_kg) <= TOL_KG)
    print("  -> " + ("[OK] coincide con el legacy" if ok else "[!!] quedan diferencias"))
    print()
    return ok


def main() -> None:
    dry_run = "--dry-run" in sys.argv
    from app import create_app
    app = create_app()

    if not dry_run:
        # Limpieza previa: el ETL hace upsert pero NO invalida filas de
        # core.salida que dejan de venir en la fuente (p.ej. al aplicar el
        # filtro Pc_Id). Para una validacion limpia borramos el rango antes
        # de recargarlo. En produccion, este fix requiere una recarga
        # equivalente del rango afectado para purgar filas viejas.
        from sqlalchemy import text as _text
        from app.extensions import db
        with app.app_context():
            for case in CASES:
                desde = min(case["faena"], case["prod"])
                hasta = max(case["faena"], case["prod"])
                db.session.execute(
                    _text("DELETE FROM core.salida WHERE fecha_emision BETWEEN :d AND :h"),
                    {"d": desde, "h": hasta},
                )
            db.session.commit()
        for case in CASES:
            desde = min(case["faena"], case["prod"])
            hasta = max(case["faena"], case["prod"])
            _run_etl_for(app, desde, hasta)
        # refrescar vistas materializadas tras cargar todos los casos
        from app.services.etl.refresher import refresh_reporting_views
        with app.app_context():
            refresh_reporting_views()
        print()
    else:
        print("[dry-run] Omitiendo ETL — sólo consultando vistas actuales.\n")

    resultados = [(_check_case(app, c), c["label"]) for c in CASES]
    fallidos = [lbl for ok, lbl in resultados if not ok]
    if fallidos:
        print(f"RESULTADO FINAL: fallaron {fallidos}")
        sys.exit(1)
    print("RESULTADO FINAL: los 3 casos coinciden con el legacy. [OK]")


if __name__ == "__main__":
    main()
