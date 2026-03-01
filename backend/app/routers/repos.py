# backend/app/routers/repos.py

import logging
from fastapi import APIRouter, Depends, HTTPException, status

from app.middleware.auth import get_current_user
from app.models.user import User
from app.schemas.history import ReposResponse, RepoSchema
from app.services.github_api import fetch_user_repos

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["repos"])


# ── GET /api/repos ─────────────────────────────────────────

@router.get("/repos", response_model=ReposResponse)
async def get_user_repos(
    current_user: User = Depends(get_current_user),
):
    """
    Returns all GitHub repositories accessible to the authenticated user.

    Fetches live from the GitHub API using the stored OAuth access token,
    so the list is always up-to-date without any caching layer.
    """
    try:
        raw = await fetch_user_repos(current_user.github_access_token)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        )

    repos = [
        RepoSchema(
            id=r["id"],
            full_name=r["full_name"],
            owner=r["owner"]["login"],
            name=r["name"],
            html_url=r["html_url"],
            description=r.get("description"),
            private=r.get("private", False),
            default_branch=r.get("default_branch", "main"),
            updated_at=r.get("updated_at"),
            language=r.get("language"),
        )
        for r in raw
    ]

    return ReposResponse(repos=repos, count=len(repos))
