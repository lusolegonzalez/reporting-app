"""Configuración central de la aplicación Flask."""

from __future__ import annotations

import os


class Config:
    """Configuración base usando variables de entorno."""

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "mssql+pyodbc://sa:YourStrong!Passw0rd@localhost:1433/reporting_db"
        "?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes",
    )
