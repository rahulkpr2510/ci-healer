# Cloud Database Migration Guide

## Overview

CI Healer uses PostgreSQL via SQLAlchemy (async). The database schema is managed with **Alembic** migrations.

The backend supports:

- **Local development** — SQLite (auto-created)
- **Docker Compose** — PostgreSQL 16 container
- **Cloud production** — Supabase or Neon PostgreSQL

---

## Option 1: Supabase (Recommended)

### Setup

1. Create a free project at [supabase.com](https://supabase.com)
2. Go to **Settings → Database → Connection string**
3. Copy the **URI** (PostgreSQL connection string)
4. Set it in your `.env`:

```bash
DATABASE_URL=postgresql+asyncpg://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres
```

> The asyncpg driver requires `postgresql+asyncpg://` prefix (not `postgresql://`).
> The backend automatically adds `ssl=require` for all PostgreSQL connections.

### Connection pooling (Supabase)

For production with multiple workers, use Supabase's PgBouncer:

```bash
DATABASE_URL=postgresql+asyncpg://postgres:[PASSWORD]@aws-0-us-east-1.pooler.supabase.com:6543/postgres?sslmode=require
```

---

## Option 2: Neon

### Setup

1. Create a free database at [neon.tech](https://neon.tech)
2. Go to **Connection Details** → copy the connection string
3. Set it in your `.env`:

```bash
DATABASE_URL=postgresql+asyncpg://[USER]:[PASSWORD]@[HOST].neon.tech/[DBNAME]?sslmode=require
```

---

## Running Migrations

### First time (apply initial schema):

```bash
cd backend
DATABASE_URL=<your-db-url> python -m alembic upgrade head
```

### Using the helper script:

```bash
cd backend
DATABASE_URL=<your-db-url> ./scripts/migrate.sh
```

### Railway (auto-run on deploy):

In `railway.json`, migrations run automatically before the server starts:

```json
{
  "deploy": {
    "startCommand": "python -m alembic upgrade head && uvicorn app.main:app ..."
  }
}
```

---

## Creating New Migrations

After changing a SQLAlchemy model (in `app/models/`):

```bash
cd backend
python -m alembic revision --autogenerate -m "describe your change"
```

Review the generated file in `app/db/migrations/versions/` before applying.

---

## Schema Overview

| Table       | Purpose                                               |
| ----------- | ----------------------------------------------------- |
| `users`     | GitHub OAuth users (github_id, username, token)       |
| `runs`      | Agent run sessions (one per POST /api/run call)       |
| `fixes`     | Individual code fixes applied during a run            |
| `ci_events` | CI pipeline iteration results (PASSED/FAILED per run) |

All tables use integer PKs + UUID `run_id` for external references.
All foreign keys cascade on delete (deleting a user removes all their data).
