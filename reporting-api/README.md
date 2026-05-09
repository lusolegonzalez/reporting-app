# reporting-api

Backend base de reporting con **Flask + PostgreSQL**.

> Documentación profesional integral en [`../docs/`](../docs):
> [arquitectura](../docs/architecture.md), [seguridad](../docs/security.md),
> [reporting](../docs/reporting.md), [auditoría](../docs/audit.md),
> [instalación](../docs/installation.md). Este README mantiene el quickstart
> técnico.

## Objetivo de esta base

- Levantar API Flask localmente.
- Conectar contra PostgreSQL por variables de entorno.
- Aplicar migración inicial con Flask-Migrate.
- Exponer endpoint de salud `GET /api/health`.
- Habilitar CORS para frontend local (`http://localhost:5173` por defecto).

## Requisitos

- Python 3.10+ (recomendado 3.12)
- PostgreSQL 14+ ejecutándose en local

## Variables de entorno

Copiar el archivo de ejemplo:

```bash
cp .env.example .env
```

Variables usadas:

- `DATABASE_URL` (obligatoria):
  - ejemplo: `postgresql+psycopg2://postgres:postgres@localhost:5432/reporting_api`
- `CORS_ORIGINS`:
  - por defecto: `http://localhost:5173,http://localhost:3000`
- `SECRET_KEY`
- `JWT_SECRET_KEY`

### Origen SQL Server (solo lectura)

Variables usadas por la fuente real `SqlServerTwinsSource` (pyodbc).
Si `MSSQL_SERVER` queda vacio, la fuente real no se puede instanciar y solo
queda disponible la fuente `empty` (in-memory) para validar la maquinaria ETL.

- `MSSQL_DRIVER` (default `{ODBC Driver 18 for SQL Server}`)
- `MSSQL_SERVER`, `MSSQL_PORT` (default `1433`)
- `MSSQL_DATABASE` (default `TwinsDbQuatro045`)
- `MSSQL_UID`, `MSSQL_PWD`
- `MSSQL_ENCRYPT` (default `no`), `MSSQL_TRUST_SERVER_CERTIFICATE` (default `yes`)
- `MSSQL_LOGIN_TIMEOUT` (default `10`s), `MSSQL_QUERY_TIMEOUT` (default `60`s)

La conexion se abre con `readonly=True` y `ApplicationIntent=ReadOnly`, y
solo se permiten sentencias `SELECT`/`WITH` (defensa en profundidad).

## Levantar backend paso a paso

1. Crear y activar entorno virtual:

```bash
python -m venv .venv
source .venv/bin/activate
```

2. Instalar dependencias:

```bash
pip install -r requirements.txt
```

3. Crear base de datos en PostgreSQL:

```sql
CREATE DATABASE reporting_api;
```

4. Ejecutar migración inicial:

```bash
flask --app run.py db upgrade
```

5. Levantar servidor Flask:

```bash
python run.py
```

La API queda disponible en `http://localhost:5000`.

## Verificaciones rápidas

### Health endpoint

```bash
curl http://localhost:5000/api/health
```

Respuesta esperada:

```json
{"service":"reporting-api","status":"ok"}
```

### Verificar CORS para frontend local

```bash
curl -i -H "Origin: http://localhost:5173" http://localhost:5000/api/health
```

Esperado en headers: `Access-Control-Allow-Origin: http://localhost:5173`

## Endpoints placeholder

- `GET /api/health`
- `POST /api/auth/login`
- `GET /api/auth/me`
- `GET /api/users`
- `POST /api/users`
- `GET /api/roles`
- `GET /api/reports`
- `GET /api/reports/<report_id>`
- `POST /api/etl/run`
- `GET /api/etl/ejecuciones/<id>`

### `POST /api/etl/run`

Body JSON:

```json
{
  "desde": "2026-04-01",
  "hasta": "2026-04-30",
  "origen": "TwinsDbQuatro045",
  "source": "empty"
}
```

`source`:

- `empty` (default): fuente in-memory vacia, util para validar la maquinaria
  del runner sin dependencias externas.
- `mssql`: usa `SqlServerTwinsSource` con las variables `MSSQL_*`.


## Seed inicial de autenticación

Después de correr migraciones, crear rol y usuario admin inicial:

```bash
flask --app run.py seed-initial-auth
```

Credenciales del usuario de prueba:

- email: `admin@reporting.local`
- password: `Admin123*`

