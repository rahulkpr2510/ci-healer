# ai-engine/engine/nodes/git_commit.py

import subprocess
import logging

from engine.state import AgentState, Fix, FixStatus
from engine.config import engine_settings
from engine.nodes.utils import emit

logger = logging.getLogger(__name__)


def _git(repo_path: str, *args) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", repo_path, *args],
        capture_output=True, text=True,
    )


def git_commit(state: AgentState) -> dict:
    """
    Node 8: Create the fix branch and commit each fix.
    Skipped entirely in read_only mode.
    """
    emit(state, "node_start", "commit", iteration=state["current_iteration"])

    if state.get("read_only"):
        logger.info("Read-only mode — skipping git commit")
        emit(state, "node_end", "commit", read_only=True)
        return {}

    repo_path = state["repo_local_path"]
    branch_name = state["branch_name"]
    github_token = state.get("github_token")
    all_fixed = [f for f in state.get("fixes", []) if f.status == FixStatus.FIXED]

    # Deduplicate: when batch-fixing a file, multiple Fix objects share the same file.
    # Keep only the first Fix per file — the file was already written once by patch_applier.
    seen_files: set[str] = set()
    fixes: list[Fix] = []
    for f in all_fixed:
        if f.file not in seen_files:
            seen_files.add(f.file)
            fixes.append(f)

    if not fixes:
        logger.info("No successful fixes to commit")
        emit(state, "node_end", "commit", fixes_count=0)
        return {"current_iteration": state["current_iteration"] + 1}

    # ── Configure git identity ────────────────────────────
    _git(repo_path, "config", "user.name", engine_settings.GIT_AUTHOR_NAME)
    _git(repo_path, "config", "user.email", engine_settings.GIT_AUTHOR_EMAIL)

    # ── Create and checkout fix branch ───────────────────
    result = _git(repo_path, "checkout", "-b", branch_name)
    if result.returncode != 0:
        # Branch may already exist — try checking it out
        _git(repo_path, "checkout", branch_name)

    commits: list[str] = []

    for fix in fixes:
        # Stage the specific file
        stage = _git(repo_path, "add", fix.file)
        if stage.returncode != 0:
            logger.warning("Could not stage %s", fix.file)
            continue

        # Commit with mandatory [AI-AGENT] prefix
        commit = _git(repo_path, "commit", "-m", fix.commit_message)
        if commit.returncode == 0:
            # Get the SHA of this commit
            sha_result = _git(repo_path, "rev-parse", "HEAD")
            sha = sha_result.stdout.strip()[:8]
            commits.append(sha)
            logger.info("Committed: %s → %s", fix.commit_message[:60], sha)

            emit(state, "node_end", "commit",
                 latest_commit=sha,
                 fixes_count=len(commits))
        else:
            logger.warning("Commit failed for %s: %s", fix.file, commit.stderr)

    # ── Push branch ───────────────────────────────────────
    push_attempted = False
    if commits and github_token:
        push_attempted = True
        push = _git(repo_path, "push", "origin", branch_name)
        if push.returncode != 0:
            logger.error("Push failed: %s", push.stderr)
        else:
            logger.info("Pushed branch: %s (%d commits)", branch_name, len(commits))

    # Always increment regardless of whether commits were made —
    # prevents infinite loop when all commits fail or nothing changed.
    return {
        "commits": commits,
        "current_iteration": state["current_iteration"] + 1,
    }
