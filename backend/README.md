# CI Healer — Backend

> **FastAPI REST API — GitHub OAuth authentication, SSE event streaming, run orchestration, and analytics.**

---

## Overview

The backend is the central coordinator between the Next.js frontend and the LangGraph AI Engine. It:

- Authenticates users via **GitHub OAuth 2.0**, issuing signed **JWT** sessions
- Persists every agent run, applied fix, and CI event to **PostgreSQL**
- Triggers agent runs as background `asyncio` tasks and streams live progress via **Server-Sent Events (SSE)**
- Exposes read-only analytics and history endpoints for the dashboard
- Polls the AI engine's log endpoint every 2 seconds, forwarding live log entries to connected SSE clients

---

## Technology Stack

| Library                | Purpose                             |
| ---------------------- | ----------------------------------- |
| FastAPI                | ASGI web framework, OpenAPI docs    |
| SQLAlchemy 2.0 (async) | ORM with asyncpg driver             |
| Alembic                | Database schema migrations          |
| asyncpg                | PostgreSQL async driver             |
| httpx                  | Async HTTP client (AI engine calls) |
| python-jose            | JWT creation and verification       |
| slowapi                | Rate limiting                       |
| pydantic-settings      | Typed environment configuration     |

---

## Project Structure

```
backend/
├── app/
│   ├── main.py              # FastAPI app, lifespan, middleware
│   ├── db/
│   │   └── database.py      # SQLAlchemy engine, session factory
│   ├── middleware/
│   │   ├── auth.py          # JWT dependency + GitHub token extraction
│   │   └── cors.py          # CORS configuration
│   ├── models/              # SQLAlchemy ORM models
│   │   ├── user.py
│   │   ├── run.py
│   │   ├── fix.py
│   │   └── ci_event.py
│   ├── routers/             # FastAPI route handlers
│   │   ├── auth.py          # GitHub OAuth flow
│   │   ├── agent.py         # Run creation + SSE streaming
│   │   ├── history.py       # Run history queries
│   │   ├── analytics.py     # Dashboard + per-repo analytics
│   │   └── repos.py         # GitHub repo listing
│   ├── schemas/             # Pydantic request/response models
│   └── services/
│       └── run_service.py   # Agent orchestration + DB persistence
├── config/
│   └── settings.py          # Typed settings via pydantic-settings
├── alembic.ini
├── Dockerfile
├── requirements.txt
└── .env.example
```

---

## Environment Variables

Copy `.env.example` to `.env`.

| Variable                 | Required | Default                 | Description                             |
| ------------------------ | -------- | ----------------------- | --------------------------------------- |
| `DATABASE_URL`           | ✅       | —                       | PostgreSQL connection string            |
| `GITHUB_CLIENT_ID`       | ✅       | —                       | GitHub OAuth App client ID              |
| `GITHUB_CLIENT_SECRET`   | ✅       | —                       | GitHub OAuth App client secret          |
| `GITHUB_REDIRECT_URI`    | ✅       | —                       | OAuth callback URL (`/auth/callback`)   |
| `JWT_SECRET_KEY`         | ✅       | —                       | Random 32-char string                   |
| `JWT_ALGORITHM`          | ❌       | `HS256`                 | JWT signing algorithm                   |
| `JWT_EXPIRE_MINUTES`     | ❌       | `10080` (7 days)        | Token lifetime                          |
| `AI_ENGINE_URL`          | ❌       | `http://localhost:8001` | Internal URL of the AI engine           |
| `AI_ENGINE_TIMEOUT`      | ❌       | `600`                   | HTTP timeout for engine calls (seconds) |
| `ALLOWED_ORIGINS`        | ❌       | `http://localhost:3000` | Comma-separated CORS allowed origins    |
| `FRONTEND_URL`           | ❌       | `http://localhost:3000` | Used for OAuth redirect construction    |
| `APP_ENV`                | ❌       | `development`           | `development` or `production`           |
| `DEBUG`                  | ❌       | `false`                 | Enable verbose SQL logging              |
| `DEFAULT_MAX_ITERATIONS` | ❌       | `5`                     | Default agent iteration limit           |

### GitHub OAuth App Setup

1. Go to [GitHub Settings → Developer settings → OAuth Apps → New OAuth App](https://github.com/settings/developers)
2. Set **Homepage URL** to your frontend URL (e.g. `http://localhost:3000`)
3. Set **Authorization callback URL** to `http://localhost:8000/auth/callback` (or your production backend URL)
4. Copy the Client ID and Client Secret to `.env`

---

## Local Development

```bash
cd backend

# Create virtual environment
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env — set DATABASE_URL, GITHUB_CLIENT_ID, GITHUB_CLIENT_SECRET, JWT_SECRET_KEY

# Run database migrations
python -m alembic upgrade head

# Start the development server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Interactive API docs: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## Database Migrations

The project uses **Alembic** for schema management.

```bash
# Apply all pending migrations
python -m alembic upgrade head

# Check current migration version
python -m alembic current

# Generate a new migration after model changes
python -m alembic revision --autogenerate -m "add my_column"

# Roll back one migration
python -m alembic downgrade -1
```

> In production (`APP_ENV=production`), migrations run automatically on every server startup via the FastAPI lifespan handler — making deployments safe and idempotent.

---

## API Endpoints

### Authentication

| Method | Path             | Description                  |
| ------ | ---------------- | ---------------------------- |
| `GET`  | `/auth/login`    | Redirect to GitHub OAuth     |
| `GET`  | `/auth/callback` | OAuth callback — returns JWT |
| `GET`  | `/auth/me`       | Current authenticated user   |
| `POST` | `/auth/logout`   | Invalidate session           |

### Agent Runs

| Method | Path                       | Description               |
| ------ | -------------------------- | ------------------------- |
| `POST` | `/api/run`                 | Start a new agent run     |
| `GET`  | `/api/run/{run_id}`        | Get run status and result |
| `GET`  | `/api/run/{run_id}/events` | SSE live log stream       |

### History

| Method | Path                          | Description                |
| ------ | ----------------------------- | -------------------------- |
| `GET`  | `/api/history/all`            | Paginated list of all runs |
| `GET`  | `/api/history/{owner}/{repo}` | Per-repo run history       |

### Analytics

| Method | Path                               | Description                                        |
| ------ | ---------------------------------- | -------------------------------------------------- |
| `GET`  | `/api/analytics/dashboard/summary` | Total runs, pass rate, fixes applied, unique repos |
| `GET`  | `/api/analytics/{owner}/{repo}`    | Per-repo breakdown — bug distribution, timeline    |

### Repositories

| Method | Path         | Description                                   |
| ------ | ------------ | --------------------------------------------- |
| `GET`  | `/api/repos` | List authenticated user's GitHub repositories |

### Health

| Method | Path      | Description              |
| ------ | --------- | ------------------------ |
| `GET`  | `/health` | Service health + version |

---

## SSE Event Types

The `/api/run/{run_id}/events` SSE stream emits these event types:

| `type`           | When                                                                    |
| ---------------- | ----------------------------------------------------------------------- |
| `AGENT_STARTED`  | Run begins                                                              |
| `log`            | Live progress message (level: `info` / `success` / `warning` / `error`) |
| `FIX_GENERATED`  | A fix was generated for a file                                          |
| `COMMIT_CREATED` | Commits pushed                                                          |
| `CI_RERUN`       | CI status polled                                                        |
| `complete`       | Run finished — payload contains final status                            |
| `error`          | Run crashed                                                             |
| `ping`           | Keep-alive (every 15 s)                                                 |

---

## Running Tests

```bash
cd backend
.venv/bin/pytest tests/ -v
```

---

## Docker

```bash
# Build
docker build -t ci-healer-backend .

# Run (requires a running PostgreSQL and AI Engine)
docker run -p 8000:8000 \
  -e DATABASE_URL="postgresql+asyncpg://..." \
  -e GITHUB_CLIENT_ID=... \
  -e GITHUB_CLIENT_SECRET=... \
  -e JWT_SECRET_KEY=... \
  -e AI_ENGINE_URL=http://your-engine-host:8001 \
  ci-healer-backend
```
