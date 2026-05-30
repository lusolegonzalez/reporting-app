# Manual de usuario — Portal de Reporting

Este manual describe cómo usar el portal web de reporting en su estado
actual. Está dirigido a usuarios funcionales (consultan reportes) y a
administradores (gestionan usuarios, roles, visibilidad de reportes y
actualización de datos).

---

## 1. Introducción

El portal de reporting permite consultar información de producción
generada en la planta y presentarla de forma estructurada para su
análisis o presentación ante organismos como SENASA.

El sistema está compuesto por:

- **Portal web**: interfaz de usuario accesible desde el navegador.
- **Backend (API)**: procesa las consultas y aplica las reglas de
  negocio.
- **Base intermedia (PostgreSQL)**: almacena los datos ya procesados
  que usa el portal.
- **Fuente de datos (SQL Server / Twins)**: origen de los datos de
  producción. Los datos se traen manualmente mediante el proceso ETL.

> **Punto clave**: los datos del portal no se actualizan solos. Un
> administrador debe ejecutar el ETL manualmente para traer información
> nueva desde el sistema fuente (Twins). Si el reporte no muestra datos,
> lo primero a verificar es si se corrió el ETL para ese rango de fechas.

---

## 2. Acceso al sistema

### Dirección

En el entorno de Test, ingresar desde el navegador a la dirección
interna provista por el área de sistemas. Ejemplo:

```
http://IP_DEL_SERVIDOR:8523/login
```

En entorno local de desarrollo, la dirección habitual es
`http://localhost:5173`.

### Inicio de sesión

1. Se muestra la pantalla **Login**.
2. Ingresar:
   - **Email**: el correo asociado a la cuenta.
   - **Password**: la contraseña asignada.
3. Presionar **Ingresar**.

Si las credenciales son correctas, el portal redirige al **Dashboard**.
Si fallan, aparece un mensaje de error debajo del formulario (por
ejemplo, "Credenciales inválidas" o "Usuario inactivo").

> La sesión se mantiene activa hasta que se cierra explícitamente con
> **Cerrar sesión** o hasta que vence el token. Si vence, el portal
> vuelve automáticamente a la pantalla de Login.

### Cierre de sesión

Presionar **Cerrar sesión** en la parte inferior de la barra lateral.
El portal vuelve al Login y descarta la sesión. Toda actividad posterior
requiere ingresar nuevamente las credenciales.

---

## 3. Navegación general

Una vez dentro, la pantalla se divide en dos áreas:

- **Barra lateral izquierda**: menú principal y datos de la sesión.
- **Área central**: contenido de la opción seleccionada.

### Menú principal

| Opción | Disponible para | Función |
|---|---|---|
| Dashboard | Todos los usuarios | Vista general y estado del sistema |
| Reportes | Todos los usuarios | Listado y ejecución de reportes |
| ETL | Solo administradores | Actualización manual de datos |
| Usuarios | Solo administradores | Alta y administración de cuentas |
| Roles | Solo administradores | Alta y administración de roles y permisos |

> Las opciones **ETL**, **Usuarios** y **Roles** sólo aparecen si la
> cuenta tiene el rol `ADMIN`. Un usuario funcional no las ve.

### Dashboard

Es la primera pantalla luego del login. Muestra el nombre y email del
usuario en sesión, y el estado de conexión con el backend
(`reporting-api - ok` si responde). Sirve como verificación rápida de
que el sistema está operativo.

---

## 4. Actualización de datos (ETL)

> Esta pantalla está disponible **solo para administradores**.

### ¿Para qué sirve?

El ETL es el proceso que trae datos desde el sistema fuente (SQL Server /
Twins) hacia la base intermedia del portal. Sin ejecutarlo, el portal no
tiene información nueva para mostrar en los reportes.

El proceso no es automático ni continuo: **debe iniciarse manualmente**
cada vez que se necesite actualizar los datos. Puede ejecutarse tantas
veces como sea necesario; el sistema no duplica registros por
solapamiento de rangos.

### Cómo ejecutar el ETL

1. Acceder a **ETL** desde el menú lateral.
2. Completar el formulario:

| Campo | Descripción |
|---|---|
| **Desde** | Fecha de inicio del rango a importar (formato dd/MM/yyyy en la UI) |
| **Hasta** | Fecha de fin del rango a importar |
| **Origen (DB)** | Nombre de la base de datos fuente. Por defecto: `TwinsDbQuatro045` |
| **Source** | Origen de los datos. Usar **SQL Server (Twins)** para datos reales |

3. Presionar **Ejecutar ETL**.
4. El botón muestra **"Ejecutando…"** mientras el proceso corre. Esperar
   a que finalice antes de cerrar la pantalla.

> La corrida corre y termina: no queda ejecutándose en segundo plano.
> Una vez que el botón vuelve a estar disponible, el proceso terminó.

### Interpretar el resultado

Cuando finaliza, aparece un resumen de la ejecución:

- **ID de ejecución**: número identificador de esa corrida.
- **Estado**: `ok` si todo fue correcto, `error` si algo falló.
- **Totales**: filas leídas, insertadas, actualizadas, descartadas y
  errores.
- **Detalle por tabla**: desglose del resultado para cada entidad
  importada (mercaderías, operarios, tropas, faena, salidas).

Si hubo errores en alguna tabla, aparece un apartado desplegable con el
detalle de cada fila que no pudo procesarse.

### Qué implica una corrida exitosa

Una corrida con estado `ok` significa que los datos del rango
seleccionado fueron importados correctamente y que las vistas del
portal están actualizadas.

Que la corrida sea exitosa **no garantiza** que el reporte devuelva
datos para cualquier rango: solo asegura que los datos de *ese rango*
están disponibles. Si se consulta un período para el que no se corrió
el ETL, el reporte mostrará secciones vacías.

### Opción "Source: Vacío (validación)"

Esta opción ejecuta el proceso sin conectarse a Twins. Se usa para
verificar que la maquinaria funciona correctamente sin modificar datos.
**No importar datos reales con esta opción.**

---

## 5. Pantalla de Reportes

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

## 6. Consulta de un reporte

Al presionar **Ver** en un reporte se abre la pantalla de detalle,
dividida en:

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
     resultantes. Si una sección no tiene filas, indica
     *"Sin datos para los parámetros indicados."*
5. Si hay un error, se muestra debajo del formulario.

### Mensajes habituales

- *"Sin datos para los parámetros indicados."* — la consulta se ejecutó
  correctamente pero no hay registros para esos filtros. Verificar si se
  corrió el ETL para ese rango.
- *"El reporte se encuentra inactivo."* — el administrador deshabilitó
  el reporte.
- *"Sin permiso para visualizar este reporte."* — falta asignación de
  permiso al rol del usuario.

---

## 7. Reporte DDJJ Menudencias

Reporte de **Declaración Jurada de producción** para SENASA. Lee datos
reales desde la base intermedia, actualizada por el ETL.

### Cómo acceder

Desde el menú lateral, ingresar a **Reportes** y presionar **Ver** en
el reporte `DDJJ_MENUDENCIAS`.

### Parámetros

| Parámetro | Tipo | Obligatorio | Descripción |
|---|---|---|---|
| Fecha desde | Fecha | Sí | Inicio del rango a consultar |
| Fecha hasta | Fecha | Sí | Fin del rango. Debe ser igual o posterior a "Fecha desde" |
| Mostrar tropas | Sí / No | No | Incluye el listado de tropas. Solo aplica cuando ambas fechas son el mismo día |

Las fechas se ingresan en formato **dd/MM/yyyy** a través del selector de
fecha del navegador.

### Validaciones

- "Fecha hasta" no puede ser anterior a "Fecha desde".
- El rango no puede superar 366 días.
- Si se activa "Mostrar tropas" para un rango mayor a un día, el sistema
  ignora la opción y devuelve una alerta informando la situación.

### Secciones del resultado

El reporte devuelve tres secciones. Todas muestran columnas:
**Código Producto**, **Descripción**, **Cajas**, **Kg. Neto**.

#### Producción del día (`diaria`)

Solo se puebla cuando ambas fechas son el mismo día. Muestra la
producción de menudencias para esa jornada, junto con el total de
cabezas faenadas. Si se activó "Mostrar tropas", también aparece el
listado de tropas con sus cabezas.

#### Decomisos (`decomisos`)

Muestra los decomisos registrados en el rango consultado, agrupados por
código de producto. Incluye el total de cabezas faenadas del período.

#### Acumulado del rango (`mensual`)

Muestra el acumulado de producción de menudencias por código de producto
para todo el rango. Incluye el total de cabezas faenadas del período.

### Alertas posibles

| Código | Nivel | Significado |
|---|---|---|
| `TROPAS_SOLO_DIARIO` | Advertencia | Se pidió mostrar tropas en un rango mayor a un día; la opción se ignoró |
| `EXCEDE_CABEZAS` | Advertencia | Hay días en los que la cantidad de cajas de menudencias supera a las cabezas faenadas |

### Qué significa que no haya datos

Si una sección aparece vacía, puede deberse a:

1. **No se corrió el ETL para ese rango**: la base intermedia no tiene
   datos de esas fechas. Solución: ejecutar el ETL para el período
   correspondiente y volver a consultar.
2. **No hubo producción en ese período**: el ETL se corrió correctamente
   pero no existían registros en la fuente para esas fechas.

Que una sección esté vacía no es un error del sistema; es información
válida que refleja el estado de los datos disponibles.

---

## 8. Exportaciones

Dentro de la pantalla de un reporte pueden aparecer botones adicionales:

- **Exportar Excel**
- **Exportar PDF**

Estos botones solo se muestran si el rol del usuario tiene **Puede
exportar** habilitado para ese reporte y si el reporte declara ese
formato como disponible.

> Estado actual: la funcionalidad de exportación está en proceso de
> habilitación final. La consulta en pantalla funciona con normalidad.

---

## 9. Restricciones por permisos

El acceso se controla por **rol**. Un mismo usuario puede tener uno o
más roles. Cada rol define, para cada reporte:

- **Puede ver** — habilita ver el reporte y consultarlo en pantalla.
- **Puede exportar** — habilita los botones de exportación. Solo aplica
  si además tiene "Puede ver".

Reglas prácticas:

- Si ningún rol del usuario tiene permiso sobre un reporte, ese reporte
  no aparece en el listado.
- Si un usuario intenta acceder por URL directa a un reporte sin
  permiso, el portal muestra un error de autorización.
- Las opciones administrativas (ETL, Usuarios, Roles, edición de
  reportes, configuración de visibilidad) están reservadas al rol
  `ADMIN`.

---

## 10. Gestión de usuarios y roles (perfil administrador)

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
momento, los usuarios de ese rol verán o dejarán de ver el reporte.

### Buenas prácticas administrativas

- Asignar permisos a **roles**, no a usuarios individuales.
- Mantener el rol `ADMIN` reservado a un grupo acotado.
- Desactivar usuarios que dejan la organización en lugar de borrarlos,
  para preservar la trazabilidad de las consultas históricas.
- Cambiar el password del usuario administrador inicial luego de la
  puesta en marcha.

---

## 11. Consideraciones importantes

- **Los datos del portal dependen del ETL.** Si no se actualizaron los
  datos, el reporte mostrará lo que haya en la base intermedia desde la
  última corrida.
- **El ETL es idempotente en datos core**: se puede correr varias veces
  para el mismo rango sin duplicar registros en la base. Los datos de
  auditoría (staging) sí acumulan por corrida.
- **Una corrida exitosa no implica datos en todo rango**: solo garantiza
  que el período importado está disponible. Si el sistema fuente no
  tenía registros para esas fechas, la base intermedia tampoco los
  tendrá.
- **Secciones vacías no son errores**: indican que no hay registros para
  ese período en la base. Verificar si se corrió el ETL o si
  efectivamente no hubo actividad en esas fechas.

---

## 12. Preguntas frecuentes

**No puedo iniciar sesión.**
Verificar que el email y la contraseña sean correctos. Si el mensaje
dice "Usuario inactivo", contactar a un administrador para reactivar la
cuenta. Si el problema persiste, solicitar al administrador que
restablezca la contraseña.

**Ejecuté el ETL pero el reporte sigue sin mostrar datos.**
Verificar que el rango del ETL coincida con el rango consultado en el
reporte. Si no coinciden, ejecutar el ETL para el rango que se quiere
consultar.

**El rango que consulté no devuelve información.**
Puede que no se haya corrido el ETL para esas fechas, o que no haya
habido actividad en la fuente de datos para ese período. Consultar con
el equipo qué fechas tienen datos cargados.

**¿Cuántas veces se puede ejecutar el ETL para el mismo rango?**
Cuantas veces sea necesario. El sistema no duplica datos de producción
por solapamiento de rangos. Cada corrida genera su propio registro de
auditoría.

**¿Qué significa el estado `error` en una corrida ETL?**
Que al menos un paso del proceso encontró un problema. Ver el detalle
de errores en la tabla de resultados para identificar qué tabla y qué
registros fallaron. Los datos que sí se procesaron correctamente quedan
disponibles igualmente.

**¿Por qué la opción "Mostrar tropas" no aparece en el resultado?**
"Mostrar tropas" solo aplica cuando se consulta un único día (fecha
desde igual a fecha hasta). Si el rango abarca más de un día, la opción
se ignora y el sistema genera una alerta informativa.

---

## Resumen

Este manual cubre el uso operativo del portal de reporting:

- **Para el usuario funcional**: cómo ingresar, consultar los reportes
  habilitados para su rol (incluido DDJJ Menudencias), interpretar
  alertas y secciones de resultados.
- **Para el administrador**: además de lo anterior, cómo ejecutar el
  ETL para actualizar los datos, y cómo gestionar usuarios, roles y
  visibilidad de reportes.

Documentación técnica (despliegue, variables de entorno, auditoría,
configuración de infraestructura) está disponible en la carpeta
[`docs/`](.) del repositorio.
