# Reporting App Backend

Backend Flask preparado para usar **SQL Server** con **SQLAlchemy** y **Flask-Migrate**.

## 1) Instalar dependencias

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

> En Linux también necesitás instalar el driver de sistema **ODBC Driver 18 for SQL Server** (`msodbcsql18`) y `unixODBC`.

## 2) Configurar conexión a SQL Server

Copiá `.env.example` a `.env` y ajustá `DATABASE_URL`:

```bash
cp .env.example .env
```

Formato recomendado:

```env
DATABASE_URL=mssql+pyodbc://usuario:password@host:1433/database?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes
```

## 3) Migraciones

Inicializar migraciones (si todavía no existe carpeta `migrations`):

```bash
flask db init
```

Crear migración:

```bash
flask db migrate -m "initial schema"
```

Aplicar migraciones:

```bash
flask db upgrade
```

### Nota sobre migración inicial existente

Si tu migración inicial fue generada para PostgreSQL y contiene tipos específicos (por ejemplo `postgresql.UUID`, `JSONB`, `ARRAY`), conviene:

1. Cambiar esos tipos por tipos portables de SQLAlchemy (`String`, `Text`, `JSON`, etc.), o
2. Regenerar la migración inicial sobre SQL Server:
   - borrar la migración inicial previa,
   - ejecutar `flask db migrate -m "initial schema for sqlserver"`,
   - ejecutar `flask db upgrade`.

Si no usaste tipos específicos de PostgreSQL, **no hace falta recrear** la migración inicial.

## 4) Levantar proyecto local

```bash
flask run
```
