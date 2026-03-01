# CI Healer — Frontend

> **Next.js 15 App Router dashboard for monitoring AI agent runs, viewing fix history, and analysing CI health trends.**

---

## Overview

The frontend provides a real-time dashboard where developers can:

- **Log in** via GitHub OAuth with a single click
- **Trigger agent runs** by submitting a GitHub repository URL
- **Watch live progress** via Server-Sent Events (SSE) — each pipeline node streams log messages as it executes
- **Browse run history** with per-repo and global views
- **Explore analytics** — pass rate, fixes applied, bug type distributions, score trends

---

## Technology Stack

| Library                 | Purpose                       |
| ----------------------- | ----------------------------- |
| Next.js 15 (App Router) | React framework, SSR, routing |
| TypeScript              | Type safety throughout        |
| Tailwind CSS            | Utility-first styling         |
| shadcn/ui               | Accessible component library  |
| Zustand                 | Global auth state             |
| EventSource API         | SSE live log streaming        |

---

## Project Structure

```
frontend/src/
├── app/                     # Next.js App Router pages
│   ├── layout.tsx           # Root layout — auth guard, theme
│   ├── page.tsx             # Landing / login page
│   ├── dashboard/
│   │   └── page.tsx         # Dashboard home — stats + quick actions
│   ├── run/
│   │   └── [runId]/
│   │       └── page.tsx     # Live run viewer (SSE + status polling)
│   ├── history/
│   │   └── page.tsx         # Paginated run history
│   └── analytics/
│       └── page.tsx         # Analytics charts and stats
├── components/              # Reusable UI components
├── hooks/                   # Custom React hooks
├── lib/
│   └── api.ts               # All API calls (typed, centralised)
├── store/
│   └── auth.ts              # Zustand auth store
└── types/
    └── agent.ts             # Shared TypeScript interfaces
```

---

## Environment Variables

Copy `.env.example` to `.env.local`.

| Variable              | Required | Description                                     |
| --------------------- | -------- | ----------------------------------------------- |
| `NEXT_PUBLIC_API_URL` | ✅       | Backend base URL (e.g. `http://localhost:8000`) |

> `NEXT_PUBLIC_*` variables are embedded at **build time** and are visible in the browser bundle. Do not put secrets here.

---

## Local Development

```bash
cd frontend

# Install dependencies
npm install

# Configure
cp .env.example .env.local
# Set NEXT_PUBLIC_API_URL=http://localhost:8000

# Start development server
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

---

## Available Scripts

| Script          | Description                        |
| --------------- | ---------------------------------- |
| `npm run dev`   | Development server with hot-reload |
| `npm run build` | Production build                   |
| `npm run start` | Start production server            |
| `npm run lint`  | ESLint check                       |

---

## Pages

| Route          | Description                                         |
| -------------- | --------------------------------------------------- |
| `/`            | Landing page — GitHub login                         |
| `/dashboard`   | Home — stats cards, new run form                    |
| `/run/[runId]` | Live run viewer — SSE log stream, status polling    |
| `/history`     | Paginated global run history                        |
| `/analytics`   | Dashboard metrics — pass rate, bug types, timelines |

---

## Authentication Flow

1. User clicks **"Sign in with GitHub"**
2. Frontend redirects to `GET /auth/login` (backend) → GitHub OAuth consent
3. GitHub redirects to `GET /auth/callback` (backend) → JWT returned
4. JWT stored in `localStorage`, attached to every API request via `Authorization: Bearer <token>`
5. Zustand store hydrated from `localStorage` on page load

---

## Live Log Streaming

The run page connects to `GET /api/run/{runId}/events` using the browser's native `EventSource` API. As the agent progresses through each node, log messages appear in real time.

A **5-second DB polling fallback** also runs in parallel — if the SSE connection drops, the page continues to reflect the latest run status by polling the database record.

---

## Building for Production

```bash
npm run build
```

The build uses **Next.js standalone output** (`output: "standalone"` in `next.config.ts`), producing a minimal self-contained `server.js` suitable for Docker or any Node.js host.

---

## Docker

```bash
# Build (API URL is embedded at build time)
docker build \
  --build-arg NEXT_PUBLIC_API_URL=https://your-backend.railway.app \
  -t ci-healer-frontend .

# Run
docker run -p 3000:3000 ci-healer-frontend
```

---

## Deployment on Vercel

1. Push your repository to GitHub
2. Import the project at [vercel.com/new](https://vercel.com/new)
3. Set the **Root Directory** to `frontend`
4. Add environment variable: `NEXT_PUBLIC_API_URL=https://your-backend.railway.app`
5. Deploy — Vercel handles builds, CDN, and SSL automatically

See the full deployment guide: [../docs/DEPLOYMENT.md](../docs/DEPLOYMENT.md)
