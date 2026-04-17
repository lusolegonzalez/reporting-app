# reporting-web

Scaffolding inicial del frontend para un sistema de reporting usando **React + TypeScript + Vite**.

## Qué incluye esta primera fase

- Router base con rutas públicas y privadas.
- Layout principal con navegación lateral mínima.
- Páginas placeholder:
  - Login
  - Dashboard
  - Usuarios (ABM inicial)
  - Reportes
- Cliente API centralizado con Axios.
- Estructura de carpetas simple y mantenible.

## Stack

- React
- TypeScript
- Vite
- React Router
- Axios

## Estructura

```text
reporting-web/
├─ src/
│  ├─ api/
│  ├─ components/
│  ├─ hooks/
│  ├─ layouts/
│  ├─ pages/
│  ├─ routes/
│  ├─ types/
│  ├─ utils/
│  ├─ main.tsx
│  └─ styles.css
├─ .env.example
├─ index.html
├─ package.json
├─ tsconfig.app.json
├─ tsconfig.json
├─ tsconfig.node.json
└─ vite.config.ts
```

## Cómo levantar el proyecto

1. Instalar dependencias:

```bash
npm install
```

2. Crear archivo `.env` a partir de `.env.example`:

```bash
cp .env.example .env
```

3. Ejecutar entorno de desarrollo:

```bash
npm run dev
```

4. Compilar para producción:

```bash
npm run build
```

## Variables de entorno

- `VITE_API_BASE_URL`: URL base del backend.

## Qué faltaría en próximas iteraciones

- Integrar autenticación real con backend.
- Implementar lógica real de ABM de usuarios.
- Implementar listado real de reportes con datos de API.
- Agregar manejo de errores y estados de carga globales.
- Definir permisos más granulares por rol.
