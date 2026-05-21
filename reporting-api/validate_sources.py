"""Validación local de los tres métodos fuente que fallan.

Ejecutar desde reporting-api/:
    python validate_sources.py [YYYY-MM-DD [YYYY-MM-DD]]

Si no se pasan fechas usa 2026-01-01 → 2026-01-10 como rango de prueba.
Imprime: método | filas devueltas | primera fila (si hay).
"""
from __future__ import annotations

import sys
from datetime import date, datetime

from dotenv import load_dotenv

load_dotenv()


def _parse(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()


def main() -> None:
    desde = _parse(sys.argv[1]) if len(sys.argv) > 1 else date(2026, 1, 1)
    hasta = _parse(sys.argv[2]) if len(sys.argv) > 2 else date(2026, 1, 10)

    print(f"Rango de prueba: {desde} → {hasta}\n")

    # Importar dentro del contexto Flask para que from_flask_config funcione.
    from app import create_app  # noqa: PLC0415
    from app.services.etl.sources.sql_server import SqlServerTwinsSource  # noqa: PLC0415

    app = create_app()
    with app.app_context():
        from flask import current_app  # noqa: PLC0415

        src = SqlServerTwinsSource.from_flask_config(current_app.config)

        for nombre, fn in [
            ("fetch_tropas", lambda: src.fetch_tropas(desde, hasta)),
            ("fetch_faena", lambda: src.fetch_faena(desde, hasta)),
            ("fetch_salidas", lambda: src.fetch_salidas(desde, hasta)),
        ]:
            print(f"--- {nombre} ---")
            try:
                rows = list(fn())
                print(f"  filas devueltas : {len(rows)}")
                if rows:
                    print(f"  primera fila    : {rows[0]}")
                else:
                    print("  (sin filas)")
            except Exception as exc:  # noqa: BLE001
                print(f"  ERROR: {exc}")
            print()


if __name__ == "__main__":
    main()
