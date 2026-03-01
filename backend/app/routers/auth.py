# backend/app/routers/auth.py  — top imports section

import secrets
import hmac
import hashlib
import time
import logging
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.user import User
from app.middleware.auth import get_current_user
from app.services.github_oauth import (
    get_github_authorization_url,
    exchange_code_for_token,
    fetch_github_user,
    upsert_user,
)
from app.services.jwt_service import create_access_token
from app.schemas.auth import UserResponse, LogoutResponse
from config.settings import settings


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])

# ── OAuth state TTL (seconds) ─────────────────────────────
_STATE_TTL = 600  # 10 minutes


# ── Signed state helpers ──────────────────────────────────
def _generate_oauth_state() -> str:
    """
    Creates a self-contained, signed state token.
    Format: <timestamp>.<nonce>.<hmac>
    Works across multiple workers / processes without shared memory.
    """
    ts = str(int(time.time()))
    nonce = secrets.token_urlsafe(16)
    payload = f"{ts}.{nonce}"
    sig = hmac.new(
        settings.JWT_SECRET_KEY.encode(),
        payload.encode(),
        hashlib.sha256,
    ).hexdigest()
    return f"{payload}.{sig}"


def _verify_oauth_state(state: str) -> bool:
    """
    Returns True only if the state has a valid signature and is not expired.
    """
    try:
        ts_str, nonce, received_sig = state.rsplit(".", 2)
    except ValueError:
        return False

    payload = f"{ts_str}.{nonce}"
    expected_sig = hmac.new(
        settings.JWT_SECRET_KEY.encode(),
        payload.encode(),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected_sig, received_sig):
        return False

    # Check expiry
    try:
        if time.time() - float(ts_str) > _STATE_TTL:
            return False
    except ValueError:
        return False

    return True


# ── GET /auth/github ──────────────────────────────────────
@router.get("/github")
async def github_login():
    """
    Entry point for GitHub OAuth.
    Frontend calls this → backend redirects user to GitHub.
    
    Flow:
      1. Frontend button hits GET /auth/github
      2. This generates a state token + redirects to GitHub
      3. GitHub redirects back to /auth/callback?code=...&state=...
    """
    state = _generate_oauth_state()

    authorization_url = get_github_authorization_url(state=state)
    return RedirectResponse(url=authorization_url, status_code=302)


# ── GET /auth/callback ────────────────────────────────────
@router.get("/callback")
async def github_callback(
    code: str = Query(..., description="Temporary code from GitHub"),
    state: str = Query(..., description="CSRF state token"),
    db: AsyncSession = Depends(get_db),
):
    """
    GitHub redirects here after user grants access.
    
    Flow:
      1. Validate the state token (CSRF protection)
      2. Exchange code → GitHub access token
      3. Fetch user profile from GitHub API
      4. Upsert user in our DB
      5. Issue our own JWT
      6. Redirect to frontend dashboard with JWT in query param
         (frontend stores it in localStorage/cookie)
    """
    # ── CSRF check ────────────────────────────────────────
    if not _verify_oauth_state(state):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OAuth state. Please try logging in again.",
        )
    # (no discard needed — expiry window provides one-shot-like protection)

    # ── Exchange code for GitHub token ────────────────────
    try:
        github_token = await exchange_code_for_token(code=code)
    except ValueError as e:
        logger.error("Token exchange failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    # ── Fetch GitHub user profile ─────────────────────────
    try:
        github_user = await fetch_github_user(access_token=github_token)
    except ValueError as e:
        logger.error("GitHub user fetch failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch user profile from GitHub.",
        )

    # ── Upsert user in DB ─────────────────────────────────
    user = await upsert_user(db=db, github_user=github_user, access_token=github_token)

    # ── Issue JWT ─────────────────────────────────────────
    jwt_token = create_access_token(
        user_id=user.id,
        github_username=user.github_username,
    )

    # ── Redirect to frontend with token ──────────────────
    # Frontend catches this at /callback?token=... and stores it
    redirect_url = f"{settings.FRONTEND_URL}/auth/callback?token={jwt_token}"

    logger.info("OAuth complete for user: %s", user.github_username)
    return RedirectResponse(url=redirect_url, status_code=302)


# ── GET /auth/me ──────────────────────────────────────────
@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
):
    """Returns the current authenticated user's profile."""
    return UserResponse(
        id=current_user.id,
        github_id=current_user.github_id,
        github_username=current_user.github_username,
        github_email=current_user.github_email,
        github_avatar_url=current_user.github_avatar_url,
        created_at=current_user.created_at.isoformat(),
        last_login_at=current_user.last_login_at.isoformat() if current_user.last_login_at else None,
    )


# ── POST /auth/logout ─────────────────────────────────────
@router.post("/logout", response_model=LogoutResponse)
async def logout():
    """
    Stateless JWT logout — frontend just deletes the token.
    This endpoint exists for a clean API contract.
    """
    return LogoutResponse()
