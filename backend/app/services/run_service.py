# backend/app/services/run_service.py

import asyncio
import json
import logging
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.run import Run
from app.models.fix import Fix as FixModel
from app.models.ci_event import CiEvent
from app.models.user import User
from app.services.sse_service import broadcast, close_stream
from config.settings import settings

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=4)


# ── Public: kick off an agent run ────────────────────────

async def start_run(
    db: AsyncSession,
    user: User,
    repo_url: str,
    team_name: str,
    team_leader: str,
    max_iterations: int = 5,
    read_only: bool = False,
) -> str:
    """
    Creates a Run record in DB, fires off the agent call async,
    returns run_id immediately so frontend can start polling/SSE.
    """
    run_id = str(uuid.uuid4())
    owner, repo_name = _parse_repo_url(repo_url)

    # ── Persist initial run record ────────────────────────
    run = Run(
        run_id=run_id,
        user_id=user.id,
        repo_url=repo_url,
        repo_owner=owner,
        repo_name=repo_name,
        team_name=team_name,
        team_leader=team_leader,
        mode="analyze-repository" if read_only else "run-agent",
        max_iterations=max_iterations,
        final_status="RUNNING",
        started_at=datetime.now(timezone.utc),
    )
    db.add(run)
    await db.flush()   # get run.id without committing
    db_run_id = run.id

    await db.commit()

    # ── Fire agent run in background ─────────────────────
    asyncio.create_task(
        _run_agent_background(
            run_id=run_id,
            db_run_id=db_run_id,
            user_github_token=user.github_access_token,
            repo_url=repo_url,
            team_name=team_name,
            team_leader=team_leader,
            max_iterations=max_iterations,
            read_only=read_only,
        )
    )

    return run_id


# ── Background worker ─────────────────────────────────────

async def _run_agent_background(
    run_id: str,
    db_run_id: int,
    user_github_token: str,
    repo_url: str,
    team_name: str,
    team_leader: str,
    max_iterations: int,
    read_only: bool,
) -> None:
    """
    Calls AI engine via HTTP, streams events to SSE,
    persists final result to DB. Runs as an asyncio background task.
    """
    from app.db.database import AsyncSessionLocal

    try:
        # ── Broadcast AGENT_STARTED ────────────────────────
        await broadcast(run_id, {
            "type": "AGENT_STARTED",
            "run_id": run_id,
            "repo_url": repo_url,
            "team_name": team_name,
        })
        await broadcast(run_id, {
            "type": "log",
            "level": "info",
            "text": "Agent run started",
            "run_id": run_id,
        })

        # ── Call AI Engine (with live log polling in parallel) ──
        poll_task = asyncio.create_task(
            _poll_engine_logs(run_id)
        )
        try:
            engine_result = await _call_engine(
                run_id=run_id,
                repo_url=repo_url,
                team_name=team_name,
                team_leader=team_leader,
                github_token=user_github_token,
                max_iterations=max_iterations,
                read_only=read_only,
            )
        finally:
            poll_task.cancel()
            try:
                await poll_task
            except asyncio.CancelledError:
                pass

        # ── Broadcast semantic events from result ─────────
        await _broadcast_semantic_events(run_id, engine_result)

        # ── Persist to DB ─────────────────────────────────
        async with AsyncSessionLocal() as db:
            await _persist_result(
                db=db,
                db_run_id=db_run_id,
                run_id=run_id,
                engine_result=engine_result,
            )

        # ── Broadcast RUN_COMPLETED ────────────────────────
        final_status = engine_result.get("final_status", "FAILED")
        skip_reason  = engine_result.get("skip_reason")

        # When there's nothing to fix, emit an informational log line
        # so users see a clear explanation rather than a bare status.
        if final_status == "NO_ISSUES" and skip_reason:
            await broadcast(run_id, {
                "type": "log",
                "level": "info",
                "run_id": run_id,
                "text": f"ℹ️  {skip_reason}",
            })

        await broadcast(run_id, {
            "type": "RUN_COMPLETED",
            "run_id": run_id,
            "final_status": final_status,
            "score": engine_result.get("score", {}).get("final_score", 0),
            "skip_reason": skip_reason,
        })
        await broadcast(run_id, {
            "type": "complete",
            "run_id": run_id,
            "final_status": final_status,
            "skip_reason": skip_reason,
        })

    except Exception as e:
        logger.exception("Background run failed for %s: %s", run_id, e)
        await broadcast(run_id, {
            "type": "error",
            "run_id": run_id,
            "message": str(e),
        })

        # Mark run as failed in DB
        async with AsyncSessionLocal() as db:
            await _mark_run_failed(db, db_run_id)

    finally:
        await close_stream(run_id)


async def _broadcast_semantic_events(run_id: str, engine_result: dict) -> None:
    """Broadcast semantic SSE events based on engine result."""
    # REPO_CLONED
    if engine_result.get("branch_name"):
        await broadcast(run_id, {
            "type": "REPO_CLONED",
            "run_id": run_id,
            "branch_name": engine_result.get("branch_name"),
            "primary_language": engine_result.get("primary_language"),
            "detected_languages": engine_result.get("detected_languages", []),
        })

    # Log primary language detection
    primary_lang = engine_result.get("primary_language")
    if primary_lang and primary_lang != "unknown":
        await broadcast(run_id, {
            "type": "log",
            "level": "info",
            "run_id": run_id,
            "text": f"🌐 Detected language: {primary_lang}",
        })

    # Broadcast tool-level errors (missing linters, timeouts, etc.) as warnings
    for err in engine_result.get("agent_errors", []):
        await broadcast(run_id, {
            "type": "log",
            "level": "warn",
            "run_id": run_id,
            "text": f"⚠️  Tool error: {err}",
        })

    # TEST_DISCOVERED + TEST_FAILED
    total_failures = engine_result.get("total_failures", 0)
    if total_failures > 0:
        await broadcast(run_id, {
            "type": "TEST_DISCOVERED",
            "run_id": run_id,
        })
        await broadcast(run_id, {
            "type": "TEST_FAILED",
            "run_id": run_id,
            "failures_count": total_failures,
        })

    # FIX_GENERATED for each fix
    for fix in engine_result.get("fixes", []):
        await broadcast(run_id, {
            "type": "FIX_GENERATED",
            "run_id": run_id,
            "file": fix.get("file"),
            "bug_type": fix.get("bug_type"),
            "line": fix.get("line_number"),
            "text": fix.get("commit_message"),
        })

    # COMMIT_CREATED
    total_commits = engine_result.get("total_commits", 0)
    if total_commits > 0:
        await broadcast(run_id, {
            "type": "COMMIT_CREATED",
            "run_id": run_id,
            "commit_count": total_commits,
        })

    # CI_RERUN for each CI timeline entry
    for ci_run in engine_result.get("ci_timeline", []):
        await broadcast(run_id, {
            "type": "CI_RERUN",
            "run_id": run_id,
            "iteration": ci_run.get("iteration"),
            "final_status": ci_run.get("status"),
        })


# ── Call the AI engine HTTP service ──────────────────────

async def _poll_engine_logs(run_id: str) -> None:
    """
    Polls the AI engine's /runs/{run_id}/log endpoint every 2 s
    and forwards any new log events to the SSE stream in real time.
    """
    seen = 0
    while True:
        await asyncio.sleep(2)
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(
                    f"{settings.AI_ENGINE_URL}/runs/{run_id}/log"
                )
                if resp.status_code == 200:
                    events = resp.json().get("events", [])
                    for ev in events[seen:]:
                        await broadcast(run_id, ev)
                    seen = len(events)
        except Exception:
            pass  # engine temporarily unavailable — keep retrying


async def _call_engine(
    run_id: str,
    repo_url: str,
    team_name: str,
    team_leader: str,
    github_token: str,
    max_iterations: int,
    read_only: bool,
) -> dict:
    payload = {
        "run_id": run_id,          # correlates engine log store with SSE stream
        "repo_url": repo_url,
        "team_name": team_name,
        "team_leader": team_leader,
        "github_token": github_token,
        "max_iterations": max_iterations,
        "read_only": read_only,
    }

    await broadcast(run_id, {
        "type": "log", "level": "info",
        "text": f"Connecting to AI engine at {settings.AI_ENGINE_URL}",
    })

    # Transient HTTP status codes that warrant a retry (engine starting up / overloaded)
    _RETRYABLE_STATUSES = {502, 503, 504}
    _MAX_RETRIES = 5
    _BASE_DELAY = 5  # seconds

    last_error: Exception | None = None
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            async with httpx.AsyncClient(timeout=settings.AI_ENGINE_TIMEOUT) as client:
                response = await client.post(
                    f"{settings.AI_ENGINE_URL}/engine/run",
                    json=payload,
                )

            if response.status_code == 200:
                result = response.json()
                await broadcast(run_id, {
                    "type": "log", "level": "success",
                    "text": f"Engine completed with status: {result.get('final_status')}",
                })
                return result

            if response.status_code in _RETRYABLE_STATUSES:
                last_error = RuntimeError(
                    f"AI engine returned {response.status_code}: {response.text[:300]}"
                )
                delay = _BASE_DELAY * attempt
                logger.warning(
                    "Engine returned %s on attempt %d/%d for run %s — retrying in %ds",
                    response.status_code, attempt, _MAX_RETRIES, run_id, delay,
                )
                await broadcast(run_id, {
                    "type": "log", "level": "warn",
                    "text": (
                        f"AI engine returned {response.status_code} "
                        f"(attempt {attempt}/{_MAX_RETRIES}) — "
                        f"retrying in {delay}s…"
                    ),
                })
                await asyncio.sleep(delay)
                continue

            # Non-retryable error (4xx, etc.) — fail immediately
            raise RuntimeError(
                f"AI engine returned {response.status_code}: {response.text[:300]}"
            )

        except httpx.TransportError as exc:
            # Connection-level failures (engine not yet up, network hiccup)
            last_error = exc
            delay = _BASE_DELAY * attempt
            logger.warning(
                "Engine connection error on attempt %d/%d for run %s (%s) — retrying in %ds",
                attempt, _MAX_RETRIES, run_id, exc, delay,
            )
            await broadcast(run_id, {
                "type": "log", "level": "warn",
                "text": (
                    f"Cannot reach AI engine (attempt {attempt}/{_MAX_RETRIES}) — "
                    f"retrying in {delay}s…"
                ),
            })
            await asyncio.sleep(delay)

    raise RuntimeError(
        f"AI engine unavailable after {_MAX_RETRIES} attempts: {last_error}"
    )


# ── Persist engine result to DB ───────────────────────────

async def _persist_result(
    db: AsyncSession,
    db_run_id: int,
    run_id: str,
    engine_result: dict,
) -> None:
    from sqlalchemy import select

    result = await db.execute(select(Run).where(Run.id == db_run_id))
    run = result.scalar_one_or_none()

    if not run:
        logger.error("Run %s not found in DB during persist", run_id)
        return

    score = engine_result.get("score", {})
    run.final_status = engine_result.get("final_status", "FAILED")
    run.branch_name = engine_result.get("branch_name")
    run.pr_url = engine_result.get("pr_url")
    run.total_failures_detected = engine_result.get("total_failures", 0)
    run.total_fixes_applied = engine_result.get("total_fixes_applied", 0)
    run.total_commits = engine_result.get("total_commits", 0)
    run.iterations_used = len(engine_result.get("ci_timeline", []))
    run.total_time_seconds = engine_result.get("total_time_seconds")
    run.base_score = score.get("base_score", 100)
    run.speed_bonus = score.get("speed_bonus", 0)
    run.efficiency_penalty = score.get("efficiency_penalty", 0)
    run.final_score = score.get("final_score", 0)
    run.finished_at = datetime.now(timezone.utc)
    run.results_json = json.dumps({
        "results_json":        engine_result.get("results_json") or {},
        "primary_language":    engine_result.get("primary_language"),
        "detected_languages":  engine_result.get("detected_languages", []),
        "agent_errors":        engine_result.get("agent_errors", []),
        "iterations_run":      engine_result.get("iterations_run", 0),
    })

    # ── Persist fixes ─────────────────────────────────────
    for fix_data in engine_result.get("fixes", []):
        fix = FixModel(
            run_id=db_run_id,
            file_path=fix_data.get("file", ""),
            bug_type=fix_data.get("bug_type", "UNKNOWN"),
            line_number=fix_data.get("line_number"),
            commit_message=fix_data.get("commit_message"),
            status=fix_data.get("status", "FAILED"),
        )
        db.add(fix)

    # ── Persist CI events ─────────────────────────────────
    for ci_data in engine_result.get("ci_timeline", []):
        event = CiEvent(
            run_id=db_run_id,
            iteration=ci_data.get("iteration", 0),
            status=ci_data.get("status", "FAILED"),
            iteration_label=ci_data.get("iteration_label"),
        )
        db.add(event)

    await db.commit()
    logger.info("Run %s persisted to DB", run_id)


async def _mark_run_failed(db: AsyncSession, db_run_id: int) -> None:
    from sqlalchemy import select
    result = await db.execute(select(Run).where(Run.id == db_run_id))
    run = result.scalar_one_or_none()
    if run:
        run.final_status = "FAILED"
        run.finished_at = datetime.now(timezone.utc)
        await db.commit()


# ── Helpers ───────────────────────────────────────────────

def _parse_repo_url(repo_url: str) -> tuple[str, str]:
    import re
    match = re.match(r"https://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$", repo_url)
    if match:
        return match.group(1), match.group(2)
    return "unknown", "unknown"
