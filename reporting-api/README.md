# reporting-api

Scaffolding inicial del backend de reporting usando **Python 3.12 + Flask**.

## Alcance de esta etapa

Incluye:

- app factory
- configuración por ambiente con variables de entorno
- conexión a base de datos (PostgreSQL por defecto)
- modelos iniciales de usuarios, roles, reportes, auditoría e importaciones
- migración inicial
- endpoints placeholder para health, auth, usuarios, roles y reportes
- CORS para frontend local

No incluye todavía:

- lógica específica de DDJJ
- integración real con legacy
- exportaciones
- permisos complejos
- reglas avanzadas de negocio

## Estructura

```text
reporting-api/
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── extensions.py
│   ├── models/
│   ├── routes/
│   ├── services/
│   ├── schemas/
│   └── utils/
├── migrations/
├── run.py
├── .env.example
├── requirements.txt
└── README.md
```

## Requisitos

- Python 3.12
- PostgreSQL

## Puesta en marcha

1. Crear y activar entorno virtual:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

2. Instalar dependencias:

```bash
pip install -r requirements.txt
```

3. Configurar variables de entorno:

```bash
cp .env.example .env
```

4. Crear base de datos (ejemplo local):

```sql
CREATE DATABASE reporting_api;
```

5. Ejecutar migraciones:

```bash
flask --app run.py db upgrade
```

6. Levantar API:

```bash
python run.py
```

## Endpoints placeholder iniciales

- `GET /api/health`
- `POST /api/auth/login`
- `GET /api/users`
- `POST /api/users`
- `GET /api/roles`
- `GET /api/reports`
- `GET /api/reports/<report_id>`

## Próximos pasos recomendados

1. Implementar login real (`JWT`) con hash de password y refresh tokens.
2. Completar ABM de usuarios con validaciones y paginación.
3. Agregar ABM de roles y asignación de reportes por rol.
4. Implementar autorización simple por claims/roles.
5. Crear capa de servicios para conexión a base intermedia de reporting.
6. Agregar versionado de API y manejo uniforme de errores.
