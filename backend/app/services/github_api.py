# backend/app/services/github_api.py
"""GitHub API helpers — used for live data fetching (e.g., user repos)."""

import logging
import httpx

logger = logging.getLogger(__name__)

GITHUB_REPOS_URL = "https://api.github.com/user/repos"

_GITHUB_HEADERS = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}


async def fetch_user_repos(access_token: str) -> list[dict]:
    """
    Fetches all repositories accessible to the authenticated user via
    their GitHub OAuth access token (owner + collaborator + org member).

    Paginates through all pages automatically (100 per page).

    Returns a list of raw GitHub repository dicts.
    """
    repos: list[dict] = []
    page = 1

    async with httpx.AsyncClient(timeout=30) as client:
        headers = {
            **_GITHUB_HEADERS,
            "Authorization": f"Bearer {access_token}",
        }

        while True:
            resp = await client.get(
                GITHUB_REPOS_URL,
                headers=headers,
                params={
                    "affiliation": "owner,collaborator,organization_member",
                    "sort": "updated",
                    "direction": "desc",
                    "per_page": 100,
                    "page": page,
                },
            )

            if resp.status_code == 401:
                raise ValueError("GitHub token is invalid or has expired. Please re-authenticate.")

            if resp.status_code != 200:
                logger.error(
                    "GitHub repos fetch failed: status=%s body=%s",
                    resp.status_code, resp.text[:200],
                )
                raise ValueError(
                    f"Failed to fetch repositories from GitHub (HTTP {resp.status_code})."
                )

            data: list[dict] = resp.json()

            if not data:
                break

            repos.extend(data)

            # If fewer than 100 results returned, we're on the last page
            if len(data) < 100:
                break

            page += 1

    logger.info("Fetched %d repos for token ending …%s", len(repos), access_token[-4:])
    return repos
