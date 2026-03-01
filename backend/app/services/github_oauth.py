# backend/app/services/github_oauth.py

import httpx
import logging
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user import User
from config.settings import settings

logger = logging.getLogger(__name__)

GITHUB_OAUTH_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_URL = "https://api.github.com/user"
GITHUB_USER_EMAILS_URL = "https://api.github.com/user/emails"


# ── Step 1: Build the redirect URL ───────────────────────
def get_github_authorization_url(state: str) -> str:
    """
    Returns the GitHub OAuth URL the frontend redirects the user to.
    Scopes:
      - read:user  → profile info
      - user:email → email address
      - repo       → read/write repos for agent operations
    """
    params = (
        f"?client_id={settings.GITHUB_CLIENT_ID}"
        f"&redirect_uri={settings.GITHUB_REDIRECT_URI}"
        f"&scope=read:user+user:email+repo"
        f"&state={state}"
    )
    return f"{GITHUB_OAUTH_URL}{params}"


# ── Step 2: Exchange code → access token ─────────────────
async def exchange_code_for_token(code: str) -> str:
    """
    Sends the temporary code GitHub gave us and gets back
    a permanent access token for the user.
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            GITHUB_TOKEN_URL,
            headers={"Accept": "application/json"},
            data={
                "client_id": settings.GITHUB_CLIENT_ID,
                "client_secret": settings.GITHUB_CLIENT_SECRET,
                "code": code,
                "redirect_uri": settings.GITHUB_REDIRECT_URI,
            },
            timeout=15,
        )

    if response.status_code != 200:
        logger.error("GitHub token exchange failed: %s", response.text)
        raise ValueError(f"GitHub token exchange failed: {response.status_code}")

    data = response.json()

    if "error" in data:
        logger.error("GitHub OAuth error: %s — %s", data.get("error"), data.get("error_description"))
        raise ValueError(data.get("error_description", "GitHub OAuth failed"))

    access_token = data.get("access_token")
    if not access_token:
        raise ValueError("No access_token in GitHub response")

    return access_token


# ── Step 3: Fetch GitHub user profile ────────────────────
async def fetch_github_user(access_token: str) -> dict:
    """
    Uses the access token to get the user's GitHub profile.
    Falls back to /user/emails if email is not public.
    """
    async with httpx.AsyncClient() as client:
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/vnd.github+json",
        }

        # Fetch main profile
        user_resp = await client.get(GITHUB_USER_URL, headers=headers, timeout=10)
        if user_resp.status_code != 200:
            raise ValueError(f"Failed to fetch GitHub user: {user_resp.status_code}")

        user_data = user_resp.json()

        # If email is private, fetch from /user/emails
        if not user_data.get("email"):
            emails_resp = await client.get(GITHUB_USER_EMAILS_URL, headers=headers, timeout=10)
            if emails_resp.status_code == 200:
                emails = emails_resp.json()
                primary = next(
                    (e["email"] for e in emails if e.get("primary") and e.get("verified")),
                    None,
                )
                user_data["email"] = primary

    return user_data


# ── Step 4: Upsert user into DB ───────────────────────────
async def upsert_user(
    db: AsyncSession,
    github_user: dict,
    access_token: str,
) -> User:
    """
    Creates a new user or updates an existing one.
    Keyed on github_id — never duplicates.
    """
    github_id = github_user["id"]

    result = await db.execute(
        select(User).where(User.github_id == github_id)
    )
    user = result.scalar_one_or_none()

    if user:
        # Update existing user — token may have changed
        user.github_access_token = access_token
        user.github_username = github_user.get("login", user.github_username)
        user.github_email = github_user.get("email") or user.github_email
        user.github_avatar_url = github_user.get("avatar_url") or user.github_avatar_url
        user.last_login_at = datetime.now(timezone.utc)
        logger.info("Updated existing user: %s", user.github_username)
    else:
        # Create new user
        user = User(
            github_id=github_id,
            github_username=github_user.get("login", ""),
            github_email=github_user.get("email"),
            github_avatar_url=github_user.get("avatar_url"),
            github_access_token=access_token,
            last_login_at=datetime.now(timezone.utc),
        )
        db.add(user)
        logger.info("Created new user: %s", user.github_username)

    await db.flush()   # assigns user.id without committing yet
    return user


# ── Step 5: Fetch user's repos via their token ───────────
async def fetch_user_repos(access_token: str) -> list[dict]:
    """
    Returns the user's accessible repos (owned + collaborator).
    Used by GET /api/repos to populate the repo selector.
    """
    repos = []
    page = 1

    async with httpx.AsyncClient() as client:
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/vnd.github+json",
        }

        while True:
            resp = await client.get(
                "https://api.github.com/user/repos",
                headers=headers,
                params={
                    "per_page": 100,
                    "page": page,
                    "sort": "updated",
                    "affiliation": "owner,collaborator",
                },
                timeout=15,
            )

            if resp.status_code != 200:
                logger.warning("GitHub repos fetch failed page %d: %s", page, resp.status_code)
                break

            batch = resp.json()
            if not batch:
                break

            repos.extend([
                {
                    "id": r["id"],
                    "full_name": r["full_name"],
                    "owner": r["owner"]["login"],
                    "name": r["name"],
                    "html_url": r["html_url"],
                    "description": r.get("description"),
                    "private": r["private"],
                    "default_branch": r.get("default_branch", "main"),
                    "updated_at": r.get("updated_at"),
                    "language": r.get("language"),
                }
                for r in batch
            ])

            # GitHub paginates at 100 — stop if last page
            if len(batch) < 100:
                break
            page += 1

    return repos
