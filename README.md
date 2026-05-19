# Backend

## Database migrations (Alembic)

Run commands from this directory (`backend/`):

- Apply latest migrations:
  - `alembic upgrade head`
- Show current DB revision:
  - `alembic current`
- Create a new migration after model changes:
  - `alembic revision --autogenerate -m "describe change"`
- Roll back one revision:
  - `alembic downgrade -1`

Alembic reads `DATABASE_URL` from `backend/.env` through `app.config.Settings`.

## Demo: dashboard API

1. Copy `.env.example` to `.env` and ensure `DATABASE_URL` points at a running PostgreSQL (local or Docker).

2. Start Postgres (example with Docker Compose from this folder):

   - `docker compose up -d db`

3. Install Python dependencies (from `backend/`):

   - `pip install -r requirements.txt`

4. Run migrations:

   - `alembic upgrade head`

5. Load demo rows (users, import jobs, sample feedback/notification/audit):

   - Windows PowerShell: `$env:PYTHONPATH = (Get-Location).Path; python scripts/seed_demo_dashboard.py`
   - Bash: `PYTHONPATH=. python scripts/seed_demo_dashboard.py`

6. Start the API (eager Celery avoids needing Redis for upload validation in dev):

   - Set in `.env`: `CELERY_TASK_ALWAYS_EAGER=true`
   - `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000` (with `PYTHONPATH` set to `backend/` or run from `backend/`)

7. Open interactive docs: `http://localhost:8000/docs`

Useful GET endpoints:

- `GET /api/v1/dashboard/demo/info` — stable demo user UUIDs and example paths
- `GET /api/v1/dashboard/overview?days=30` — platform-wide metrics
- `GET /api/v1/dashboard/users/{user_id}/overview?days=30` — metrics for one user (until JWT replaces the path param)

If `pip install` fails with a PostgreSQL SSL certificate path error on Windows, fix or unset the `SSL_CERT_FILE` / `REQUESTS_CA_BUNDLE` environment variables pointing at an invalid file, then retry.
