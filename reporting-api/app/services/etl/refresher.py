"""Refresco coordinado de las vistas materializadas de reporting."""
from __future__ import annotations

from sqlalchemy import text

from app.extensions import db


# Orden importante: las MV de mas abajo dependen de las anteriores.
_MATERIALIZED_VIEWS: tuple[str, ...] = (
    "reporting.mv_ddjj_menudencias_diaria",
    "reporting.mv_faena_diaria",
    "reporting.mv_tropas_por_faena_diaria",
    "reporting.mv_consistencia_ddjj",
)


def refresh_reporting_views(*, concurrently: bool = True) -> list[str]:
    """Refresca todas las MV de reporting. Devuelve la lista refrescada.

    Cada REFRESH se confirma en su propia transaccion para que un
    fallback (rollback al modo no-CONCURRENTLY) no descarte el trabajo
    ya hecho en MV previas. El primer REFRESH de una MV creada con
    WITH NO DATA debe correr sin CONCURRENTLY (Postgres lo exige); si
    concurrently=True y la MV esta vacia, se reintenta sin CONCURRENTLY.
    """
    refrescadas: list[str] = []
    for mv in _MATERIALIZED_VIEWS:
        # Aseguramos transaccion limpia para esta MV.
        db.session.commit()
        try:
            if concurrently:
                db.session.execute(
                    text(f"REFRESH MATERIALIZED VIEW CONCURRENTLY {mv}")
                )
            else:
                db.session.execute(text(f"REFRESH MATERIALIZED VIEW {mv}"))
            db.session.commit()
        except Exception:
            db.session.rollback()
            db.session.execute(text(f"REFRESH MATERIALIZED VIEW {mv}"))
            db.session.commit()
        refrescadas.append(mv)
    return refrescadas
