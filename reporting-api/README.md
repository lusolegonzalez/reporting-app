# reporting-api

Backend base de reporting con **Flask + PostgreSQL**.

## Objetivo de esta base

- Levantar API Flask localmente.
- Conectar contra PostgreSQL por variables de entorno.
- Aplicar migración inicial con Flask-Migrate.
- Exponer endpoint de salud `GET /api/health`.
- Habilitar CORS para frontend local (`http://localhost:5173` por defecto).

## Requisitos

- Python 3.10+ (recomendado 3.12)
- PostgreSQL 14+ ejecutándose en local

## Variables de entorno

Copiar el archivo de ejemplo:

```bash
cp .env.example .env
```

Variables usadas:

- `DATABASE_URL` (obligatoria):
  - ejemplo: `postgresql+psycopg2://postgres:postgres@localhost:5432/reporting_api`
- `CORS_ORIGINS`:
  - por defecto: `http://localhost:5173,http://localhost:3000`
- `SECRET_KEY`
- `JWT_SECRET_KEY`

## Levantar backend paso a paso

1. Crear y activar entorno virtual:

```bash
python -m venv .venv
source .venv/bin/activate
```

2. Instalar dependencias:

```bash
pip install -r requirements.txt
```

3. Crear base de datos en PostgreSQL:

```sql
CREATE DATABASE reporting_api;
```

4. Ejecutar migración inicial:

```bash
flask --app run.py db upgrade
```

5. Levantar servidor Flask:

```bash
python run.py
```

La API queda disponible en `http://localhost:5000`.

## Verificaciones rápidas

### Health endpoint

```bash
curl http://localhost:5000/api/health
```

Respuesta esperada:

```json
{"service":"reporting-api","status":"ok"}
```

### Verificar CORS para frontend local

```bash
curl -i -H "Origin: http://localhost:5173" http://localhost:5000/api/health
```

Esperado en headers: `Access-Control-Allow-Origin: http://localhost:5173`

## Endpoints placeholder

- `GET /api/health`
- `POST /api/auth/login`
- `GET /api/users`
- `POST /api/users`
- `GET /api/roles`
- `GET /api/reports`
- `GET /api/reports/<report_id>`
