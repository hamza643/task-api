# Task API

A small FastAPI service: signup and login (JWT), tasks that belong to users,
projects, comments and tags. It runs in Docker together with a Postgres database.

## Quick start (from a clean clone)

You only need Docker.

```bash
git clone https://github.com/hamza643/task-api.git
cd task-api
cp .env.example .env
docker compose up --build
```

Then open:

- API docs (try every endpoint here): http://localhost:8000/docs
- Health check: http://localhost:8000/health

The values in `.env.example` are placeholders so the stack starts. Put a real
secret in your own `.env` before using it for anything else (see below).

Stop it with `Ctrl+C`, then:

```bash
docker compose down        # stops the containers, keeps the database data
docker compose down -v     # also deletes the database data (start from zero)
```

### In GitHub Codespaces

Container-to-container networking is blocked there, so use the host-network file:

```bash
cp .env.example .env
docker compose -f docker-compose.codespaces.yml up --build
```

## Configuration (.env)

All secrets live in `.env`, which is **not** committed (it is in `.gitignore`)
and **not** copied into the image (it is in `.dockerignore`).
`.env.example` shows which variables exist.

| Variable | Used by | Meaning |
|---|---|---|
| `SECRET_KEY` | API | Signs the JWT tokens. The app refuses to start without it. |
| `POSTGRES_USER` | Postgres and API | Database user |
| `POSTGRES_PASSWORD` | Postgres and API | Database password |
| `POSTGRES_DB` | Postgres and API | Database name |
| `ACCESS_TOKEN_MINUTES` | API | Optional, token lifetime (default 30) |
| `DATABASE_URL` | API | Optional. Docker compose builds it from the POSTGRES_* values. If it is not set, the API uses a local SQLite file `tasks.db`. |

Make a real secret:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

## Run the tests

The tests use their own in-memory database and a throwaway secret, so they need
neither Docker nor a `.env` file.

```bash
python -m venv .venv
.venv/Scripts/activate        # Windows PowerShell: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pytest -v
```

## Run without Docker

```bash
cp .env.example .env
uvicorn main:app --reload
```

This uses SQLite (`tasks.db`) because `DATABASE_URL` is not set.

## Data model

- `User` has many `Task`s and many `Project`s.
- `Project` has many `Task`s (one-to-many).
- `Comment` belongs to a `Task` **and** to a `User` (its author): two foreign keys.
- `Task` and `Tag` are many-to-many through the `task_tags` association table.

## Endpoints

"Login" means a valid token (use the Authorize button in `/docs`).

| Method and path | Login | What it does |
|---|---|---|
| `GET /health` | no | Returns `{"status": "ok"}` |
| `POST /signup` | no | Create an account |
| `POST /login` | no | Get a token |
| `GET /me` | yes | Who am I |
| `GET /tasks` (optional `?tag=urgent`) | no | All tasks, public on purpose |
| `GET /tasks/mine` | yes | Only my tasks |
| `POST /tasks` | yes | Create a task (owner = me) |
| `DELETE /tasks/{id}` | yes | Delete my task (403 if it is not mine) |
| `POST /projects` | yes | Create a project |
| `GET /projects/mine` | yes | My projects |
| `POST /projects/{project_id}/tasks/{task_id}` | yes | Put my task into my project |
| `GET /projects/{project_id}/tasks` | yes | Tasks of my project |
| `POST /tasks/{id}/comments` | yes | Comment on any task |
| `GET /tasks/{id}/comments` | no | List comments of a task |
| `DELETE /comments/{id}` | yes | Allowed for the comment's author and the task's owner |
| `POST /tasks/{id}/tags` | yes | Tag my task (the tag is created on first use) |
| `GET /tags` | no | All tags |

## Notes

- Tables are created at startup with `create_all`. That does not change tables
  that already exist. When the models change in development, reset the database
  (`docker compose down -v`, or delete `tasks.db`). A real project would use
  migrations (Alembic).
- The Dockerfile is multi-stage and the container runs as a non-root user.