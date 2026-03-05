# backend/app/routers/analytics.py

import logging
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.database import get_db
from app.middleware.auth import get_current_user
from app.models.user import User
from app.models.run import Run
from app.models.fix import Fix
from app.schemas.run import RunSummarySchema
from app.schemas.history import (
    RepoAnalyticsResponse,
    AnalyticsSummarySchema,
    DashboardSummaryResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/analytics", tags=["analytics"])


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


@router.get("/dashboard/summary", response_model=DashboardSummaryResponse)
async def get_dashboard_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    High-level stats for the main dashboard home page.
    Total runs, repos touched, overall pass rate, total fixes.

    NOTE: This route must be registered before /{owner}/{repo} so FastAPI
    does not match the literal path "dashboard/summary" as a parameterized
    owner/repo pair.
    """
    runs_result = await db.execute(
        select(Run).where(Run.user_id == current_user.id)
    )
    runs = runs_result.scalars().all()

    unique_repos = {f"{r.repo_owner}/{r.repo_name}" for r in runs}
    passed = [r for r in runs if r.final_status == "PASSED"]
    # NO_ISSUES runs are healthy repos — exclude from pass-rate denominator
    eligible = [r for r in runs if r.final_status in ("PASSED", "FAILED")]
    total_fixes = sum(r.total_fixes_applied or 0 for r in runs)

    return DashboardSummaryResponse(
        total_runs=len(runs),
        unique_repos=len(unique_repos),
        total_fixes_applied=total_fixes,
        pass_rate=round(len(passed) / max(len(eligible), 1) * 100, 1),
        repos=list(unique_repos),
    )


@router.get("/{owner}/{repo}", response_model=RepoAnalyticsResponse)
async def get_repo_analytics(
    owner: str,
    repo: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Aggregated analytics for a specific repo.
    Powers the analytics charts on the per-repo dashboard page.
    """
    runs_result = await db.execute(
        select(Run).where(
            Run.user_id == current_user.id,
            Run.repo_owner == owner,
            Run.repo_name == repo,
        )
    )
    runs = runs_result.scalars().all()

    if not runs:
        return RepoAnalyticsResponse(
            owner=owner, repo=repo,
            summary=AnalyticsSummarySchema(),
            bug_type_distribution={},
            recent_runs=[],
        )

    total_runs = len(runs)
    passed = [r for r in runs if r.final_status == "PASSED"]
    failed = [r for r in runs if r.final_status == "FAILED"]
    # NO_ISSUES runs excluded from pass-rate denominator (healthy repos)
    eligible = [r for r in runs if r.final_status in ("PASSED", "FAILED")]

    avg_time = (
        sum(r.total_time_seconds for r in runs if r.total_time_seconds)
        / max(len([r for r in runs if r.total_time_seconds]), 1)
    )
    avg_score = sum(r.final_score or 0 for r in runs) / total_runs
    avg_fixes = sum(r.total_fixes_applied or 0 for r in runs) / total_runs

    # Bug type distribution across all fixes for this repo
    run_ids = [r.id for r in runs]
    fixes_result = await db.execute(
        select(Fix).where(Fix.run_id.in_(run_ids))
    )
    fixes = fixes_result.scalars().all()

    bug_distribution: dict[str, int] = {}
    for fix in fixes:
        bug_distribution[fix.bug_type] = bug_distribution.get(fix.bug_type, 0) + 1

    # Run history for timeline chart (last 10 runs)
    recent_runs = sorted(runs, key=lambda r: r.created_at, reverse=True)[:10]

    return RepoAnalyticsResponse(
        owner=owner,
        repo=repo,
        summary=AnalyticsSummarySchema(
            total_runs=total_runs,
            passed=len(passed),
            failed=len(failed),
            pass_rate=round(len(passed) / max(len(eligible), 1) * 100, 1),
            avg_time_seconds=round(avg_time, 1),
            avg_score=round(avg_score, 1),
            avg_fixes_per_run=round(avg_fixes, 1),
            total_fixes_ever=len(fixes),
        ),
        bug_type_distribution=bug_distribution,
        recent_runs=[_run_to_summary(r) for r in recent_runs],
    )
