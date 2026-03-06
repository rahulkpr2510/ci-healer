# ai-engine/engine/nodes/repo_analyzer.py

import os
import logging
import subprocess
from datetime import datetime, timezone

from engine.state import AgentState
from engine.config import engine_settings, format_branch_name
from engine.nodes.utils import extract_owner_repo, walk_repo, emit

logger = logging.getLogger(__name__)


def repo_analyzer(state: AgentState) -> dict:
    """
    Node 1: Clone the repo and build file inventory.
    Returns partial state dict — LangGraph merges it.
    """
    emit(state, "node_start", "repo", iteration=state["current_iteration"])

    repo_url = state["repo_url"]
    branch_prefix = state.get("branch_prefix", "")
    github_token = state.get("github_token")

    # ── Build authenticated clone URL ─────────────────────
    if github_token:
        # Inject token into URL for private repo access
        authed_url = repo_url.replace(
            "https://", f"https://{github_token}@"
        )
    else:
        authed_url = repo_url

    # ── Determine clone path ──────────────────────────────
    owner, repo_name = extract_owner_repo(repo_url)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    clone_dir = os.path.join(
        engine_settings.workspace_path,
        f"{owner}_{repo_name}_{timestamp}"
    )
    os.makedirs(engine_settings.workspace_path, exist_ok=True)

    # ── Clone ─────────────────────────────────────────────
    logger.info("Cloning %s → %s", repo_url, clone_dir)
    result = subprocess.run(
        ["git", "clone", "--depth=1", authed_url, clone_dir],
        capture_output=True,
        text=True,
        timeout=120,
    )

    if result.returncode != 0:
        error = result.stderr.strip()
        logger.error("Clone failed: %s", error)
        emit(state, "node_end", "repo", error=error)
        raise RuntimeError(f"Failed to clone repository: {error}")

    # ── Detect default branch ─────────────────────────────
    branch_result = subprocess.run(
        ["git", "-C", clone_dir, "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True, text=True
    )
    default_branch = branch_result.stdout.strip() or "main"

    # ── Walk file tree ────────────────────────────────────
    source_files, test_files = walk_repo(clone_dir)
    logger.info(
        "Repo scanned: %d source files, %d test files",
        len(source_files), len(test_files)
    )

    # ── Build fix branch name ─────────────────────────────
    # Use a short timestamp-based counter for uniqueness without API calls
    run_seq = int(datetime.now(timezone.utc).strftime("%H%M%S")) % 10000
    branch_name = format_branch_name(branch_prefix, run_seq)

    emit(state, "node_end", "repo",
         source_count=len(source_files),
         test_count=len(test_files))

    return {
        "repo_local_path": clone_dir,
        "repo_owner": owner,
        "repo_name": repo_name,
        "branch_name": branch_name,
        "default_branch": default_branch,
        "source_files": source_files,
        "test_files": test_files,
        "has_tests": len(test_files) > 0,
    }
