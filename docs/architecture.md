# Arquitectura

## Componentes

```
+----------------------+       HTTPS/JSON       +-----------------------+
|  reporting-web       |  <------------------>  |  reporting-api        |
|  React + TypeScript  |   /api/auth, /api/...  |  Flask (Python 3.10+) |
+----------------------+                        +-----------+-----------+
                                                            |
                                            +---------------+----------------+
                                            |                                |
                                  +---------v---------+        +-------------v---------------+
                                  |  PostgreSQL       |        |  SQL Server (Twins PI4)     |
                                  |  base intermedia  |        |  TwinsDbQuatro045 (READONLY)|
                                  |  read/write       |        |  ApplicationIntent=ReadOnly |
                                  +-------------------+        +-----------------------------+
                                            ^
                                            |
                                            |  ETL (pyodbc)
                                            +--- run_etl(...) (servicios/etl/runner)
```

- **El sistema nunca escribe en SQL Server**. La conexión se abre en
  `readonly=True` con `ApplicationIntent=ReadOnly` y un guard rechaza
  cualquier sentencia que no sea `SELECT`/`WITH` (defensa en profundidad).
- La base intermedia PostgreSQL es la única fuente de verdad para autenticación,
  permisos, datos productivos consolidados, vistas de reporting y auditoría.

## Backend — `reporting-api`

Stack:

- Flask 3 + Flask-SQLAlchemy + Flask-Migrate (Alembic) + Flask-JWT-Extended +
  flask-cors.
- `psycopg2` para PostgreSQL.
- `pyodbc` para SQL Server (`{ODBC Driver 18 for SQL Server}`).

Capas:

| Capa | Carpeta | Responsabilidad |
|------|---------|-----------------|
| Configuración | [`app/config.py`](../reporting-api/app/config.py) | Carga de env vars, perfiles dev/test/prod |
| Extensiones | [`app/extensions.py`](../reporting-api/app/extensions.py) | Inicializa SQLAlchemy, JWT, CORS, Migrate |
| Modelos | [`app/models/`](../reporting-api/app/models) | Auth, reportes, permisos, ETL, auditoría, staging, core |
| Rutas | [`app/routes/`](../reporting-api/app/routes) | Endpoints HTTP por dominio |
| Servicios | [`app/services/`](../reporting-api/app/services) | Lógica de negocio: ETL, reportes, auditoría |
| Utils | [`app/utils/`](../reporting-api/app/utils) | Decoradores comunes (`admin_required`) |

### Servicios — ETL

[`app/services/etl/`](../reporting-api/app/services/etl)

- `runner.py` — orquesta la corrida, abre `EjecucionImportacion`,
  toma advisory lock para evitar concurrencia, ejecuta los pasos en orden y
  graba el resumen.
- `source.py` — Protocol `TwinsSource` que abstrae la fuente.
- `sources/in_memory.py` — fuente vacía para validar la maquinaria sin DB origen.
- `sources/sql_server.py` — `SqlServerTwinsSource` (pyodbc, read-only).
- `steps/` — pasos productivos: `mercaderias`, `operarios`, `tropas`, `faena`, `salidas`.
- `classifier.py`, `refresher.py` — utilitarios de clasificación / refresco.

### Servicios — Reporting

[`app/services/reports/`](../reporting-api/app/services/reports)

- `base.py` — contratos: `ReportParameter`, `ReportRequest`, `ReportResponse`,
  `ReportSection`, `ReportAlerta`, errores tipados, helpers `parse_date` /
  `parse_bool`.
- `registry.py` — `ReportRegistry`. Cada reporte concreto se registra con su
  `codigo` y se resuelve en runtime por el endpoint `/by-codigo/<codigo>/run`.
- `ddjj_menudencias.py` — primer reporte concreto (DDJJ Menudencias).

### Servicios — Auditoría

[`app/services/audit.py`](../reporting-api/app/services/audit.py)

- `record_report_query(usuario_id, reporte_id, parametros)` — context manager
  que abre una `AuditoriaConsultaReporte`, mide duración con `time.perf_counter`
  y commitea con `resultado_ok=True` o `False` según haya excepción.

### Rutas (resumen)

| Endpoint | Método | Auth |
|----------|--------|------|
| `/api/health` | GET | público |
| `/api/health/ready` | GET | público (probe) |
| `/api/auth/login` | POST | público |
| `/api/auth/me` | GET | JWT |
| `/api/users`, `/api/users/<id>`, `/api/users/<id>/roles` | GET/POST/PUT | admin |
| `/api/roles`, `/api/roles/<id>` | GET/POST/PUT | admin |
| `/api/reports` (admin), `/api/reports/<id>`, `/api/reports/<id>/visibility` | GET/POST/PUT | admin |
| `/api/reports/visible/me` | GET | JWT |
| `/api/reports/by-codigo/<codigo>/metadata` | GET | JWT + permiso |
| `/api/reports/by-codigo/<codigo>/run` | POST | JWT + permiso |
| `/api/etl/run`, `/api/etl/ejecuciones/<id>` | POST/GET | admin |
| `/api/audit/reportes`, `/api/audit/etl-ejecuciones` | GET | admin |

Ver [security.md](security.md) para el detalle del modelo de permisos.

## Frontend — `reporting-web`

Stack: React 18, TypeScript, Vite, react-router-dom, axios.

Capas:

| Carpeta | Responsabilidad |
|---------|-----------------|
| `src/api/` | Cliente axios + funciones por dominio. Interceptor 401 → logout |
| `src/components/` | Reutilizables (`PageHeader`, `ReportRunner`, `ReportForm`, `ReportsBreadcrumbs`) |
| `src/hooks/` | `useAuth` |
| `src/layouts/` | `MainLayout` con sidebar (oculta items admin a no-admin) |
| `src/pages/` | Pantallas: login, dashboard, usuarios, roles, reportes |
| `src/routes/` | Configuración de rutas + `PrivateRoute` |
| `src/types/` | Tipos compartidos (`ReportItem`, `ReportMetadata`, etc.) |
| `src/utils/storage.ts` | Persistencia de token y usuario en `localStorage` |

El frontend usa el JWT como `Bearer` en todas las requests. La ejecución de
reportes pasa por el componente genérico `ReportRunner`, que renderiza
parámetros y resultados a partir de la metadata del backend, sin lógica
específica por reporte. Esto permite incorporar nuevos reportes sin tocar el
frontend mientras respeten el contrato de `ReportDefinition`.

## Modelo de datos (resumen)

Tablas principales en PostgreSQL intermedia:

### Autenticación / autorización

- `usuarios` (id, nombre, email único, password_hash, activo, timestamps)
- `roles` (id, nombre único, descripcion)
- `usuarios_roles` (usuario_id, rol_id) — N:M
- `reportes` (id, codigo único, nombre, descripcion, activo)
- `roles_reportes_permisos` (rol_id, reporte_id, `puede_ver`, `puede_exportar`)

### ETL técnico

- `ejecuciones_importacion` (id, origen, fecha_desde, fecha_hasta, estado,
  observaciones, created_at, created_by_user_id)
- `etl.ejecucion_tablas` (filas leídas/insertadas/actualizadas/descartadas, duracion_ms por tabla)
- `etl.ejecucion_errores` (mensaje, source_pk, payload JSONB)

### Auditoría funcional

- `auditorias_consultas_reportes` (usuario_id, reporte_id, filtros_json,
  fecha_consulta, resultado_ok, **`duracion_ms`**, observaciones)

### Reporting (datos)

- Esquemas `staging` (datos crudos del ETL) y `core` (datos consolidados):
  mercaderías, operarios, tropas/sub-tropas, faena, salidas.
- Esquema `reporting` con vistas materializadas/normales para los reportes
  (ver migración `0008_reporting_views.py`).

## Flujo de un request de ejecución de reporte

1. El frontend pide `GET /api/reports/visible/me` y muestra solo reportes con
   `puede_ver=true` para el rol del usuario.
2. Al entrar a un reporte, pide `GET /api/reports/by-codigo/<CODIGO>/metadata`
   para obtener los parámetros y los flags de exportación permitidos.
3. El usuario completa parámetros y dispara `POST /by-codigo/<CODIGO>/run`
   con `{parametros, formato="json"}`.
4. Backend:
   - Valida JWT y existencia del reporte (`activo=true`).
   - Comprueba `puede_ver` (y `puede_exportar` si `formato` ≠ `json`).
   - Resuelve la `ReportDefinition` en el registry.
   - `parse_and_validate(raw)` → `ReportRequest` (puede devolver 400).
   - Abre auditoría con `record_report_query(...)`.
   - Ejecuta `definition.execute(request)` → `ReportResponse`.
   - Cierra auditoría con `resultado_ok` y `duracion_ms`.
   - Devuelve JSON estandarizado o 501 si el formato es excel/pdf (renderer
     pendiente).

## Migraciones

Las migraciones viven en [`reporting-api/migrations/versions/`](../reporting-api/migrations/versions).
Se aplican con `flask --app run.py db upgrade`. Ver [installation.md](installation.md).

| Versión | Cambio |
|---------|--------|
| 0001 | Auth + reportes base |
| 0002 | Esquemas ETL |
| 0003 | Categorías de mercadería |
| 0004 | Operario en mercadería |
| 0005 | Tropa / sub-tropa |
| 0006 | Faena |
| 0007 | Salidas |
| 0008 | Vistas de reporting |
| 0009 | `roles_reportes_permisos.puede_exportar` |
| 0010 | `auditorias_consultas_reportes.duracion_ms` |
