# CI Healer — AI Engine

> **Internal LangGraph service that autonomously repairs failing test suites using an LLM-driven multi-node agent graph.**

---

## Overview

The AI Engine is a self-contained FastAPI service that wraps a **LangGraph** directed graph. It is called exclusively by the backend service; it is **not** exposed to the public internet.

When invoked, the agent:

1. Clones the target repository to an isolated workspace directory
2. Detects the language and test framework
3. Runs static analysis and the test suite
4. Classifies each failure by bug type (linting, logic, import, type, etc.)
5. Generates minimal, file-level code fixes via an LLM
6. Applies the patches, commits them, and pushes a fix branch
7. Opens a pull request against the default branch
8. Polls GitHub Actions to verify CI passes
9. Iterates up to `max_iterations` times if CI still fails

---

## Agent Node Pipeline

```
repo_analyzer
      │
language_detector
      │
static_analyzer ◄──────────────────────────────────────────────┐
      │                                                        │
test_runner                                              (re-iterate if
      │                                                   CI fails and
failure_classifier                                     iterations remain)
      │                                                         │
      ├─ (failures found) ──► fix_generator                     │
      │                              │                          │
      │                        patch_applier                    │
      │                              │                          │
      │              (not read_only) ├──► git_commit            │
      │                              │          │               │
      │                              │   create_pull_request    │
      │                              │          │               │
      │                              │       ci_monitor ────────┘
      │                              │
      └─ (no failures) ──────────────┴──► finalize ──► END
```

### Node Descriptions

| Node                  | Responsibility                                               |
| --------------------- | ------------------------------------------------------------ |
| `repo_analyzer`       | Clones repo, builds file tree and manifest                   |
| `language_detector`   | Detects language, test framework, entry points               |
| `static_analyzer`     | Runs `flake8` / `eslint` / `tsc` depending on language       |
| `test_runner`         | Executes `pytest` / `jest` / `npm test`, captures output     |
| `failure_classifier`  | Parses output, maps each error to a `BugType` enum           |
| `fix_generator`       | Sends file + errors to LLM; batches multiple errors per file |
| `patch_applier`       | Sole file writer — writes `fix.after_snippet` to disk        |
| `git_commit`          | Creates fix branch, commits each changed file, pushes        |
| `create_pull_request` | Opens PR via GitHub REST API                                 |
| `ci_monitor`          | Polls GitHub Actions; treats `no_ci` as `PASSED`             |
| `finalize`            | Computes score, writes `results.json`, returns final state   |

---

## LLM Configuration

The engine supports two LLM providers, switchable via the `LLM_PROVIDER` environment variable:

| Provider           | Variable         | Free Tier  | Recommended Model         |
| ------------------ | ---------------- | ---------- | ------------------------- |
| **Groq** (default) | `GROQ_API_KEY`   | ✅ Yes     | `llama-3.3-70b-versatile` |
| Google Gemini      | `GOOGLE_API_KEY` | ✅ Limited | `gemini-2.5-flash`        |

Groq is strongly recommended for development — it is free, extremely fast (200 tokens/s), and the `llama-3.3-70b-versatile` model produces high-quality code repairs.

**Fix generation strategy:**

- **Single error per file** → single LLM call with targeted prompt
- **Multiple errors per file** → batched into one LLM call to prevent conflicting patches
- **Cache** → identical (file, error) pairs skip the LLM entirely within the same process lifetime
- **Rule-based fallback** → if the LLM returns unchanged code, deterministic regex/AST fixes are applied

---

## Environment Variables

Copy `.env.example` to `.env` and fill in the required values.

| Variable                 | Required     | Default                   | Description                                             |
| ------------------------ | ------------ | ------------------------- | ------------------------------------------------------- |
| `LLM_PROVIDER`           | ❌           | `groq`                    | `groq` or `gemini`                                      |
| `GROQ_API_KEY`           | ✅ if Groq   | —                         | From [console.groq.com](https://console.groq.com)       |
| `GROQ_MODEL`             | ❌           | `llama-3.3-70b-versatile` | Any Groq chat model                                     |
| `GOOGLE_API_KEY`         | ✅ if Gemini | —                         | From [aistudio.google.com](https://aistudio.google.com) |
| `GEMINI_MODEL`           | ❌           | `gemini-2.5-flash`        | Any Gemini chat model                                   |
| `LLM_TEMPERATURE`        | ❌           | `0.2`                     | Lower = more deterministic fixes                        |
| `LLM_MAX_TOKENS`         | ❌           | `8192`                    | Max tokens per LLM response                             |
| `DEFAULT_MAX_ITERATIONS` | ❌           | `5`                       | Max fix-iterate loops                                   |
| `GIT_AUTHOR_NAME`        | ❌           | `CI Healer Agent`         | Git commit author name                                  |
| `GIT_AUTHOR_EMAIL`       | ❌           | `agent@cihealer.dev`      | Git commit author email                                 |
| `GIT_COMMIT_PREFIX`      | ❌           | `[AI-AGENT]`              | Prepended to every commit message                       |
| `WORKSPACE_DIR`          | ❌           | `./workspace`             | Directory for cloned repos                              |
| `ENGINE_HOST`            | ❌           | `0.0.0.0`                 | Bind address                                            |
| `ENGINE_PORT`            | ❌           | `8001`                    | Listen port                                             |
| `BACKEND_ORIGIN`         | ❌           | `*`                       | Lock CORS to specific backend URL in prod               |

---

## Local Development

```bash
cd ai-engine

# Create virtual environment
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env — set GROQ_API_KEY at minimum

# Start with scoped hot-reload (excludes workspace/ from watcher)
uvicorn api.main:app \
  --host 0.0.0.0 --port 8001 \
  --reload --reload-dir api --reload-dir engine
```

> ⚠️ Always use `--reload-dir api --reload-dir engine`. Without this flag, uvicorn watches the entire directory including `workspace/`, which causes the server to restart mid-run whenever the agent writes files.

### Verify startup

```bash
curl http://localhost:8001/health
# {"status":"ok","provider":"groq","model":"llama-3.3-70b-versatile",...}
```

---

## API Endpoints

| Method | Path                 | Description                       |
| ------ | -------------------- | --------------------------------- |
| `POST` | `/engine/run`        | Trigger a full agent run          |
| `GET`  | `/runs/{run_id}/log` | Fetch accumulated live log events |
| `GET`  | `/health`            | Health check + provider info      |

### `POST /engine/run`

**Request body:**

```json
{
  "run_id": "uuid-from-backend",
  "repo_url": "https://github.com/owner/repo",
  "team_name": "Slytherin",
  "team_leader": "Rahul Kapoor",
  "github_token": "ghp_...",
  "max_iterations": 5,
  "read_only": false
}
```

**Response:** `EngineRunResult` schema — final status, fixes applied, CI timeline, score breakdown.

---

## Running Tests

```bash
cd ai-engine
.venv/bin/pytest tests/ -v
```

---

## Docker

```bash
# Build
docker build -t ci-healer-engine .

# Run (pass your API key)
docker run -p 8001:8001 \
  -e GROQ_API_KEY=gsk_... \
  -e LLM_PROVIDER=groq \
  -v ci_workspace:/workspace \
  ci-healer-engine
```

---

## Scoring

Each agent run produces a score:

| Component          | Value                               |
| ------------------ | ----------------------------------- |
| Base score         | 100 pts                             |
| Speed bonus        | +10 pts if completed in < 5 minutes |
| Efficiency penalty | −2 pts per commit over 20           |
| **Minimum**        | 0 pts                               |
