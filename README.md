# reporting-app

Plataforma de reporting para producción frigorífica. Compuesta por:

- **`reporting-api/`** — Backend Flask (Python) que expone autenticación, ABM
  de usuarios/roles, ejecución de reportes y auditoría.
- **`reporting-web/`** — Frontend React + TypeScript + Vite.
- **PostgreSQL intermedia** — base operacional del sistema (auth, permisos,
  staging y core para reporting, auditoría).
- **SQL Server origen (solo lectura)** — Twins PI4 (`TwinsDbQuatro045`),
  consumido por el ETL para alimentar la base intermedia.

## Documentación

| Documento | Tema |
|-----------|------|
| [docs/architecture.md](docs/architecture.md) | Arquitectura general, capas, modelo de datos, flujo de un request |
| [docs/security.md](docs/security.md) | Auth JWT, roles, permisos por reporte, exportación, guards |
| [docs/reporting.md](docs/reporting.md) | Concepto del módulo de reportes, metadata, contratos, DDJJ Menudencias |
| [docs/audit.md](docs/audit.md) | Auditoría funcional y técnica, trazabilidad, endpoints de consulta |
| [docs/installation.md](docs/installation.md) | Variables de entorno, base de datos, migraciones, ejecución y despliegue básico |
| [reporting-api/README.md](reporting-api/README.md) | Quickstart backend |
| [reporting-web/README.md](reporting-web/README.md) | Quickstart frontend |

## Quickstart

```bash
# Backend
cd reporting-api
python -m venv .venv && source .venv/bin/activate   # Linux/macOS
# o: .venv\Scripts\Activate.ps1                      # Windows
pip install -r requirements.txt
cp .env.example .env
flask --app run.py db upgrade
flask --app run.py seed-initial-auth
python run.py

# Frontend (otra terminal)
cd reporting-web
cp .env.example .env
npm install
npm run dev
```

- Backend en `http://localhost:5000`
- Frontend en `http://localhost:5173`
- Usuario inicial: `admin@reporting.local` / `Admin123*` (ver [docs/security.md](docs/security.md))

## Estado del sistema

| Componente | Estado |
|---|---|
| Auth + JWT + roles + ABM usuarios/roles | Implementado |
| Permisos por reporte (`puede_ver`, `puede_exportar`) | Implementado |
| Base intermedia PostgreSQL + migraciones | Implementado |
| ETL desde SQL Server origen (solo lectura) | Conector implementado, pasos productivos parametrizados |
| Reporting service: registry + contratos + endpoints metadata/run | Implementado |
| DDJJ Menudencias: estructura + parámetros + alertas | Implementado (consulta SQL final pendiente) |
| Auditoría funcional (consultas a reportes) + auditoría técnica (ETL) | Implementado |
| Exportación Excel/PDF | Pendiente: contrato listo, devuelve 501 hasta cablear renderer |
| Tests automatizados | Sólo smoke check CLI (`flask smoke-check`) |

Ver detalles y pendientes en [docs/reporting.md](docs/reporting.md) y [docs/audit.md](docs/audit.md).
