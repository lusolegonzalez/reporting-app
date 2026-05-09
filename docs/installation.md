# Instalación y configuración

## Requisitos

- **Python 3.10+** (recomendado 3.12) — backend.
- **Node.js 20+** y npm — frontend.
- **PostgreSQL 14+** — base intermedia.
- **SQL Server origen** + driver ODBC instalado en el host — opcional para
  el ETL real. Sin él, el sistema funciona con la fuente in-memory `empty`.
  - Linux: `unixODBC` + `msodbcsql18`.
  - Windows: `ODBC Driver 18 for SQL Server`.

## Estructura del repo

```
reporting-app/
├── README.md                  -> overview + links
├── docs/                      -> documentación profesional
├── reporting-api/             -> backend Flask
│   ├── app/
│   ├── migrations/
│   ├── requirements.txt
│   ├── run.py
│   └── .env.example
├── reporting-web/             -> frontend React
│   ├── src/
│   ├── package.json
│   └── .env.example
└── documentation/             -> material funcional original
```

## Variables de entorno

### Backend — [`reporting-api/.env`](../reporting-api/.env.example)

| Variable | Default | Descripción |
|----------|---------|-------------|
| `FLASK_ENV` | `development` | Perfil (`development`/`testing`/`production`) |
| `SECRET_KEY` | `change-me` | Secret de Flask (sesiones, signed cookies si se usaran) |
| `JWT_SECRET_KEY` | `change-me-too` | Secret para firmar JWT |
| `DATABASE_URL` | `postgresql+psycopg2://postgres:postgres@localhost:5432/reporting_api` | DSN de la base intermedia |
| `CORS_ORIGINS` | `http://localhost:5173,http://localhost:3000` | Orígenes permitidos por flask-cors |
| `ADMIN_ROLE_NAME` | `ADMIN` | Nombre del rol admin para el guard `admin_required` |
| `MSSQL_DRIVER` | `{ODBC Driver 18 for SQL Server}` | Driver ODBC. En Linux suele ser `{ODBC Driver 18 for SQL Server}` también |
| `MSSQL_SERVER` | *(vacío)* | Host SQL Server. Si está vacío, sólo `source=empty` funciona |
| `MSSQL_PORT` | `1433` | Puerto SQL Server |
| `MSSQL_DATABASE` | `TwinsDbQuatro045` | Base origen |
| `MSSQL_UID`, `MSSQL_PWD` | *(vacíos)* | Credenciales SQL |
| `MSSQL_ENCRYPT` | `no` | `yes`/`no` |
| `MSSQL_TRUST_SERVER_CERTIFICATE` | `yes` | `yes`/`no` |
| `MSSQL_LOGIN_TIMEOUT` | `10` | Segundos |
| `MSSQL_QUERY_TIMEOUT` | `60` | Segundos |

> En producción cambiar `SECRET_KEY`, `JWT_SECRET_KEY` y restringir
> `CORS_ORIGINS` al dominio público.

### Frontend — [`reporting-web/.env`](../reporting-web/.env.example)

| Variable | Default | Descripción |
|----------|---------|-------------|
| `VITE_API_BASE_URL` | `http://localhost:5000/api` | URL base de la API |

## Base de datos

Crear la base PostgreSQL (una vez):

```sql
CREATE DATABASE reporting_api;
```

Aplicar migraciones (idempotente):

```bash
cd reporting-api
flask --app run.py db upgrade
```

Las migraciones viven en
[`reporting-api/migrations/versions/`](../reporting-api/migrations/versions).
Crean los esquemas necesarios (`public`, `etl`, `staging`, `core`,
`reporting`).

### Seed inicial

Crea el rol `ADMIN`, el usuario `admin@reporting.local` (password
`Admin123*`) y los reportes seed (`REP_RESUMEN`, `REP_DETALLE`,
`DDJJ_MENUDENCIAS`) con permisos completos para ADMIN:

```bash
flask --app run.py seed-initial-auth
```

> Cambiar el password del admin inicial antes de exponer el servicio.

## Ejecución local

### Backend

```bash
cd reporting-api
python -m venv .venv
# Linux/macOS
source .venv/bin/activate
# Windows PowerShell
# .venv\Scripts\Activate.ps1

pip install -r requirements.txt
cp .env.example .env       # editar según corresponda
flask --app run.py db upgrade
flask --app run.py seed-initial-auth
python run.py
```

API expuesta en `http://localhost:5000`.

### Frontend

```bash
cd reporting-web
cp .env.example .env
npm install
npm run dev
```

UI expuesta en `http://localhost:5173`.

## Verificaciones

### Health checks

```bash
curl http://localhost:5000/api/health
# {"service":"reporting-api","status":"ok"}

curl http://localhost:5000/api/health/ready
# 200 si la DB intermedia responde, 503 si no.
```

`/api/health` es un check liviano (proceso vivo). `/api/health/ready` ejecuta
`SELECT 1` contra la DB intermedia y es lo que debe consumir un orquestador
(k8s readiness, load balancer probe, systemd).

### Smoke check técnico

```bash
flask --app run.py smoke-check
```

Valida:

1. Conectividad a la base intermedia (`SELECT 1`).
2. Existencia del rol admin (configurable por `ADMIN_ROLE_NAME`).
3. Usuario admin activo.
4. Reportes seed presentes en DB.
5. `DDJJ_MENUDENCIAS` registrado en el `report_registry`.
6. Permiso de admin sobre `DDJJ_MENUDENCIAS`.

Sale con código `0` si todo OK, `1` si algo falla. Usable en pipelines /
post-deploy hooks.

### Login manual

```bash
curl -X POST http://localhost:5000/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@reporting.local","password":"Admin123*"}'
```

Debe devolver `access_token` y `user.roles=["ADMIN"]`.

## Despliegue básico

El proyecto no incluye Dockerfiles ni manifiestos de orquestación, pero la
estructura está pensada para un despliegue clásico:

### Backend (recomendado)

- Servidor WSGI: `gunicorn` o `uwsgi` detrás de Nginx/Traefik.
- Comando típico (gunicorn):

  ```bash
  gunicorn -w 4 -b 0.0.0.0:5000 'run:app'
  ```

- Variables de entorno gestionadas por `.env` o el sistema (systemd
  `EnvironmentFile=`, secrets de k8s, etc.).
- Aplicar `flask db upgrade` antes de levantar el proceso.
- Probar `flask smoke-check` post-deploy y abortar si falla.
- Configurar el orquestador para usar `/api/health/ready` como readiness
  probe y `/api/health` como liveness.

### Frontend (recomendado)

- `npm run build` genera `dist/`.
- Servir `dist/` con Nginx, Caddy, S3+CloudFront, etc.
- En producción, fijar `VITE_API_BASE_URL` apuntando al backend público.
- Configurar el web server para hacer fallback a `index.html` (SPA).

### Compatibilidad Linux

- Todos los paths del código nuevo usan `/`. No hay separadores de Windows.
- Driver ODBC en Linux: instalar `unixODBC` + `msodbcsql18` siguiendo la
  [guía oficial de Microsoft](https://learn.microsoft.com/sql/connect/odbc/linux-mac/installing-the-microsoft-odbc-driver-for-sql-server).
- `pyodbc` y `psycopg2-binary` están en `requirements.txt` con wheels
  precompilados para distribuciones comunes.
- El advisory lock del ETL (`pg_try_advisory_lock`) es nativo de PostgreSQL,
  funciona igual en cualquier OS.

## Errores comunes

| Síntoma | Causa probable | Mitigación |
|---------|----------------|------------|
| `401` en cualquier llamada autenticada | Token vencido o ausente | El frontend redirige a `/login` automáticamente; volver a loguear |
| `403 Se requieren permisos de administrador` | Endpoint admin con usuario sin rol ADMIN | Asignar rol o usar otro usuario |
| `403 Sin permiso para visualizar este reporte` | Falta `puede_ver` para algún rol del usuario | Configurar visibilidad desde la UI admin |
| `409 Hay una ejecución de ETL en curso` | Otro proceso tiene el advisory lock | Esperar / verificar `GET /api/audit/etl-ejecuciones?estado=en_curso` |
| `501 Exportación X aún no implementada` | Renderer Excel/PDF pendiente | Esperado; usar formato JSON por ahora |
| `503` en `/api/health/ready` | DB intermedia caída o inaccesible | Revisar `DATABASE_URL`, conectividad, credenciales |
| ETL `mssql` falla con error ODBC | Driver no instalado o credenciales inválidas | Instalar driver ODBC; revisar `MSSQL_*` |
