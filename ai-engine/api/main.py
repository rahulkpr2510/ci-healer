# ai-engine/api/main.py

import logging
import json
import os
import uuid
import asyncio
from contextlib import asynccontextmanager
from collections import defaultdict

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.schemas import EngineRunRequest, EngineRunResult, ScoreResult, FixResult, CiRunResult
from engine.orchestrator import run_agent
from engine.state import FixStatus
from engine.config import engine_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Trusted backend origins — set BACKEND_ORIGIN env var in production
_BACKEND_ORIGIN = os.environ.get("BACKEND_ORIGIN", "")
_ALLOWED_ORIGINS = (
    [_BACKEND_ORIGIN] if _BACKEND_ORIGIN else ["*"]
)

# ── Per-run live event store ───────────────────────────────
# run_id → list of {"type": ..., "node": ..., "level": ..., "text": ...}
_run_events: dict[str, list[dict]] = {}

# Maps all node key aliases used by the orchestrator → canonical frontend pipeline keys
_NODE_KEY_MAP: dict[str, str] = {
    "repo_analyzer":      "repo_analyzer",
    "repo":               "repo_analyzer",
    "language_detector":  "detect_lang",
    "lang":               "detect_lang",
    "detect_lang":        "detect_lang",
    "static_analyzer":    "static_analyzer",
    "static":             "static_analyzer",
    "test_runner":        "run_tests",
    "test":               "run_tests",
    "run_tests":          "run_tests",
    "failure_classifier": "failure_classifier",
    "classify":           "failure_classifier",
    "fix_generator":      "fix_generator",
    "fix":                "fix_generator",
    "patch_applier":      "patch_applier",
    "patch":              "patch_applier",
    "git_commit":         "git_commit",
    "commit":             "git_commit",
    "create_pull_request":"create_pr",
    "pr":                 "create_pr",
    "ci_monitor":         "ci_monitor",
    "ci":                 "ci_monitor",
    "finalize":           "finalize",
    "final":              "finalize",
}


def _make_observer(run_id: str):
    """
    Returns a callable observer that translates raw node events
    into frontend-friendly log messages and stores them per run_id.
    """
    NODE_START_LABELS: dict[str, str] = {
        "repo_analyzer":     "📦 Cloning repository...",
        "repo":              "📦 Cloning repository...",
        "language_detector": "🔍 Detecting language...",
        "lang":              "🔍 Detecting language...",
        "static_analyzer":   "🔬 Running static analysis...",
        "static":            "🔬 Running static analysis...",
        "test_runner":       "🧪 Running tests...",
        "test":              "🧪 Running tests...",
        "failure_classifier":"🗂️  Classifying failures...",
        "classify":          "🗂️  Classifying failures...",
        "fix_generator":     "🤖 Generating fixes with LLM...",
        "fix":               "🤖 Generating fixes with LLM...",
        "patch_applier":     "✏️  Applying patches to disk...",
        "patch":             "✏️  Applying patches to disk...",
        "git_commit":        "💾 Committing fixes to git...",
        "commit":            "💾 Committing fixes to git...",
        "create_pull_request":"🔀 Creating pull request...",
        "pr":                "🔀 Creating pull request...",
        "ci_monitor":        "⏳ Checking CI status...",
        "ci":                "⏳ Checking CI status...",
        "finalize":          "🏁 Finalizing run...",
        "final":             "🏁 Finalizing run...",
    }

    def observer(event: dict) -> None:
        ev_type = event.get("event", "")
        node    = event.get("node", "")
        msg: str | None = None
        level = "info"

        if ev_type == "node_start":
            msg = NODE_START_LABELS.get(node, f"▶ Starting {node}...")

        elif ev_type == "node_end":
            if node in ("static_analyzer", "static"):
                n = event.get("findings_count", "?")
                msg = f"  Static analysis: {n} findings"
            elif node in ("language_detector", "lang", "detect_lang"):
                lang = event.get("primary_language", "unknown")
                tier = event.get("support_tier", "")
                tier_label = {"full": "✅ full support", "partial": "⚠️  partial support", "none": "❌ no tooling"}.get(tier, tier)
                msg = f"  Language: {lang}" + (f" ({tier_label})" if tier_label else "")
                level = "success" if tier == "full" else "warning" if tier in ("partial", "none") else "info"
            elif node in ("test_runner", "test"):
                passed = event.get("test_passed", event.get("passed", False))
                msg = "  ✅ Tests PASSED" if passed else "  ❌ Tests FAILED"
                level = "success" if passed else "error"
            elif node in ("failure_classifier", "classify"):
                n = event.get("failures_count", 0)
                skip = event.get("skip_reason")
                if n == 0 and skip:
                    msg   = f"  ℹ️  {skip}"
                    level = "info"
                else:
                    msg   = f"  Classified {n} failure(s)"
                    level = "warning" if n > 0 else "success"
            elif node in ("fix_generator", "fix"):
                n = event.get("fixes_count", 0)
                skipped = event.get("skipped")
                if skipped == "tests_passed":
                    msg = "  Tests already pass — no fixes needed"
                    level = "success"
                else:
                    msg = f"  Generated {n} fix(es)"
                    level = "success" if n > 0 else "warning"
            elif node in ("patch_applier", "patch"):
                fix = event.get("latest_fix", {})
                if fix:
                    msg = f"  Patched {fix.get('file','')} — {fix.get('bug_type','')} [{fix.get('status','')}]"
            elif node in ("git_commit", "commit"):
                sha   = event.get("latest_commit")
                count = event.get("fixes_count", 0)
                if sha:
                    msg = f"  ✅ Committed {count} fix(es) → {sha}"
                    level = "success"
            elif node in ("create_pull_request", "pr"):
                url = event.get("pr_url")
                if url:
                    msg = f"  🔀 PR created: {url}"
                    level = "success"
            elif node in ("ci_monitor", "ci"):
                status = event.get("final_status", "?")
                level  = "success" if status == "PASSED" else ("error" if status == "FAILED" else "info")
                msg    = f"  CI: {status}"
            elif node in ("finalize", "final"):
                skip = event.get("skip_reason")
                status = event.get("final_status", "?")
                if status == "NO_ISSUES" and skip:
                    msg   = f"  ℹ️  {skip}"
                    level = "info"
                else:
                    msg   = f"  Final status: {status}"
            elif node in ("repo_analyzer", "repo"):
                files = event.get("source_count", event.get("source_files_count", "?"))
                tests = event.get("test_count", event.get("test_files_count", "?"))
                msg = f"  Scanned: {files} source files, {tests} test files"

            # Always surface tool-level errors (missing linters, timeouts) as warnings,
            # regardless of which node emitted them.
            tool_errors = event.get("tool_errors", [])
            if tool_errors:
                for err in tool_errors:
                    events_list = _run_events.setdefault(run_id, [])
                    events_list.append({"type": "log", "level": "warn", "text": f"  ⚠️  {err}"})

        if msg:
            events = _run_events.setdefault(run_id, [])
            pipeline_key = _NODE_KEY_MAP.get(node)
            # Use "node_start" / "node_end" as the event type so the frontend
            # pipeline can track which step is currently active vs completed.
            event_type = ev_type if ev_type in ("node_start", "node_end") else "log"
            entry: dict = {"type": event_type, "level": level, "text": msg}
            if pipeline_key:
                entry["node"] = pipeline_key
            events.append(entry)

    return observer


@asynccontextmanager
async def lifespan(app: FastAPI):
    engine_settings.validate_keys()
    from engine.orchestrator import get_compiled_graph
    get_compiled_graph()
    logger.info(
        "✅ LangGraph compiled and ready (provider: %s / %s)",
        engine_settings.LLM_PROVIDER, engine_settings.active_model,
    )
    yield
    logger.info("AI Engine shutting down")


app = FastAPI(
    title="CI Healer — AI Engine",
    version="1.0.0",
    description="Internal LangGraph agent service. Not public-facing.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)


# ── Global exception handlers ─────────────────────────────

@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    errors = [
        {"field": " → ".join(str(loc) for loc in e.get("loc", [])), "message": e["msg"]}
        for e in exc.errors()
    ]
    return JSONResponse(status_code=422, content={"detail": "Validation error", "errors": errors})


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled engine exception: %s", exc)
    return JSONResponse(status_code=500, content={"detail": "Internal engine error"})


# ── POST /engine/run ──────────────────────────────────────
@app.post("/engine/run", response_model=EngineRunResult)
async def run_engine(request: EngineRunRequest):
    """
    Triggers a full agent run.
    Called exclusively by backend/app/services/run_service.py.
    """
    from concurrent.futures import ThreadPoolExecutor
    import re

    # Guard: validate repo URL format
    if not re.match(r"https://github\.com/[^/]+/[^/]+", request.repo_url):
        raise HTTPException(
            status_code=400,
            detail="repo_url must be a valid GitHub repository URL (https://github.com/owner/repo)",
        )

    # Use the backend's run_id so log polling is correlated
    run_id = request.run_id or str(uuid.uuid4())
    _run_events[run_id] = [{"type": "log", "level": "info", "text": f"🚀 Run started: {request.repo_url}"}]
    observer = _make_observer(run_id)

    logger.info("Engine run requested: repo=%s team=%s run_id=%s", request.repo_url, request.team_name, run_id)

    loop = asyncio.get_event_loop()
    executor = ThreadPoolExecutor(max_workers=1)

    try:
        final_state = await loop.run_in_executor(
            executor,
            lambda: run_agent(
                repo_url=request.repo_url,
                team_name=request.team_name,
                team_leader=request.team_leader,
                github_token=request.github_token,
                max_iterations=request.max_iterations,
                read_only=request.read_only,
                observer=observer,
            ),
        )
    except Exception as e:
        logger.exception("Agent run failed: %s", e)
        _run_events.pop(run_id, None)
        raise HTTPException(status_code=500, detail=f"Agent run failed: {str(e)}")

    # Schedule cleanup of event store after 10 minutes
    async def _cleanup():
        await asyncio.sleep(600)
        _run_events.pop(run_id, None)
    asyncio.create_task(_cleanup())

    # ── Map final state → response schema ─────────────────
    fixes    = final_state.get("fixes", [])
    ci_runs  = final_state.get("ci_runs", [])
    failures = final_state.get("failures", [])
    score    = final_state.get("score")
    max_iter = final_state.get("max_iterations", 5)

    fix_results = [
        FixResult(
            file=f.file,
            bug_type=f.bug_type.value,
            line_number=f.line,
            commit_message=f.commit_message,
            status=f.status.value,
        )
        for f in fixes
    ]

    ci_results = [
        CiRunResult(
            iteration=r.iteration,
            status=r.status.value,
            timestamp=r.timestamp,
            iteration_label=f"{r.iteration}/{max_iter}",
        )
        for r in ci_runs
    ]

    score_result = ScoreResult(
        base_score=score.base_score if score else 100,
        speed_bonus=score.speed_bonus if score else 0,
        efficiency_penalty=score.efficiency_penalty if score else 0,
        final_score=score.final_score if score else 0,
    )

    results_json = None
    repo_path = final_state.get("repo_local_path")
    if repo_path:
        results_path = os.path.join(repo_path, "results.json")
        if os.path.exists(results_path):
            try:
                with open(results_path) as f:
                    results_json = json.load(f)
            except Exception:
                pass

    agent_errors = final_state.get("agent_errors", [])

    # Emit any accumulated agent errors as warning log lines so they appear in the
    # frontend log stream even if the observer didn't catch them during the run.
    if agent_errors:
        _run_events.setdefault(run_id, []).extend([
            {"type": "log", "level": "warn", "text": f"  ⚠️  {err}"}
            for err in agent_errors
        ])

    return EngineRunResult(
        final_status=final_state.get("final_status", "FAILED"),
        branch_name=final_state.get("branch_name"),
        pr_url=final_state.get("pr_url"),
        total_failures=len(failures),
        total_fixes_applied=len([f for f in fixes if f.status == FixStatus.FIXED]),
        total_commits=len(final_state.get("commits", [])),
        total_time_seconds=final_state.get("total_time_seconds"),
        skip_reason=final_state.get("skip_reason"),
        primary_language=final_state.get("primary_language"),
        detected_languages=final_state.get("detected_languages", []),
        iterations_run=final_state.get("current_iteration", 1),
        score=score_result,
        fixes=fix_results,
        ci_timeline=ci_results,
        agent_output=[f.to_agent_output() for f in failures],
        agent_errors=agent_errors,
        results_json=results_json,
    )


# ── GET /runs/{run_id}/log ────────────────────────────────
@app.get("/runs/{run_id}/log")
async def get_run_log(run_id: str):
    """
    Returns accumulated live log events for a run.
    Backend polls this every 2 s and forwards events to SSE.
    """
    return {"run_id": run_id, "events": _run_events.get(run_id, [])}


# ── GET /health ───────────────────────────────────────────
@app.get("/health")
def health():
    return {
        "status": "ok",
        "provider": engine_settings.LLM_PROVIDER,
        "model": engine_settings.active_model,
        "workspace": engine_settings.workspace_path,
    }


# ── Entrypoint ────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host=engine_settings.ENGINE_HOST,
        port=engine_settings.ENGINE_PORT,
        reload=False,
    )
