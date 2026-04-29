"""Clasificacion de mercaderias en categorias de reporting.

Las reglas se cargan desde core.mercaderia_clasificacion_regla y se
evaluan en orden de prioridad ascendente. Si ninguna matchea, la
mercaderia cae en la categoria OTRO.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from app.extensions import db
from app.models import MercaderiaCategoria, MercaderiaClasificacionRegla


@dataclass(frozen=True)
class _Regla:
    tipo_match: str
    patron: str
    categoria_id: int
    compilado: re.Pattern[str] | None


class MercaderiaClassifier:
    """Snapshot inmutable de reglas; instanciar una vez por corrida ETL."""

    def __init__(self, reglas: list[_Regla], categoria_otro_id: int) -> None:
        self._reglas = reglas
        self._categoria_otro_id = categoria_otro_id

    @classmethod
    def from_db(cls) -> "MercaderiaClassifier":
        reglas_raw = (
            db.session.query(MercaderiaClasificacionRegla)
            .filter(MercaderiaClasificacionRegla.activa.is_(True))
            .order_by(MercaderiaClasificacionRegla.prioridad.asc())
            .all()
        )
        reglas: list[_Regla] = []
        for r in reglas_raw:
            compilado: re.Pattern[str] | None = None
            if r.tipo_match == "REGEX_DESCRIPCION":
                try:
                    compilado = re.compile(r.patron, re.IGNORECASE)
                except re.error:
                    continue
            reglas.append(
                _Regla(
                    tipo_match=r.tipo_match,
                    patron=r.patron,
                    categoria_id=int(r.categoria_id),
                    compilado=compilado,
                )
            )

        otro = (
            db.session.query(MercaderiaCategoria)
            .filter(MercaderiaCategoria.codigo == "OTRO")
            .one()
        )
        return cls(reglas=reglas, categoria_otro_id=int(otro.id))

    def clasificar(self, codigo: str | None, descripcion: str | None) -> int:
        codigo_norm = (codigo or "").strip().upper()
        descripcion_norm = (descripcion or "").strip().upper()

        for r in self._reglas:
            if r.tipo_match == "PREFIJO_CODIGO":
                if codigo_norm.startswith(r.patron.upper()):
                    return r.categoria_id
            elif r.tipo_match == "CODIGO_EXACTO":
                if codigo_norm == r.patron.upper():
                    return r.categoria_id
            elif r.tipo_match == "REGEX_DESCRIPCION" and r.compilado is not None:
                if r.compilado.search(descripcion_norm):
                    return r.categoria_id

        return self._categoria_otro_id
