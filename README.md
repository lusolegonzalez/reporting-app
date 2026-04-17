# Reporting App Backend

Backend Flask configurado para usar **PostgreSQL** como base de datos principal.

## Requisitos

- Python 3.11+
- PostgreSQL 14+

## Instalación

1. Crear y activar entorno virtual:

```bash
python -m venv .venv
source .venv/bin/activate
```

2. Instalar dependencias:

```bash
pip install -r requirements.txt
```

3. Configurar variables de entorno:

```bash
cp .env.example .env
```

Editar `DATABASE_URL` en `.env` con tus credenciales reales.

## URL de base de datos (PostgreSQL)

Este proyecto espera una URL de SQLAlchemy compatible con PostgreSQL:

```text
postgresql+psycopg://usuario:password@localhost:5432/reporting_db
```

## Migraciones

Con Flask-Migrate:

```bash
flask db upgrade
```

Si necesitas generar una migración nueva:

```bash
flask db migrate -m "descripcion"
flask db upgrade
```

## Ejecutar en local

```bash
flask run
```

---

## Nota sobre reversión desde SQL Server

Para una reversión limpia hacia PostgreSQL:

- remover dependencias de SQL Server (`pyodbc`, `mssql+pyodbc`, etc.)
- usar `psycopg` (driver moderno recomendado para PostgreSQL)
- mantener modelos SQLAlchemy sin tipos/ajustes específicos de SQL Server

Si la migración inicial fue alterada con dialecto SQL Server, conviene **regenerar una migración inicial limpia para PostgreSQL** en entornos nuevos.
