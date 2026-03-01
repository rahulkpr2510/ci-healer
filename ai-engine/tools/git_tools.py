# ai-engine/tools/git_tools.py
"""
Git utility helpers used by the agent nodes.

These wrap subprocess / GitPython calls used throughout the pipeline.
All functions accept an absolute repo path and return plain Python types
so they are easy to test and mock.
"""

from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


# ── Low-level git helpers ─────────────────────────────────────────────────────

def run_git(args: list[str], cwd: str, check: bool = True) -> subprocess.CompletedProcess:
    """Run a git command in *cwd* and return the CompletedProcess result."""
    cmd = ["git"] + args
    logger.debug("git %s  (cwd=%s)", " ".join(args), cwd)
    return subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=check,
    )


def clone_repo(repo_url: str, dest_dir: str, token: Optional[str] = None) -> str:
    """
    Clone *repo_url* into *dest_dir*.

    If *token* is provided the URL is rewritten to include credentials so the
    clone works for private repos without requiring SSH keys.

    Returns the absolute path to the cloned repository.
    """
    auth_url = repo_url
    if token:
        # Inject token: https://x-access-token:TOKEN@github.com/…
        auth_url = repo_url.replace("https://", f"https://x-access-token:{token}@")

    os.makedirs(dest_dir, exist_ok=True)
    run_git(["clone", "--depth=1", auth_url, dest_dir], cwd=os.path.dirname(dest_dir) or ".")
    logger.info("Cloned %s → %s", repo_url, dest_dir)
    return dest_dir


def get_default_branch(repo_path: str) -> str:
    """Return the default branch name (main / master / …)."""
    try:
        result = run_git(
            ["symbolic-ref", "refs/remotes/origin/HEAD", "--short"],
            cwd=repo_path,
            check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            # "origin/main" → "main"
            return result.stdout.strip().split("/", 1)[-1]
    except Exception:
        pass

    # Fallback: try common names
    for branch in ("main", "master", "develop"):
        res = run_git(["rev-parse", "--verify", branch], cwd=repo_path, check=False)
        if res.returncode == 0:
            return branch

    return "main"


def create_branch(repo_path: str, branch_name: str) -> None:
    """Create and checkout a new branch.  No-op if it already exists."""
    result = run_git(["checkout", "-b", branch_name], cwd=repo_path, check=False)
    if result.returncode != 0:
        # Branch may already exist — try to check it out
        run_git(["checkout", branch_name], cwd=repo_path)
    logger.info("Switched to branch: %s", branch_name)


def stage_file(repo_path: str, file_path: str) -> None:
    """Stage a single file for commit."""
    run_git(["add", file_path], cwd=repo_path)


def commit(repo_path: str, message: str, author_name: str, author_email: str) -> str:
    """
    Commit staged changes with *message*.
    Returns the short commit SHA on success.
    """
    env = os.environ.copy()
    env["GIT_AUTHOR_NAME"] = author_name
    env["GIT_AUTHOR_EMAIL"] = author_email
    env["GIT_COMMITTER_NAME"] = author_name
    env["GIT_COMMITTER_EMAIL"] = author_email

    result = subprocess.run(
        ["git", "commit", "-m", message],
        cwd=repo_path,
        capture_output=True,
        text=True,
        env=env,
    )
    if result.returncode != 0:
        logger.warning("git commit failed: %s", result.stderr.strip())
        return ""

    # Extract short SHA from output ("main abc1234] …")
    try:
        sha_line = result.stdout.splitlines()[0]
        sha = sha_line.split("]")[0].split()[-1]
        return sha
    except (IndexError, ValueError):
        return ""


def push_branch(repo_path: str, branch_name: str, token: Optional[str] = None) -> bool:
    """
    Push *branch_name* to origin.  Returns True on success.

    If *token* is provided it rewrites the remote URL to include credentials.
    """
    if token:
        # Rewrite origin URL to include token
        result = run_git(["remote", "get-url", "origin"], cwd=repo_path, check=False)
        if result.returncode == 0:
            url = result.stdout.strip()
            auth_url = url.replace("https://", f"https://x-access-token:{token}@")
            run_git(["remote", "set-url", "origin", auth_url], cwd=repo_path)

    result = run_git(
        ["push", "-u", "origin", branch_name],
        cwd=repo_path,
        check=False,
    )
    if result.returncode != 0:
        logger.error("git push failed: %s", result.stderr.strip())
        return False

    logger.info("Pushed branch %s to origin", branch_name)
    return True


def get_diff(repo_path: str, file_path: str) -> str:
    """Return the unstaged diff for *file_path* (empty string if none)."""
    result = run_git(["diff", file_path], cwd=repo_path, check=False)
    return result.stdout if result.returncode == 0 else ""


def get_staged_diff(repo_path: str) -> str:
    """Return the staged diff for all files."""
    result = run_git(["diff", "--cached"], cwd=repo_path, check=False)
    return result.stdout if result.returncode == 0 else ""


def has_uncommitted_changes(repo_path: str) -> bool:
    """Return True if there are any staged or unstaged changes."""
    result = run_git(["status", "--porcelain"], cwd=repo_path, check=False)
    return bool(result.stdout.strip())


def list_commits(repo_path: str, branch: str, n: int = 10) -> list[str]:
    """Return the last *n* short SHAs on *branch*."""
    result = run_git(
        ["log", branch, "--oneline", f"-{n}"],
        cwd=repo_path,
        check=False,
    )
    if result.returncode != 0:
        return []
    return [line.split()[0] for line in result.stdout.splitlines() if line]
