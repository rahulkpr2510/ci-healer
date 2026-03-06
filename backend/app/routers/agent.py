# backend/app/routers/agent.py

import logging
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.db.database import get_db
from app.middleware.auth import get_current_user, get_current_user_from_token_or_query
from app.models.user import User
from app.models.run import Run
from app.models.fix import Fix
from app.models.ci_event import CiEvent
from app.schemas.run import (
    RunRequest,
    RunStartResponse,
    RunDetailResponse,
    RunSummarySchema,
    FixSchema,
    CiEventSchema,
    ScoreSchema,
    TimingSchema,
)
from app.services.run_service import start_run
from app.services.sse_service import subscribe

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["agent"])

# Rate limiter instance - will use app.state.limiter set in main.py
limiter = Limiter(key_func=get_remote_address)


# ── POST /api/run ─────────────────────────────────────────

@router.post("/run", response_model=RunStartResponse)
@limiter.limit("10/minute")
async def start_agent_run(
    request: Request,
    payload: RunRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Starts an agent run for the given repo.
    Returns immediately with run_id — use GET /api/run/{id} to poll
    or GET /api/run/{id}/stream for live SSE events.
    
    Rate limit: 10 requests per minute per IP.
    """
    # Basic GitHub URL validation
    if not payload.repo_url.startswith("https://github.com/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only GitHub repository URLs are supported (https://github.com/owner/repo)",
        )

    run_id = await start_run(
        db=db,
        user=current_user,
        repo_url=payload.repo_url,
        branch_prefix=payload.branch_prefix,
        max_iterations=payload.max_iterations,
        read_only=payload.read_only,
    )

    logger.info(
        "Run %s started by user %s for repo %s",
        run_id, current_user.github_username, payload.repo_url,
    )

    return RunStartResponse(run_id=run_id)


# ── GET /api/run/{run_id} ─────────────────────────────────

@router.get("/run/{run_id}", response_model=RunDetailResponse)
async def get_run_status(
    run_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns full run details including fixes, CI timeline, and score.
    Frontend polls this every few seconds while status is RUNNING.
    """
    result = await db.execute(
        select(Run).where(
            Run.run_id == run_id,
            Run.user_id == current_user.id,   # users can only see their own runs
        )
    )
    run = result.scalar_one_or_none()

    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Run not found",
        )

    # Fetch associated fixes
    fixes_result = await db.execute(
        select(Fix).where(Fix.run_id == run.id)
    )
    fixes = fixes_result.scalars().all()

    # Fetch CI events
    ci_result = await db.execute(
        select(CiEvent).where(CiEvent.run_id == run.id).order_by(CiEvent.iteration)
    )
    ci_events = ci_result.scalars().all()

    # Extract language / errors / iterations from persisted results_json blob
    _extra: dict = {}
    if run.results_json:
        try:
            import json as _json
            _extra = _json.loads(run.results_json)
        except Exception:
            pass

    return RunDetailResponse(
        run_id=run.run_id,
        repo_url=run.repo_url,
        repo_owner=run.repo_owner,
        repo_name=run.repo_name,
        team_name=run.team_name,
        team_leader=run.team_leader,
        mode=run.mode,
        branch_name=run.branch_name,
        pr_url=run.pr_url,
        final_status=run.final_status,
        total_failures_detected=run.total_failures_detected or 0,
        total_fixes_applied=run.total_fixes_applied or 0,
        total_commits=run.total_commits or 0,
        iterations_used=run.iterations_used or 0,
        score=ScoreSchema(
            base_score=run.base_score or 100,
            speed_bonus=run.speed_bonus or 0,
            efficiency_penalty=run.efficiency_penalty or 0,
            final_score=run.final_score or 0,
        ),
        timing=TimingSchema(
            started_at=run.started_at.isoformat() if run.started_at else None,
            finished_at=run.finished_at.isoformat() if run.finished_at else None,
            total_time_seconds=run.total_time_seconds,
        ),
        fixes=[
            FixSchema(
                file=f.file_path,
                bug_type=f.bug_type,
                line_number=f.line_number,
                commit_message=f.commit_message,
                status=f.status,
            )
            for f in fixes
        ],
        ci_timeline=[
            CiEventSchema(
                iteration=e.iteration,
                status=e.status,
                iteration_label=e.iteration_label,
                ran_at=e.ran_at.isoformat() if e.ran_at else None,
            )
            for e in ci_events
        ],
        created_at=run.created_at.isoformat(),
        primary_language=_extra.get("primary_language"),
        detected_languages=_extra.get("detected_languages") or [],
        agent_errors=_extra.get("agent_errors") or [],
        iterations_run=_extra.get("iterations_run") or 0,
        skip_reason=_extra.get("skip_reason"),
    )


# ── GET /api/run/{run_id}/events  (primary SSE path) ─────
# ── GET /api/run/{run_id}/stream (legacy alias kept)  ─────

def _sse_response(run_id: str) -> StreamingResponse:
    """Shared SSE response builder."""
    return StreamingResponse(
        subscribe(run_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",      # disables Nginx buffering
            "Connection": "keep-alive",
        },
    )


@router.get("/run/{run_id}/events")
async def stream_run_events_v2(
    run_id: str,
    current_user: User = Depends(get_current_user_from_token_or_query),
):
    """
    Server-Sent Events endpoint for live agent run updates.

    Emits events of the following types:
      AGENT_STARTED, REPO_CLONED, TEST_DISCOVERED, TEST_FAILED,
      FIX_GENERATED, COMMIT_CREATED, CI_RERUN, RUN_COMPLETED,
      log, ping, complete, error

    Authentication:
      - Authorization: Bearer <token> header  (preferred)
      - ?token=<jwt>  query param             (required for browser EventSource)

    Reconnect: EventSource reconnects automatically on network drop.
    The stream emits keepalive pings every 30 s to prevent proxy timeouts.
    """
    return _sse_response(run_id)


@router.get("/run/{run_id}/stream")
async def stream_run_events_legacy(
    run_id: str,
    current_user: User = Depends(get_current_user_from_token_or_query),
):
    """Legacy SSE path kept for backwards compatibility. Prefer /events."""
    return _sse_response(run_id)


# ── GET /api/repos ────────────────────────────────────────


