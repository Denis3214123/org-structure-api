# Organizational structure API

Test assignment implementation: REST API for departments (tree) and employees on **FastAPI**, **SQLAlchemy 2**, **PostgreSQL**, **Alembic**, **Docker Compose**.

## Run with Docker

```bash
docker compose up --build
```

API: `http://localhost:8000`  
OpenAPI: `http://localhost:8000/docs`  
Health: `http://localhost:8000/health`

On startup the API container runs `alembic upgrade head`, then `uvicorn`.

## Local development

1. Python 3.12+, PostgreSQL 16 (or use only the `db` service from Compose).
2. Copy `.env.example` to `.env` and point `DATABASE_URL` at your database.
3. Install dependencies: `pip install -r requirements.txt`
4. Migrations: `alembic upgrade head`
5. Run: `uvicorn app.main:app --reload`

## Tests

```bash
pip install -r requirements.txt
pytest
```

Inside Docker (after `docker compose up --build`):

```bash
docker compose exec api pytest -v
```

Tests use in-memory SQLite with foreign keys enabled (PostgreSQL remains the production target).

## API overview

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/departments/` | Create department (`name`, optional `parent_id`) |
| `POST` | `/departments/{id}/employees/` | Create employee in department |
| `GET` | `/departments/{id}` | Department details, employees, nested children (`depth` 1–5, `include_employees`) |
| `PATCH` | `/departments/{id}` | Update `name` and/or `parent_id` |
| `DELETE` | `/departments/{id}` | `mode=cascade` or `mode=reassign` + `reassign_to_department_id` |

Department names are unique among siblings (case-insensitive). Moving a department under its own subtree returns `409`. Reassign delete moves employees and child departments to the target department before removing the node.

## Project layout

- `app/main.py` — FastAPI app
- `app/models/` — SQLAlchemy models
- `app/schemas/` — Pydantic request/response models
- `app/services/department_service.py` — business rules
- `app/routers/departments.py` — HTTP layer
- `alembic/versions/` — migrations
