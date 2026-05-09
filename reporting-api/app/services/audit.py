"""Servicio de auditoria funcional de consultas a reportes.

Encapsula el patron "abrir auditoria, ejecutar, cerrar auditoria" para que los
endpoints no tengan que repetir el flujo de filas + manejo de errores.

Uso tipico desde una ruta:

    with record_report_query(
        usuario_id=current_user.id,
        reporte_id=report.id,
        parametros=request.parametros,
    ) as audit:
        response = definition.execute(request)

Si `execute` lanza, el helper marca `resultado_ok=False` y guarda la
descripcion del error en `observaciones`. Siempre commitea la auditoria.

La auditoria tecnica de extracciones (etl) se sigue resolviendo en el
runner ETL, que ya escribe en `etl.ejecucion_*`.
"""
from __future__ import annotations

import json
import logging
import time
from contextlib import contextmanager
from datetime import date, datetime, timezone
from typing import Any, Iterator

from app.extensions import db
from app.models import AuditoriaConsultaReporte

logger = logging.getLogger(__name__)


def _safe_json_dumps(value: Any) -> str:
    def _default(v: Any) -> Any:
        if isinstance(v, (date, datetime)):
            return v.isoformat()
        return str(v)

    try:
        return json.dumps(value, default=_default, ensure_ascii=False)
    except Exception:  # noqa: BLE001
        return "{}"


@contextmanager
def record_report_query(
    *,
    usuario_id: int,
    reporte_id: int,
    parametros: dict[str, Any] | None = None,
) -> Iterator[AuditoriaConsultaReporte]:
    """Crea y persiste una `AuditoriaConsultaReporte` rodeando un bloque.

    - Si el bloque termina sin error -> resultado_ok=True.
    - Si lanza -> resultado_ok=False, observaciones=resumen del error.
    - Siempre setea `duracion_ms` y commitea.
    """
    audit = AuditoriaConsultaReporte(
        usuario_id=usuario_id,
        reporte_id=reporte_id,
        filtros_json=_safe_json_dumps(parametros or {}),
        fecha_consulta=datetime.now(timezone.utc),
        resultado_ok=True,
    )
    db.session.add(audit)
    db.session.flush()  # asegura id si la ruta lo necesita

    inicio = time.perf_counter()
    try:
        yield audit
    except Exception as exc:  # noqa: BLE001
        audit.resultado_ok = False
        # Guardamos el repr (clase + mensaje) recortado: utilidad real para debugging.
        audit.observaciones = f"{type(exc).__name__}: {exc}"[:500]
        audit.duracion_ms = int((time.perf_counter() - inicio) * 1000)
        try:
            db.session.commit()
        except Exception:  # noqa: BLE001
            logger.exception("No se pudo commitear auditoria de error")
            db.session.rollback()
        raise
    else:
        audit.duracion_ms = int((time.perf_counter() - inicio) * 1000)
        db.session.commit()
