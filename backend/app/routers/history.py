# backend/app/routers/history.py

import logging
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.db.database import get_db
from app.middleware.auth import get_current_user
from app.models.user import User
from app.models.run import Run
from app.models.fix import Fix
from app.schemas.run import RunSummarySchema
from app.schemas.history import RepoHistoryResponse, AllHistoryResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/history", tags=["history"])


def _run_to_summary(r: Run) -> RunSummarySchema:
    return RunSummarySchema(
        run_id=r.run_id,
        repo_owner=r.repo_owner,
        repo_name=r.repo_name,
        repo_url=r.repo_url,
        final_status=r.final_status,
        total_fixes_applied=r.total_fixes_applied or 0,
        final_score=r.final_score,
        total_time_seconds=r.total_time_seconds,
        started_at=r.started_at.isoformat() if r.started_at else None,
    )


@router.get("/{owner}/{repo}", response_model=RepoHistoryResponse)
async def get_repo_history(
    owner: str,
    repo: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status_filter: str | None = Query(default=None),   # PASSED | FAILED | RUNNING
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns paginated run history for a specific repo.
    Scoped to the current user.
    """
    query = select(Run).where(
        Run.user_id == current_user.id,
        Run.repo_owner == owner,
        Run.repo_name == repo,
    )

    if status_filter:
        query = query.where(Run.final_status == status_filter.upper())

    query = query.order_by(desc(Run.created_at))
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    runs = result.scalars().all()

    # Count total for pagination
    count_query = select(Run).where(
        Run.user_id == current_user.id,
        Run.repo_owner == owner,
        Run.repo_name == repo,
    )
    count_result = await db.execute(count_query)
    total = len(count_result.scalars().all())

    return RepoHistoryResponse(
        owner=owner,
        repo=repo,
        total=total,
        page=page,
        page_size=page_size,
        runs=[_run_to_summary(r) for r in runs],
    )


@router.get("/all", response_model=AllHistoryResponse)
async def get_all_history(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """All runs across all repos for the current user — for the main dashboard."""
    query = (
        select(Run)
        .where(Run.user_id == current_user.id)
        .order_by(desc(Run.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(query)
    runs = result.scalars().all()

    return AllHistoryResponse(runs=[_run_to_summary(r) for r in runs])
