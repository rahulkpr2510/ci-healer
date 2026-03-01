# CI Healer — Autonomous CI/CD Healing Agent

> **An AI-powered agent that monitors failing CI pipelines, automatically diagnoses root causes, applies targeted code fixes, commits them to a dedicated branch, and opens a pull request — all without human intervention.**

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [Quick Start — Local Development](#quick-start--local-development)
- [Environment Variables](#environment-variables)
- [Running Tests](#running-tests)
- [Deployment](#deployment)
- [API Reference](#api-reference)
- [Contributing](#contributing)

---

## Overview

CI Healer integrates with your GitHub repositories and listens for CI failures. When a failure is detected, a **LangGraph-powered agent** clones the repository, runs static analysis and tests, classifies every failure by bug type, and invokes an LLM (Groq `llama-3.3-70b-versatile` by default) to generate minimal, precise code fixes. The fixes are committed to an `[AI-AGENT]`-prefixed branch and a pull request is opened automatically.

**Key capabilities:**

- 🔁 Iterative fix loop — up to N configurable iterations
- 🤖 LLM-driven code repair with rule-based fallbacks
- 📊 Real-time SSE log streaming to the dashboard
- 🔐 GitHub OAuth authentication with per-user isolation
- 📈 Analytics dashboard — pass rate, fixes applied, run history

---

## Architecture

```
Browser (Next.js)
      │  GitHub OAuth login
      │  REST + SSE
      ▼
┌─────────────────────────────────────────────────────┐
│  Backend  (FastAPI · PostgreSQL · Port 8000)        │
│                                                     │
│  /auth      GitHub OAuth → JWT session              │
│  /api/run   Triggers agent, streams SSE events      │
│  /api/history, /api/analytics  Read-only queries    │
└──────────────────────┬──────────────────────────────┘
                       │  HTTP POST /engine/run
                       │  HTTP GET  /runs/{id}/log  (poll every 2 s)
                       ▼
┌─────────────────────────────────────────────────────┐
│  AI Engine  (LangGraph · Groq/Gemini · Port 8001)   │
│                                                     │
│  repo_analyzer → language_detector                  │
│       → static_analyzer → test_runner               │
│       → failure_classifier → fix_generator          │
│       → patch_applier → git_commit                  │
│       → create_pull_request → ci_monitor            │
│       → (iterate or finalize)                       │
└─────────────────────────────────────────────────────┘
                       │
                       │  git clone / push / PR
                       ▼
              GitHub Repository
```

---

## Technology Stack

| Layer            | Technology                                               |
| ---------------- | -------------------------------------------------------- |
| Frontend         | Next.js 16, TypeScript, Tailwind CSS, shadcn/ui, Zustand |
| Backend          | FastAPI, SQLAlchemy 2.0 (async), Alembic, asyncpg        |
| AI Engine        | LangGraph, LangChain, Groq (`llama-3.3-70b-versatile`)   |
| Database         | PostgreSQL 16                                            |
| Auth             | GitHub OAuth 2.0 + JWT                                   |
| Containerisation | Docker, Docker Compose                                   |
| Deployment       | Railway (backend + engine), Vercel (frontend)            |

---

## Project Structure

```
ci-healer/
├── frontend/          # Next.js 16 App Router SPA
├── backend/           # FastAPI REST API + SSE
├── ai-engine/         # LangGraph autonomous agent
├── docker-compose.yml # Full local stack
└── docs/
    └── ARCHITECTURE.md
```

---

## Quick Start — Local Development

### Prerequisites

| Requirement         | Version                                                                  |
| ------------------- | ------------------------------------------------------------------------ |
| Python              | 3.12+                                                                    |
| Node.js             | 20+                                                                      |
| Docker + Compose    | Latest                                                                   |
| A free Groq API key | [console.groq.com](https://console.groq.com)                             |
| A GitHub OAuth App  | [github.com/settings/developers](https://github.com/settings/developers) |

### 1 — Clone the repository

```bash
git clone https://github.com/rahulkpr2510/ci-healer.git
cd ci-healer
```

### 2 — Configure environment variables

```bash
# AI Engine
cp ai-engine/.env.example ai-engine/.env
# → Set GROQ_API_KEY

# Backend
cp backend/.env.example backend/.env
# → Set GITHUB_CLIENT_ID, GITHUB_CLIENT_SECRET, JWT_SECRET_KEY, DATABASE_URL

# Frontend
cp frontend/.env.example frontend/.env.local
# → Set NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 3a — Start with Docker Compose (recommended)

```bash
# Create a root .env file for compose variable substitution
cat > .env << 'EOF'
GROQ_API_KEY=gsk_your_key_here
GITHUB_CLIENT_ID=your_client_id
GITHUB_CLIENT_SECRET=your_client_secret
JWT_SECRET_KEY=$(openssl rand -hex 32)
POSTGRES_USER=cihealer
POSTGRES_PASSWORD=cihealer_dev
POSTGRES_DB=cihealer
GITHUB_REDIRECT_URI=http://localhost:8000/auth/callback
FRONTEND_URL=http://localhost:3000
ALLOWED_ORIGINS=http://localhost:3000
EOF

docker-compose up --build
```

Open [http://localhost:3000](http://localhost:3000).

### 3b — Start services manually

```bash
# Terminal 1 — PostgreSQL (or use existing)
docker run -e POSTGRES_USER=cihealer -e POSTGRES_PASSWORD=cihealer_dev \
           -e POSTGRES_DB=cihealer -p 5432:5432 postgres:16-alpine

# Terminal 2 — Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 3 — AI Engine
cd ai-engine
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn api.main:app --host 0.0.0.0 --port 8001 \
  --reload --reload-dir api --reload-dir engine

# Terminal 4 — Frontend
cd frontend
npm install
npm run dev
```

---

## Environment Variables

### Root `.env` (Docker Compose only)

| Variable               | Required | Description                                                 |
| ---------------------- | -------- | ----------------------------------------------------------- |
| `GROQ_API_KEY`         | ✅       | Groq API key ([console.groq.com](https://console.groq.com)) |
| `GITHUB_CLIENT_ID`     | ✅       | GitHub OAuth App client ID                                  |
| `GITHUB_CLIENT_SECRET` | ✅       | GitHub OAuth App client secret                              |
| `JWT_SECRET_KEY`       | ✅       | Random 32-char string (`openssl rand -hex 32`)              |
| `POSTGRES_USER`        | ❌       | Default: `cihealer`                                         |
| `POSTGRES_PASSWORD`    | ❌       | Default: `cihealer_dev`                                     |
| `POSTGRES_DB`          | ❌       | Default: `cihealer`                                         |

Refer to each service's own `.env.example` for the full variable reference.

---

## Running Tests

```bash
# Backend
cd backend
.venv/bin/pytest tests/ -v

# AI Engine
cd ai-engine
.venv/bin/pytest tests/ -v
```

---

## Deployment

See the full deployment playbook: [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)

**Recommended stack:**

- **Backend + AI Engine** → [Railway](https://railway.app) (two services, one project)
- **Frontend** → [Vercel](https://vercel.com) (free tier)
- **Database** → [Supabase](https://supabase.com) or Railway Postgres add-on

---

## API Reference

| Method | Path                               | Description                |
| ------ | ---------------------------------- | -------------------------- |
| `POST` | `/auth/github`                     | Initiate GitHub OAuth      |
| `GET`  | `/auth/callback`                   | OAuth callback → JWT       |
| `POST` | `/api/run`                         | Start an agent run         |
| `GET`  | `/api/run/{id}`                    | Run status                 |
| `GET`  | `/api/run/{id}/events`             | SSE live log stream        |
| `GET`  | `/api/history/all`                 | Paginated run history      |
| `GET`  | `/api/history/{owner}/{repo}`      | Per-repo history           |
| `GET`  | `/api/analytics/dashboard/summary` | Dashboard stats            |
| `GET`  | `/api/analytics/{owner}/{repo}`    | Per-repo analytics         |
| `GET`  | `/api/repos`                       | Authenticated user's repos |
| `GET`  | `/health`                          | Health check               |

Interactive docs available at [http://localhost:8000/docs](http://localhost:8000/docs) when running locally.

---

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feat/my-feature`
3. Make your changes and add tests
4. Run the test suite: `pytest tests/ -v`
5. Open a pull request against `main`

Please follow the existing code style (Black for Python, ESLint/Prettier for TypeScript).
