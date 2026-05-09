# reporting-web

Frontend base con **React + TypeScript + Vite**.

> Documentación integral del sistema en [`../docs/`](../docs)
> ([arquitectura](../docs/architecture.md), [seguridad](../docs/security.md),
> [reporting](../docs/reporting.md), [auditoría](../docs/audit.md),
> [instalación](../docs/installation.md)). Este README mantiene el quickstart
> del frontend.

## Requisitos

- Node.js 20+
- Backend `reporting-api` corriendo en `http://localhost:5000`

## Variables de entorno

Copiar archivo de ejemplo:

```bash
cp .env.example .env
```

Variable usada:

- `VITE_API_BASE_URL` (por defecto `http://localhost:5000/api`)

## Levantar frontend

1. Instalar dependencias:

```bash
npm install
```

2. Ejecutar entorno local:

```bash
npm run dev
```

Frontend disponible en `http://localhost:5173`.

## Verificar consumo de `/health`

Con backend levantado, al abrir Dashboard el frontend hace `GET /health` usando `VITE_API_BASE_URL`.

También se puede validar desde terminal:

```bash
curl http://localhost:5173
```

Y en navegador (Network tab) debe verse request a:

- `http://localhost:5000/api/health`

Si responde OK, en pantalla aparece estado del backend (`reporting-api - ok`).
