# Reporting

## Concepto general

El módulo de reporting está pensado como una **plataforma**, no como un set
fijo de pantallas. La estructura permite registrar nuevos reportes en el
backend y reutilizar el mismo runner del frontend sin escribir código nuevo
por cada reporte mientras respeten el contrato `ReportDefinition`.

Capas:

```
+-------------------+     metadata + parámetros validados      +---------------------+
|  ReportRunner     |  --------------------------------------> |  ReportDefinition   |
|  (frontend)       |                                          |  (DDJJ_MENUDENCIAS, |
|                   |  <--------------------------------------  |   ...)              |
+-------------------+         ReportResponse (json)            +---------------------+
                                                                          |
                                                                          v
                                                          PostgreSQL intermedia
                                                          (esquemas core / reporting)
```

## Componentes backend

[`app/services/reports/`](../reporting-api/app/services/reports)

### Contratos (`base.py`)

| Tipo | Rol |
|------|-----|
| `ReportParameter` | Descriptor de parámetro (nombre, tipo, requerido, descripcion, valor_por_defecto) |
| `ReportRequest` | Parámetros validados y normalizados de una corrida |
| `ReportSection` | Sección del resultado (codigo, titulo, columnas, filas, totales) |
| `ReportAlerta` | Alerta `info | warning | error` con codigo y mensaje |
| `ReportResponse` | Respuesta estandarizada (secciones + alertas + flags) |
| `ReportDefinition` (Protocol) | Contrato que cada reporte concreto implementa |
| `ReportValidationError` / `ReportPermissionError` / `ReportNotFoundError` | Errores tipados |

### Registry (`registry.py`)

`report_registry` es un singleton donde se registran las implementaciones de
reporte con su `codigo`. Se inicializa en `_bootstrap()` (auto-registro de
los reportes implementados, hoy solo `DDJJ_MENUDENCIAS`).

### Endpoints

| Endpoint | Método | Auth | Body / Query |
|----------|--------|------|--------------|
| `GET /api/reports/by-codigo/<codigo>/metadata` | GET | JWT + `puede_ver` | — |
| `POST /api/reports/by-codigo/<codigo>/run` | POST | JWT + `puede_ver` (+ `puede_exportar` si formato≠json) | `{parametros: {...}, formato: "json"|"excel"|"pdf"}` |

### Metadata (ejemplo)

`GET /api/reports/by-codigo/DDJJ_MENUDENCIAS/metadata`

```json
{
  "codigo": "DDJJ_MENUDENCIAS",
  "nombre": "Declaración Jurada Menudencias",
  "descripcion": "Reporte de producción en carácter de declaración jurada (SENASA). ...",
  "parametros": [
    {"nombre": "fecha_desde", "tipo": "date", "requerido": true,  "descripcion": "...", "valor_por_defecto": null},
    {"nombre": "fecha_hasta", "tipo": "date", "requerido": true,  "descripcion": "...", "valor_por_defecto": null},
    {"nombre": "mostrar_tropas", "tipo": "bool", "requerido": false, "descripcion": "...", "valor_por_defecto": false}
  ],
  "permisos": { "puede_ver": true, "puede_exportar": true },
  "formatos_disponibles": { "json": true, "excel": true, "pdf": true }
}
```

### Respuesta de ejecución (`ReportResponse`)

```json
{
  "codigo_reporte": "DDJJ_MENUDENCIAS",
  "nombre_reporte": "Declaración Jurada Menudencias",
  "parametros": { "fecha_desde": "2026-04-01", "fecha_hasta": "2026-04-30", "mostrar_tropas": false },
  "secciones": [
    {
      "codigo": "diaria",
      "titulo": "Producción diaria",
      "columnas": [
        {"key": "codigo", "titulo": "Código Producto", "tipo": "string"},
        {"key": "descripcion", "titulo": "Descripción", "tipo": "string"},
        {"key": "cajas", "titulo": "Cajas", "tipo": "number"},
        {"key": "kg_neto", "titulo": "Kg. Neto", "tipo": "number"}
      ],
      "filas": [],
      "totales": {"cabezas_faenadas": 0, "cajas": 0, "kg_neto": 0.0, "tropas": []}
    },
    { "codigo": "decomisos", "titulo": "Decomisos ...", "columnas": [...], "filas": [], "totales": {} },
    { "codigo": "mensual",   "titulo": "Mensual ...",   "columnas": [...], "filas": [], "totales": {} }
  ],
  "alertas": [
    { "nivel": "info", "codigo": "CONSISTENCIA_PENDIENTE", "mensaje": "..." }
  ],
  "export_permitido": { "excel": true, "pdf": true },
  "generado_en": "2026-04-30T12:00:00",
  "es_placeholder": true
}
```

`es_placeholder=true` indica que las filas todavía no provienen de la query
final (se conectará al cerrar la consulta SQL). El frontend lo muestra como
nota visible.

## DDJJ Menudencias

[`app/services/reports/ddjj_menudencias.py`](../reporting-api/app/services/reports/ddjj_menudencias.py)

### Origen funcional

Relevamiento en [documentation/Menudencias Relevamiento.md](../documentation/Menudencias%20Relevamiento.md).

- Solicitante: Julieta Suárez (14/04/2026).
- Generador del reporte original: Matías Chiari.
- Destinatario: SENASA.
- Carácter: Declaración Jurada de producción.
- Reportes de origen (Twins PI4):
  - **PWR054** Consulta Producción → Menudencias / Decomiso, Salida, sin stock.
  - **PWR109** Faena por Usuario → Tropas y cabezas.

### Parámetros soportados

| Nombre | Tipo | Requerido | Default | Validación |
|--------|------|-----------|---------|------------|
| `fecha_desde` | date (YYYY-MM-DD) | sí | — | formato válido |
| `fecha_hasta` | date (YYYY-MM-DD) | sí | — | `fecha_hasta >= fecha_desde` |
| `mostrar_tropas` | bool | no | `false` | sólo se aplica si `fecha_desde == fecha_hasta` |

Restricción adicional: `(fecha_hasta - fecha_desde).days + 1 <= 366` para
evitar rangos absurdos (`MAX_DIAS_RANGO`).

### Secciones

| Código | Cuándo | Contenido |
|--------|--------|-----------|
| `diaria` | siempre | Producción del día (si rango = 1 día) o producción agregada diaria |
| `decomisos` | siempre | Decomisos del rango |
| `mensual` | siempre | Acumulado mensual del rango |

Columnas de producción:

- `codigo` (string)
- `descripcion` (string)
- `cajas` (number)
- `kg_neto` (number)

### Reglas de negocio implementadas

- `mostrar_tropas` solo aplica a reportes diarios. Si el usuario lo solicita
  con un rango mayor, se ignora silenciosamente y se devuelve la alerta
  `TROPAS_SOLO_DIARIO` (warning).
- Se devuelve siempre una alerta `CONSISTENCIA_PENDIENTE` (info) avisando
  que la validación cruzada menudencias/cabezas faenadas se conecta al
  cerrar la consulta SQL final.

### Restricciones funcionales conocidas (pendientes)

1. **Consulta SQL final**: el cuerpo de `_build_secciones` devuelve filas
   vacías. Cuando esté la query definitiva contra `core.*` / `reporting.*`,
   solo se reemplaza ese método.
2. **Eliminación de tropas duplicadas** (regla del relevamiento): pendiente
   hasta cablear la query.
3. **Validación de consistencia menudencias vs cabezas faenadas**: pendiente.
4. **Exportación a Excel** (formato oficial pedido por SENASA): el contrato
   está; el endpoint devuelve `501` con el JSON adjunto hasta cablear el
   renderer (openpyxl o similar). Misma situación con PDF.

## Frontend — `ReportRunner`

[`src/components/ReportRunner.tsx`](../reporting-web/src/components/ReportRunner.tsx)

Componente único usado por todos los reportes. Recibe `codigo` y resuelve:

1. `getReportMetadataRequest(codigo)` para parámetros + permisos.
2. Renderiza inputs según `tipo` (`date` → input date, `bool` → checkbox,
   `int` → input number, `string` → input text).
3. Botón "Consultar" → `runReportRequest(codigo, {parametros, formato:"json"})`.
4. Botones "Exportar Excel" / "Exportar PDF" sólo si
   `permisos.puede_exportar=true` y el formato está disponible. Si vuelve
   `501`, muestra un aviso con el mensaje del backend.
5. Resultado:
   - Tarjeta resumen (nombre, generado_en, parámetros, aviso de placeholder).
   - Lista de alertas con estilos `info`/`warning`/`error`.
   - Una tabla por sección. Si la sección no tiene filas, muestra "Sin datos
     para los parámetros indicados".

`ReportDetailPage` despacha al runner solo si el reporte está activo y el
usuario tiene permiso de verlo.

## Cómo agregar un nuevo reporte

1. Crear un módulo en `app/services/reports/` que implemente
   `ReportDefinition` (atributos `codigo`, `nombre`, `descripcion`,
   `parametros` y métodos `parse_and_validate`, `execute`).
2. Registrar la clase en `_bootstrap()` de
   [`registry.py`](../reporting-api/app/services/reports/registry.py).
3. Crear el `Reporte` en la base con su `codigo`. El comando
   `flask --app run.py seed-initial-auth` puede ser un buen lugar para
   seedearlo si es estructural.
4. Asignar permiso a los roles correspondientes desde la UI admin de
   visibilidad.
5. **No hace falta tocar el frontend**: el `ReportRunner` lo levanta a
   partir de la metadata.
