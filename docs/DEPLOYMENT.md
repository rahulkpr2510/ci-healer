# CI Healer — Deployment Guide

This document covers the full production deployment of CI Healer using the recommended free-tier stack:

| Service               | Platform                         | Free Tier                   |
| --------------------- | -------------------------------- | --------------------------- |
| Frontend              | [Vercel](https://vercel.com)     | ✅ Generous free tier       |
| Backend (FastAPI)     | [Railway](https://railway.app)   | ✅ $5/month credit (Hobby)  |
| AI Engine (LangGraph) | [Railway](https://railway.app)   | Shared project with backend |
| Database (PostgreSQL) | [Supabase](https://supabase.com) | ✅ Free tier (500 MB)       |
| LLM                   | [Groq](https://console.groq.com) | ✅ Free tier                |

> **Alternative:** Use Railway's built-in Postgres add-on instead of Supabase (easier setup, but limited to 1 GB on Hobby plan).

---

## Prerequisites

Before you begin, collect these credentials:

| Credential       | Where to get it                                                          |
| ---------------- | ------------------------------------------------------------------------ |
| Groq API key     | [console.groq.com](https://console.groq.com) → API Keys                  |
| GitHub OAuth App | [github.com/settings/developers](https://github.com/settings/developers) |
| Supabase DB URL  | Supabase project → Settings → Database → Connection string               |
| Railway account  | [railway.app](https://railway.app)                                       |
| Vercel account   | [vercel.com](https://vercel.com)                                         |

---

## Step 1 — Database (Supabase)

1. Go to [supabase.com](https://supabase.com) and create a new project
2. Navigate to **Settings → Database**
3. Copy the **Connection string** (URI format) — it looks like:
   ```
   postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres
   ```
4. Keep this — you will use it as `DATABASE_URL` in the backend

> No schema setup is needed. Alembic migrations run automatically on first backend boot.

---

## Step 2 — GitHub OAuth App

1. Go to [GitHub → Settings → Developer Settings → OAuth Apps → New OAuth App](https://github.com/settings/developers)
2. Fill in:
   - **Application name:** `CI Healer`
   - **Homepage URL:** `https://your-frontend.vercel.app` _(fill in after Vercel deploy)_
   - **Authorization callback URL:** `https://your-backend.railway.app/auth/callback` _(fill in after Railway deploy)_
3. Click **Register application**
4. Note the **Client ID** and generate a **Client Secret**

> You can create the app now with placeholder URLs and update them after deployment.

---

## Step 3 — Deploy Backend + AI Engine on Railway

### 3.1 — Create a Railway project

1. Go to [railway.app/new](https://railway.app/new) and create a new project
2. The project will hold two services: **backend** and **ai-engine**

### 3.2 — Deploy the Backend service

1. Inside your Railway project, click **+ New Service → GitHub Repo**
2. Select your repository
3. Set **Root Directory** to `backend`
4. Railway auto-detects the `Dockerfile` — the build starts automatically

**Add these environment variables in Railway → backend → Variables:**

```
APP_ENV=production
DATABASE_URL=postgresql://postgres:[PASSWORD]@db.[REF].supabase.co:5432/postgres
GITHUB_CLIENT_ID=<your client id>
GITHUB_CLIENT_SECRET=<your client secret>
GITHUB_REDIRECT_URI=https://<your-railway-backend-url>/auth/callback
JWT_SECRET_KEY=<openssl rand -hex 32>
AI_ENGINE_URL=http://ai-engine.railway.internal:8001
ALLOWED_ORIGINS=https://<your-vercel-frontend-url>
FRONTEND_URL=https://<your-vercel-frontend-url>
DEFAULT_MAX_ITERATIONS=5
AI_ENGINE_TIMEOUT=600
```

> `http://ai-engine.railway.internal:8001` uses Railway's **private networking** — the AI engine is not exposed to the internet but is reachable by the backend within the same project.

### 3.3 — Deploy the AI Engine service

1. In the same Railway project, add **+ New Service → GitHub Repo**
2. Select the same repository
3. Set **Root Directory** to `ai-engine`
4. Railway auto-detects the `Dockerfile`

**Add these environment variables in Railway → ai-engine → Variables:**

```
LLM_PROVIDER=groq
GROQ_API_KEY=gsk_<your groq key>
GROQ_MODEL=llama-3.3-70b-versatile
LLM_TEMPERATURE=0.2
LLM_MAX_TOKENS=8192
DEFAULT_MAX_ITERATIONS=5
WORKSPACE_DIR=/workspace
GIT_AUTHOR_NAME=CI Healer Agent
GIT_AUTHOR_EMAIL=agent@cihealer.dev
GIT_COMMIT_PREFIX=[AI-AGENT]
BACKEND_ORIGIN=https://<your-railway-backend-url>
```

> **Important:** The AI engine should **not** have a public domain in Railway. Use its private internal URL only. If Railway assigns a public domain, you can leave it but ensure `BACKEND_ORIGIN` is set to reject external requests.

### 3.4 — Add a persistent volume for the workspace

In Railway → ai-engine → **Volumes**, add a mounted volume:

- **Mount path:** `/workspace`
- **Size:** 5 GB (adjust as needed)

This ensures cloned repository workspaces survive container restarts.

### 3.5 — Verify deployment

```bash
# Backend health
curl https://your-backend.railway.app/health

# AI engine health (via backend URL, since engine has no public domain)
# Or check Railway logs
```

---

## Step 4 — Deploy Frontend on Vercel

1. Go to [vercel.com/new](https://vercel.com/new)
2. Import your GitHub repository
3. Set **Root Directory** to `frontend`
4. Add environment variable:
   ```
   NEXT_PUBLIC_API_URL = https://your-backend.railway.app
   ```
5. Click **Deploy**

Vercel automatically detects Next.js and runs `npm run build`.

### 4.1 — Update GitHub OAuth callback URL

Now that you have the Vercel URL, go back to your GitHub OAuth App and update:

- **Homepage URL** → `https://your-frontend.vercel.app`
- **Callback URL** → `https://your-backend.railway.app/auth/callback`

Also update the backend Railway variable:

```
GITHUB_REDIRECT_URI=https://your-backend.railway.app/auth/callback
```

---

## Step 5 — Smoke Test

1. Open `https://your-frontend.vercel.app`
2. Click **Sign in with GitHub** — you should be redirected to GitHub and back
3. On the dashboard, submit a public GitHub repo URL
4. Watch the live log stream — the agent should clone, analyse, and attempt fixes
5. Check the **History** tab after the run completes

---

## Alternative: Full Local Stack via Docker Compose

For local integration testing with all services in containers:

```bash
# 1. Copy and fill root .env
cp .env.example .env
# Edit .env with your credentials

# 2. Build and start
docker-compose up --build

# 3. Run migrations (first time only — handled automatically by backend)
# Visit http://localhost:3000
```

Services:

- Frontend: [http://localhost:3000](http://localhost:3000)
- Backend API: [http://localhost:8000](http://localhost:8000)
- AI Engine: [http://localhost:8001](http://localhost:8001)
- PostgreSQL: `localhost:5432`

---

## Environment Variables Quick Reference

### Backend (Railway)

| Variable               | Required | Notes                               |
| ---------------------- | -------- | ----------------------------------- |
| `APP_ENV`              | ✅       | `production`                        |
| `DATABASE_URL`         | ✅       | Supabase or Railway Postgres URL    |
| `GITHUB_CLIENT_ID`     | ✅       | OAuth App                           |
| `GITHUB_CLIENT_SECRET` | ✅       | OAuth App                           |
| `GITHUB_REDIRECT_URI`  | ✅       | `https://backend-url/auth/callback` |
| `JWT_SECRET_KEY`       | ✅       | `openssl rand -hex 32`              |
| `AI_ENGINE_URL`        | ✅       | Railway internal URL                |
| `ALLOWED_ORIGINS`      | ✅       | Vercel frontend URL                 |
| `FRONTEND_URL`         | ✅       | Vercel frontend URL                 |

### AI Engine (Railway)

| Variable         | Required | Notes                               |
| ---------------- | -------- | ----------------------------------- |
| `LLM_PROVIDER`   | ✅       | `groq` or `gemini`                  |
| `GROQ_API_KEY`   | ✅       | If using Groq                       |
| `GOOGLE_API_KEY` | ✅       | If using Gemini                     |
| `WORKSPACE_DIR`  | ✅       | `/workspace` (matches volume mount) |
| `BACKEND_ORIGIN` | ❌       | Lock CORS to backend origin         |

### Frontend (Vercel)

| Variable              | Required | Notes                      |
| --------------------- | -------- | -------------------------- |
| `NEXT_PUBLIC_API_URL` | ✅       | Railway backend public URL |

---

## Estimated Monthly Cost

| Service                    | Plan  | Cost                             |
| -------------------------- | ----- | -------------------------------- |
| Railway (backend + engine) | Hobby | ~$5/month (covered by $5 credit) |
| Vercel (frontend)          | Free  | $0                               |
| Supabase (database)        | Free  | $0                               |
| Groq (LLM)                 | Free  | $0                               |
| **Total**                  |       | **~$0–$5/month**                 |

Railway charges per-usage. The backend is very lightweight. The AI engine only runs during active runs; with a few runs per day it stays well within the $5 credit.

---

## Scaling Considerations

- **AI Engine**: LangGraph is CPU-bound during repo analysis. Railway's smallest instance (0.5 vCPU / 512 MB) handles one concurrent run comfortably. For more concurrent runs, scale vertically or run multiple engine instances behind a load balancer.
- **Backend**: Two uvicorn workers (`--workers 2`) are sufficient for hundreds of concurrent SSE connections. Scale vertically on Railway as needed.
- **Database**: Supabase free tier handles ~100 concurrent connections. For >50 simultaneous users, upgrade to Pro or use PgBouncer connection pooling.
- **Workspace storage**: Each run clones a full repository. Size the Railway volume accordingly (5–20 GB recommended). Old workspaces are not currently auto-cleaned — implement a cron job if storage becomes an issue.
