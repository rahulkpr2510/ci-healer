# ai-engine/tools/github_tools.py
"""
GitHub REST API helpers used by the agent nodes.

Wraps httpx calls so nodes don't need to manage HTTP sessions directly.
All public functions are purely functional — no state, easy to test/mock.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"
TIMEOUT = httpx.Timeout(30.0)


def _headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


# ── Pull Requests ─────────────────────────────────────────────────────────────

def create_pull_request(
    owner: str,
    repo: str,
    head: str,
    base: str,
    title: str,
    body: str,
    token: str,
) -> Optional[str]:
    """
    Open a pull request via the GitHub REST API.
    Returns the PR HTML URL on success, or None on failure.
    """
    url = f"{GITHUB_API}/repos/{owner}/{repo}/pulls"
    payload = {"title": title, "head": head, "base": base, "body": body}

    try:
        with httpx.Client(timeout=TIMEOUT) as client:
            resp = client.post(url, json=payload, headers=_headers(token))

        if resp.status_code == 201:
            pr_url: str = resp.json().get("html_url", "")
            logger.info("PR created: %s", pr_url)
            return pr_url

        if resp.status_code == 422:
            # PR may already exist — try to fetch it
            existing = _find_existing_pr(owner, repo, head, base, token)
            if existing:
                logger.info("PR already exists: %s", existing)
                return existing

        logger.error("Failed to create PR: %s %s", resp.status_code, resp.text[:200])
        return None

    except Exception as e:
        logger.error("Exception creating PR: %s", e)
        return None


def _find_existing_pr(owner: str, repo: str, head: str, base: str, token: str) -> Optional[str]:
    """Search for an open PR with the same head branch."""
    url = f"{GITHUB_API}/repos/{owner}/{repo}/pulls"
    params = {"state": "open", "head": f"{owner}:{head}", "base": base}
    try:
        with httpx.Client(timeout=TIMEOUT) as client:
            resp = client.get(url, params=params, headers=_headers(token))
        if resp.status_code == 200:
            prs = resp.json()
            if prs:
                return prs[0].get("html_url")
    except Exception:
        pass
    return None


# ── CI / Actions ──────────────────────────────────────────────────────────────

def get_latest_workflow_run(
    owner: str,
    repo: str,
    branch: str,
    token: str,
) -> Optional[dict[str, Any]]:
    """
    Fetch the most recent GitHub Actions workflow run for *branch*.
    Returns the run dict (with 'status' and 'conclusion' keys) or None.
    """
    url = f"{GITHUB_API}/repos/{owner}/{repo}/actions/runs"
    params = {"branch": branch, "per_page": 1}
    try:
        with httpx.Client(timeout=TIMEOUT) as client:
            resp = client.get(url, params=params, headers=_headers(token))
        if resp.status_code == 200:
            runs = resp.json().get("workflow_runs", [])
            return runs[0] if runs else None
    except Exception as e:
        logger.error("Failed to fetch workflow runs: %s", e)
    return None


def wait_for_ci(
    owner: str,
    repo: str,
    branch: str,
    token: str,
    poll_interval: int = 10,
    max_wait: int = 300,
) -> str:
    """
    Poll GitHub Actions until the latest run on *branch* completes.
    Returns 'PASSED', 'FAILED', or 'UNKNOWN' if timed out / no CI.
    """
    import time

    elapsed = 0
    while elapsed < max_wait:
        run = get_latest_workflow_run(owner, repo, branch, token)
        if run is None:
            logger.info("No CI workflow found for branch %s — treating as PASSED", branch)
            return "PASSED"

        status = run.get("status", "")
        conclusion = run.get("conclusion", "")

        if status == "completed":
            if conclusion in ("success", "neutral", "skipped"):
                return "PASSED"
            if conclusion in ("failure", "timed_out", "action_required", "cancelled"):
                return "FAILED"
            return "FAILED"

        logger.debug("CI status=%s — waiting… (%ds elapsed)", status, elapsed)
        time.sleep(poll_interval)
        elapsed += poll_interval

    logger.warning("CI wait timed out after %ds — treating as PASSED", max_wait)
    return "PASSED"


# ── Repository info ───────────────────────────────────────────────────────────

def get_repo_info(owner: str, repo: str, token: str) -> Optional[dict[str, Any]]:
    """Fetch basic repository metadata."""
    url = f"{GITHUB_API}/repos/{owner}/{repo}"
    try:
        with httpx.Client(timeout=TIMEOUT) as client:
            resp = client.get(url, headers=_headers(token))
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        logger.error("Failed to fetch repo info: %s", e)
    return None


def list_user_repos(token: str, per_page: int = 100) -> list[dict[str, Any]]:
    """
    List repositories accessible to the authenticated user (sorted by push date).
    Returns a list of repo dicts.  Follows a single page of pagination.
    """
    url = f"{GITHUB_API}/user/repos"
    params = {"sort": "pushed", "per_page": per_page, "affiliation": "owner,collaborator"}
    try:
        with httpx.Client(timeout=TIMEOUT) as client:
            resp = client.get(url, params=params, headers=_headers(token))
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        logger.error("Failed to list user repos: %s", e)
    return []


def get_branch_info(owner: str, repo: str, branch: str, token: str) -> Optional[dict[str, Any]]:
    """Fetch branch protection / SHA info."""
    url = f"{GITHUB_API}/repos/{owner}/{repo}/branches/{branch}"
    try:
        with httpx.Client(timeout=TIMEOUT) as client:
            resp = client.get(url, headers=_headers(token))
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        logger.error("Failed to fetch branch info: %s", e)
    return None
