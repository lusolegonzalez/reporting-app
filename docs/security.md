# Seguridad

## Autenticación

- Método: JWT vía [Flask-JWT-Extended](https://flask-jwt-extended.readthedocs.io/).
- Endpoint: `POST /api/auth/login` con body `{"email", "password"}`.
- Backend valida:
  - usuario existe (búsqueda case-insensitive por email),
  - `activo=true`,
  - `check_password` con `werkzeug.security.check_password_hash` (almacenamos
    `password_hash`, nunca el password en claro).
- Si OK, devuelve:
  ```json
  {
    "access_token": "...",
    "user": { "id": 1, "nombre": "Admin", "email": "admin@reporting.local", "roles": ["ADMIN"] }
  }
  ```
- El JWT se emite con:
  - `identity = str(user.id)` — clave para el `user_lookup_loader`.
  - `additional_claims.roles = user.role_names` — usado por el guard `admin_required`
    para no hacer un round-trip extra a la base.
- El frontend persiste `access_token` y `user` en `localStorage` y envía
  `Authorization: Bearer <token>` en todas las llamadas via interceptor axios.
- Si una respuesta vuelve `401`, el cliente axios limpia sesión y redirige a
  `/login`. Los `403` quedan a cargo de cada pantalla.

## Usuarios y roles

Modelos: `Usuario`, `Rol`, `UsuarioRol` (relación N:M).

| Operación | Endpoint | Permiso |
|-----------|----------|---------|
| Listar / crear / editar usuarios | `GET/POST/PUT /api/users` | admin |
| Asignar roles a un usuario | `PUT /api/users/<id>/roles` | admin |
| Listar / crear / editar roles | `GET/POST/PUT /api/roles` | admin |

- Email único, normalizado a `lower()`.
- Password se setea con `Usuario.set_password(raw)` (genera hash). Nunca se
  expone `password_hash` en respuestas (`to_auth_dict()` solo devuelve
  `id, nombre, email, roles`).
- `roles[]` viaja como lista de **nombres** (string), no IDs, para simplificar
  consumo en frontend.

## Permisos por reporte

Modelo: `RolReportePermiso`

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `rol_id` | FK roles | Rol al que aplica el permiso |
| `reporte_id` | FK reportes | Reporte al que aplica |
| `puede_ver` | bool | Habilita ver/ejecutar el reporte |
| `puede_exportar` | bool | Habilita exportación (Excel/PDF). Requiere `puede_ver=true` |

Reglas:

- Si un usuario tiene **al menos un rol** con `puede_ver=true` para el reporte
  y el reporte está `activo`, puede verlo y ejecutarlo en formato JSON.
- Si tiene **al menos un rol** con `puede_exportar=true`, puede pedir
  formatos `excel` o `pdf`. El backend valida `puede_exportar` antes de
  ejecutar.
- En la UI de visibilidad ([ReportFormPage / ReportsPage](../reporting-web/src/pages)),
  desmarcar `puede_ver` desmarca automáticamente `puede_exportar` para
  mantener la coherencia. El backend aplica la misma regla en
  `PUT /api/reports/<id>/visibility`.

### Endpoints de visibilidad

| Endpoint | Método | Permiso | Notas |
|----------|--------|---------|-------|
| `GET /api/reports/<id>/visibility` | GET | admin | Lista todos los roles con su flag actual |
| `PUT /api/reports/<id>/visibility` | PUT | admin | Recibe `[{role_id, puede_ver, puede_exportar}, ...]`. Roles no incluidos quedan sin permiso |
| `GET /api/reports/visible/me` | GET | JWT | Lista los reportes activos visibles para el usuario actual |
| `GET /api/reports/by-codigo/<codigo>/metadata` | GET | JWT + `puede_ver` | Devuelve `permisos.puede_exportar` y `formatos_disponibles` para que la UI muestre/oculte botones |

## Guard `admin_required`

[`app/utils/auth.py`](../reporting-api/app/utils/auth.py)

- Verifica el JWT (`verify_jwt_in_request`).
- Lee el claim `roles` del JWT (lista de nombres). Si no está, cae a
  `current_user.role_names`.
- Si el rol admin (configurable por `ADMIN_ROLE_NAME`, default `ADMIN`) no
  está presente, devuelve `403 {"message": "Se requieren permisos de administrador."}`.

Aplicado en:

| Blueprint | Endpoints protegidos |
|-----------|----------------------|
| `users_bp` | todos |
| `roles_bp` | todos |
| `reports_bp` | listado admin, create/update, GET/PUT visibility |
| `etl_bp` | run + ejecuciones |
| `audit_bp` | listados de auditoría funcional y técnica |

Los endpoints de **ejecución** de reportes (`metadata`, `run`) **no** usan
`admin_required`: solo exigen JWT y validan permisos por rol contra la tabla
`roles_reportes_permisos`. Esto permite que cualquier usuario con el permiso
correspondiente ejecute el reporte sin necesidad de ser administrador.

## Restricciones por rol — matriz final

| Acción | Sin login | Usuario común | Admin |
|---|---|---|---|
| `/api/auth/login` | público | — | — |
| `/api/health`, `/api/health/ready` | público | público | público |
| `/api/users/*`, `/api/roles/*`, `/api/etl/*`, `/api/audit/*`, `/api/reports` (admin) | 401 | 403 | 200 |
| `GET /api/reports/visible/me` | 401 | reportes con `puede_ver=true` | todos los suyos |
| `GET /by-codigo/<x>/metadata` | 401 | 403 si no `puede_ver`; `formatos_disponibles.excel/pdf=false` si no `puede_exportar` | 200 |
| `POST /by-codigo/<x>/run` formato=json | 401 | requiere `puede_ver` | OK |
| `POST .../run` formato=excel/pdf | 401 | 403 si no `puede_exportar`; 501 si tiene permiso pero el renderer no está | 501 |

## Sidebar adaptativo (frontend)

[`src/layouts/MainLayout.tsx`](../reporting-web/src/layouts/MainLayout.tsx)

Items `Usuarios` y `Roles` solo se muestran si el usuario incluye `ADMIN` en
sus roles. Esto evita 403 visibles para usuarios no administradores y mantiene
la navegación limpia. **No es un mecanismo de seguridad**: la autorización
real ocurre siempre en el backend.

## Buenas prácticas implementadas

- `SECRET_KEY` y `JWT_SECRET_KEY` por env var; nunca en código.
- CORS restringido por env var (`CORS_ORIGINS`), default solo `localhost`.
- Conexión a SQL Server origen forzada a solo lectura
  (`ApplicationIntent=ReadOnly` + `readonly=True` + guard SELECT/WITH).
- Coherencia entre `puede_ver` y `puede_exportar` aplicada en backend y UI.
- Endpoints administrativos centralizan la verificación con un único decorador,
  evitando reglas dispersas.

## Pendientes / mejoras sugeridas

- **Rate limit en `/auth/login`** para mitigar brute-force.
- **Rotación de `JWT_SECRET_KEY`** y soporte de revocación (lista de tokens
  revocados).
- **Política de password** (largo mínimo, complejidad, expiración) en
  `Usuario.set_password`.
- **Auditoría de operaciones administrativas** (alta de usuario, cambio de
  permisos): hoy solo se audita la consulta de reportes y las corridas ETL.
