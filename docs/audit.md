# Auditoría y trazabilidad

El sistema mantiene **dos pistas de auditoría independientes**:

| Pista | Tabla(s) | Origen | Endpoint de lectura |
|-------|----------|--------|---------------------|
| Funcional — consultas a reportes | `auditorias_consultas_reportes` | `record_report_query` | `GET /api/audit/reportes` |
| Técnica — corridas ETL | `ejecuciones_importacion` + `etl.ejecucion_tablas` + `etl.ejecucion_errores` | `run_etl` | `GET /api/audit/etl-ejecuciones`, `GET /api/etl/ejecuciones/<id>` |

Ambos endpoints exigen rol admin.

## Auditoría funcional — consultas a reportes

Modelo: [`AuditoriaConsultaReporte`](../reporting-api/app/models/audit.py)

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id` | int | PK |
| `usuario_id` | FK usuarios | Quién ejecutó |
| `reporte_id` | FK reportes | Qué reporte |
| `fecha_consulta` | timestamptz | Inicio de la corrida (UTC) |
| `filtros_json` | text | Parámetros serializados (JSON safe) |
| `resultado_ok` | bool | true si terminó sin excepción |
| `duracion_ms` | int | Tiempo medido con `time.perf_counter` |
| `observaciones` | text | Si `resultado_ok=false`: `{ClassName}: {msg}` (≤500 chars) |

### Cómo se registra

[`app/services/audit.py`](../reporting-api/app/services/audit.py) expone un
context manager:

```python
with record_report_query(
    usuario_id=current_user.id,
    reporte_id=report.id,
    parametros=report_request.parametros,
):
    response = definition.execute(report_request)
```

Comportamiento:

- Crea la fila con `resultado_ok=true`, `fecha_consulta=now(utc)`,
  `filtros_json=json(parametros)`, hace `flush` (id disponible dentro del
  bloque) y arranca un cronómetro.
- Si el bloque sale OK: setea `duracion_ms` y commitea.
- Si lanza: setea `resultado_ok=false`, escribe `observaciones=
  "{type(exc).__name__}: {exc}"[:500]`, setea `duracion_ms`, commitea
  igual y re-lanza la excepción.
- Si el commit final falla, se loguea con `logger.exception(...)` y se hace
  rollback. Esto evita perder el resto de la transacción.

### Cobertura

Se auditan los `POST /api/reports/by-codigo/<codigo>/run` que pasaron la
validación de parámetros. Es decir:

- ✅ Ejecución exitosa → 1 fila con `resultado_ok=true` y `duracion_ms`.
- ✅ Ejecución que rompe en `definition.execute(...)` → 1 fila con
  `resultado_ok=false` y mensaje del error.
- ❌ Errores de validación de parámetros (`ReportValidationError` antes del
  `with`) **no** se auditan: hoy se considera ruido funcional, no consulta.
  Si en el futuro se quiere registrar también esos intentos, basta mover el
  `with` antes de `parse_and_validate` y serializar `raw_parametros`.

### Endpoint de consulta

`GET /api/audit/reportes` (admin)

Query params (todos opcionales):

| Param | Tipo | Filtro |
|-------|------|--------|
| `usuario_id` | int | Igualdad |
| `reporte_id` | int | Igualdad |
| `reporte_codigo` | string | Igualdad sobre `reportes.codigo` |
| `desde` | YYYY-MM-DD | `fecha_consulta >= desde 00:00` |
| `hasta` | YYYY-MM-DD | `fecha_consulta <= hasta 23:59:59.999` |
| `resultado_ok` | bool | true/false |
| `limit` | int | default 50, max 200 |
| `offset` | int | default 0 |

Respuesta:

```json
{
  "items": [
    {
      "id": 12,
      "fecha_consulta": "2026-04-30T12:34:56+00:00",
      "usuario": { "id": 1, "email": "admin@reporting.local", "nombre": "Admin" },
      "reporte": { "id": 3, "codigo": "DDJJ_MENUDENCIAS", "nombre": "Declaración Jurada Menudencias" },
      "filtros_json": "{\"fecha_desde\": \"2026-04-01\", ...}",
      "resultado_ok": true,
      "duracion_ms": 145,
      "observaciones": null
    }
  ],
  "total": 1,
  "limit": 50,
  "offset": 0
}
```

Ordenado por `fecha_consulta DESC`.

## Auditoría técnica — corridas ETL

[`app/services/etl/runner.py`](../reporting-api/app/services/etl/runner.py)
escribe en tres tablas:

### `ejecuciones_importacion`

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id` | int | PK |
| `origen` | string | Nombre lógico de la fuente (ej. `TwinsDbQuatro045`) |
| `fecha_desde`, `fecha_hasta` | date | Rango de la corrida |
| `estado` | string | `en_curso`, `ok`, `error` |
| `observaciones` | text | Detalle si falló |
| `created_at` | timestamptz | Inicio de la corrida |
| `created_by_user_id` | FK usuarios | Quién la disparó (puede ser null si fue scheduled) |

### `etl.ejecucion_tablas`

Una fila por **tabla destino procesada** (mercaderías, operarios, tropas,
faena, salidas):

| Columna | Tipo |
|---------|------|
| `tabla_destino` | string |
| `filas_leidas` | int |
| `filas_insertadas` | int |
| `filas_actualizadas` | int |
| `filas_descartadas` | int |
| `duracion_ms` | int |
| `creado_en` | timestamptz |

### `etl.ejecucion_errores`

Errores fila a fila durante un paso:

| Columna | Tipo |
|---------|------|
| `tabla_destino` | string |
| `source_pk` | string (PK de origen, si se conoce) |
| `mensaje` | text |
| `payload` | jsonb |
| `ocurrido_en` | timestamptz |

### Endpoints

- `POST /api/etl/run` (admin) — dispara una corrida con
  `{desde, hasta, origen, source}`. `source` puede ser `empty` (in-memory) o
  `mssql` (real). Devuelve resumen 202 con el detalle de cada paso.
- `GET /api/etl/ejecuciones/<id>` (admin) — detalle completo de una corrida
  (cabecera + tablas + errores).
- `GET /api/audit/etl-ejecuciones` (admin) — listado con filtros (origen,
  estado, rango de fechas, paginado).

## Criterios de trazabilidad adoptados

1. **Una sola fila por corrida funcional**, sin importar cuántas secciones
   o consultas internas haga el reporte. Esto mantiene la auditoría legible.
2. **Tiempo medido en backend** (`time.perf_counter`), no en cliente, para
   evitar ruido de red.
3. **Mensajes de error acotados** a 500 caracteres en `observaciones`.
   Suficiente para diagnóstico, no leak excesivo de datos.
4. **Parámetros serializados como JSON seguro** (`_safe_json_dumps`):
   `date`/`datetime` → `isoformat`, otros tipos → `str`. Si la serialización
   falla, se guarda `"{}"` en vez de romper la auditoría.
5. **Auditoría siempre se commitea**, incluso ante error. La excepción
   original se re-lanza para que el handler de la ruta devuelva el HTTP
   adecuado (500 / 400 / etc.).
6. **Admin-only**: la lectura de auditoría no es para usuarios finales.
7. **Concurrencia ETL**: el runner toma un advisory lock de PostgreSQL
   (`pg_try_advisory_lock`) para que no haya dos corridas simultáneas. Si
   ya hay una, devuelve `409 EtlAlreadyRunning`.

## Pendientes / mejoras sugeridas

- **Auditoría de operaciones administrativas** (alta/baja de usuarios,
  cambios de roles, modificaciones de visibilidad de reportes): hoy no se
  registran. Sería natural una tabla `auditoria_admin` con
  `(usuario_id, accion, entidad, entidad_id, payload_antes, payload_despues)`.
- **Retención**: definir política de purga / archivado de
  `auditorias_consultas_reportes` y `etl.ejecucion_*` para mantener acotado
  el volumen.
- **Exportación de auditoría** (CSV/Excel) para auditores externos.
