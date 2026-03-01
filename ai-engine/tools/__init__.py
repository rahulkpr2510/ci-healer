# ai-engine/tools/__init__.py
"""
AI Engine tool modules.

These are utility helpers that wrap subprocess calls and HTTP requests
used by the LangGraph pipeline nodes.
"""

from tools.git_tools import (
    clone_repo,
    get_default_branch,
    create_branch,
    stage_file,
    commit,
    push_branch,
    get_diff,
    has_uncommitted_changes,
)

from tools.github_tools import (
    create_pull_request,
    get_latest_workflow_run,
    wait_for_ci,
    get_repo_info,
    list_user_repos,
)

from tools.analysis_tools import (
    run_flake8,
    run_pylint,
    run_eslint,
    run_pytest,
    run_npm_test,
    detect_package_manager,
)

__all__ = [
    # git
    "clone_repo",
    "get_default_branch",
    "create_branch",
    "stage_file",
    "commit",
    "push_branch",
    "get_diff",
    "has_uncommitted_changes",
    # github
    "create_pull_request",
    "get_latest_workflow_run",
    "wait_for_ci",
    "get_repo_info",
    "list_user_repos",
    # analysis
    "run_flake8",
    "run_pylint",
    "run_eslint",
    "run_pytest",
    "run_npm_test",
    "detect_package_manager",
]
