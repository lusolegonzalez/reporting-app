# Manual de usuario — Portal de Reporting

Este manual describe cómo usar el portal web de reporting tal como está
implementado hoy. Está pensado para usuarios funcionales (consultan
reportes) y para administradores (configuran usuarios, roles y
visibilidad).

---

## 1. Acceso al portal

1. Abrir el navegador en la dirección que provee el área de sistemas
   (por ejemplo `http://localhost:5173` en entorno local).
2. Se muestra la pantalla **Login**.
3. Ingresar:
   - **Email**: el correo asociado a la cuenta.
   - **Password**: la contraseña asignada.
4. Presionar **Ingresar**.

Si las credenciales son correctas, el portal redirige automáticamente al
**Dashboard**. Si fallan, aparece un mensaje de error debajo del
formulario (por ejemplo, "Credenciales inválidas" o "Usuario inactivo").

> La sesión se mantiene activa hasta que se cierra explícitamente con
> **Cerrar sesión** o hasta que vence el token. Si vence, el portal
> vuelve a la pantalla de Login automáticamente.

---

## 2. Navegación general

Una vez dentro, la pantalla se divide en dos áreas:

- **Barra lateral izquierda**: menú principal y datos de la sesión.
- **Área central**: contenido de la opción seleccionada.

### Menú principal

| Opción | Disponible para | Función |
|---|---|---|
| Dashboard | Todos los usuarios | Vista general y estado del backend |
| Reportes | Todos los usuarios | Listado y ejecución de reportes |
| Usuarios | Solo administradores | Alta y administración de cuentas |
| Roles | Solo administradores | Alta y administración de roles y permisos |

> Las opciones **Usuarios** y **Roles** sólo aparecen si la cuenta tiene
> el rol `ADMIN`. Un usuario funcional no las ve.

En la parte inferior de la barra lateral está el botón **Cerrar sesión**.

---

## 3. Dashboard

Es la primera pantalla luego del login. Muestra:

- Nombre y email del usuario en sesión.
- Estado de conexión con el backend (`reporting-api - ok` si responde).

Sirve como verificación rápida de que el sistema está operativo.

---

## 4. Pantalla de Reportes

Acceder desde el menú lateral en **Reportes**.

Se muestra una tabla con los reportes disponibles:

| Columna | Descripción |
|---|---|
| Nombre | Nombre funcional del reporte |
| Código | Código técnico del reporte (ej. `DDJJ_MENUDENCIAS`) |
| Descripción | Descripción breve |
| Estado *(solo admin)* | Activo / Inactivo |
| Acciones | Botón **Ver** y, para admin, **Editar** |

### Qué reportes ve cada perfil

- **Usuario funcional**: sólo los reportes activos para los que su rol
  tiene permiso de visualización. Si no tiene ninguno asignado, aparece
  el mensaje *"No tenés reportes disponibles asignados a tu rol."*
- **Administrador**: ve todos los reportes configurados en el sistema,
  activos e inactivos.

### Acciones disponibles

- **Ver** — abre el detalle del reporte para consultarlo.
- **Editar** *(solo admin)* — permite modificar el reporte y configurar
  visibilidad por rol.
- **Nuevo reporte** *(solo admin)* — botón en la cabecera para dar de
  alta un reporte.

---

## 5. Consulta de un reporte

Al presionar **Ver** en un reporte se abre la pantalla de detalle, dividida en:

1. **Encabezado**: nombre y descripción del reporte.
2. **Parámetros**: formulario con los campos requeridos por ese reporte.
3. **Resultado** (al ejecutar): resumen, alertas y secciones de datos.

### Pasos para consultar

1. Completar los parámetros. Los marcados con `*` son obligatorios.
2. Presionar **Consultar**.
3. Esperar el resultado. Mientras se procesa, el botón muestra
   "Consultando…".
4. Si la consulta es válida, aparecen:
   - **Resumen**: nombre del reporte, fecha y hora de generación,
     parámetros usados.
   - **Alertas** (si las hay): mensajes informativos o de advertencia.
   - **Secciones de datos**: una o varias tablas con las filas
     resultantes. Si una sección no tiene resultados, indica
     *"Sin datos para los parámetros indicados."*
5. Si hay un error, se muestra debajo del formulario (por ejemplo,
   parámetro inválido o reporte sin permiso).

### Mensajes habituales

- *"Sin datos para los parámetros indicados."* — la consulta se ejecutó
  correctamente pero no hay registros para esos filtros.
- *"El reporte se encuentra inactivo."* — el administrador deshabilitó
  el reporte.
- *"Sin permiso para visualizar este reporte."* — falta asignación de
  permiso al rol del usuario.

---

## 6. Reporte DDJJ Menudencias

Reporte para la **Declaración Jurada de producción** dirigida a SENASA.

### Parámetros

| Parámetro | Tipo | Obligatorio | Descripción |
|---|---|---|---|
| `fecha_desde` | Fecha | Sí | Inicio del rango a consultar |
| `fecha_hasta` | Fecha | Sí | Fin del rango. Debe ser igual o posterior a `fecha_desde` |
| `mostrar_tropas` | Sí / No | No | Solo aplica cuando `fecha_desde` y `fecha_hasta` son el mismo día |

### Validaciones

- `fecha_hasta` no puede ser anterior a `fecha_desde`.
- El rango total no puede superar 366 días.
- Si se marca `mostrar_tropas` para un rango mayor a un día, el sistema
  ignora la opción y devuelve una alerta informando la situación.

### Secciones del resultado

| Código | Contenido |
|---|---|
| `diaria` | Producción diaria (relevante cuando se consulta un único día) |
| `decomisos` | Decomisos del rango |
| `mensual` | Acumulado mensual del rango |

Columnas: `Código Producto`, `Descripción`, `Cajas`, `Kg. Neto`.

### Alertas posibles

- **TROPAS_SOLO_DIARIO** *(advertencia)*: se solicitó mostrar tropas en
  un rango mayor a un día; la opción se ignoró.
- **CONSISTENCIA_PENDIENTE** *(informativa)*: aviso de que la validación
  cruzada entre menudencias y cabezas faenadas se cerrará junto con la
  consulta SQL final.

> Estado actual: la estructura, parámetros, alertas y permisos están
> operativos. La carga de filas reales se conecta cuando se cierre la
> consulta SQL definitiva contra la base intermedia.

---

## 7. Restricciones por permisos

El acceso se controla por **rol**. Un mismo usuario puede tener uno o
más roles. Cada rol define, para cada reporte:

- **Puede ver** — habilita ver el reporte y consultarlo en pantalla.
- **Puede exportar** — habilita los botones de exportación. Sólo aplica
  si además tiene "Puede ver".

Reglas prácticas:

- Si ningún rol del usuario tiene permiso sobre un reporte, ese reporte
  no aparece en el listado.
- Si un usuario intenta acceder por URL directa a un reporte sin
  permiso, el portal muestra un error de autorización.
- Las opciones administrativas (Usuarios, Roles, edición de reportes,
  configuración de visibilidad, ETL, auditoría) están reservadas al rol
  `ADMIN`.

---

## 8. Exportaciones

Dentro de la pantalla de un reporte, además del botón **Consultar**,
pueden aparecer botones adicionales:

- **Exportar Excel**
- **Exportar PDF**

Condiciones:

- Sólo se muestran si el rol del usuario tiene **Puede exportar**
  habilitado para ese reporte.
- Sólo se muestran si el reporte declara ese formato como disponible.

> Estado actual: el contrato de exportación está implementado y los
> botones aparecen cuando el perfil lo permite. El renderizado a Excel y
> PDF aún no está disponible: al presionar el botón, el sistema muestra
> el mensaje *"La exportación a EXCEL/PDF aún no está disponible."*
> hasta que se habilite el generador definitivo. Mientras tanto, la
> consulta en pantalla (formato JSON) sí funciona normalmente.

---

## 9. Gestión de usuarios y roles (perfil administrador)

Las siguientes pantallas solo están disponibles para usuarios con rol
`ADMIN`.

### Usuarios

Acceso desde el menú lateral en **Usuarios**.

Permite:

- Listar todos los usuarios con nombre, email, estado y roles.
- Crear un nuevo usuario (botón **Nuevo usuario**).
- Editar un usuario existente (nombre, email, password, roles).
- Activar o desactivar un usuario (botón en la fila). Un usuario
  inactivo no puede iniciar sesión.

### Roles

Acceso desde el menú lateral en **Roles**.

Permite:

- Listar y crear roles.
- Editar un rol (nombre y descripción).

### Visibilidad de un reporte por rol

Desde el listado **Reportes**, presionar **Editar** en un reporte y
acceder a la sección de visibilidad. Para cada rol existente:

- **Puede ver** — habilita la consulta del reporte.
- **Puede exportar** — habilita la exportación. Si se desmarca
  *"Puede ver"*, también se desmarca automáticamente *"Puede exportar"*.

Los cambios se guardan al confirmar la pantalla. A partir de ese
momento, los usuarios de cada rol verán o dejarán de ver el reporte
según corresponda.

### Buenas prácticas administrativas

- Asignar permisos a **roles**, no a usuarios individuales.
- Mantener el rol `ADMIN` reservado a un grupo acotado.
- Desactivar usuarios que dejan la organización en lugar de borrarlos,
  para preservar la trazabilidad de las consultas históricas.
- Cambiar el password del usuario administrador inicial luego de la
  puesta en marcha.

---

## 10. Cierre de sesión

Presionar **Cerrar sesión** en la barra lateral. El portal vuelve a la
pantalla de Login y se descarta la sesión local. Toda actividad
posterior requiere ingresar nuevamente las credenciales.

---

## Resumen final

Este manual cubre el uso real del portal de reporting en su estado
actual:

- **Para el usuario funcional**: cómo ingresar, ubicar los reportes
  habilitados para su rol, consultarlos (incluido el reporte DDJJ
  Menudencias), entender las alertas y, si su perfil lo permite,
  solicitar exportaciones.
- **Para el administrador funcional**: además de lo anterior, cómo
  administrar usuarios, roles y la visibilidad de cada reporte por rol,
  incluyendo la habilitación o restricción de exportaciones.

Funcionalidades fuera de alcance de este manual (operación de ETL,
consulta de auditoría técnica, despliegue, configuración de variables
de entorno) están documentadas en el material técnico bajo la carpeta
[`docs/`](.) del repositorio.
