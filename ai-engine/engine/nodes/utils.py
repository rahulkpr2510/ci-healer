# ai-engine/engine/nodes/utils.py

import os
import re
import shutil
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Files/dirs to always skip when walking repos
IGNORE_DIRS = {
    ".git", "node_modules", ".venv", "venv", "__pycache__",
    ".next", "dist", "build", ".cache", "coverage", ".pytest_cache",
    ".mypy_cache", ".tox", "eggs", "*.egg-info",
}

IGNORE_EXTENSIONS = {
    ".pyc", ".pyo", ".lock", ".sum", ".png", ".jpg", ".jpeg",
    ".gif", ".svg", ".ico", ".woff", ".woff2", ".ttf", ".eot",
    ".pdf", ".zip", ".tar", ".gz", ".bin", ".exe",
}

TEST_FILENAME_PATTERNS = [
    r"test_.*\.py$", r".*_test\.py$",           # Python
    r".*\.test\.(js|ts|jsx|tsx)$",               # JS/TS
    r".*\.spec\.(js|ts|jsx|tsx)$",               # JS/TS
    r".*Test\.java$", r".*_test\.go$",           # Java / Go
]


def is_test_file(path: str) -> bool:
    filename = os.path.basename(path)
    return any(re.search(pattern, filename) for pattern in TEST_FILENAME_PATTERNS)


def is_source_file(path: str) -> bool:
    ext = Path(path).suffix.lower()
    return ext not in IGNORE_EXTENSIONS and not is_test_file(path)


def walk_repo(repo_path: str) -> tuple[list[str], list[str]]:
    """
    Returns (source_files, test_files) as relative paths.
    Skips ignored dirs and binary extensions.
    """
    source_files = []
    test_files = []

    for root, dirs, files in os.walk(repo_path):
        # Prune ignored directories in-place
        dirs[:] = [
            d for d in dirs
            if d not in IGNORE_DIRS and not d.startswith(".")
        ]

        for filename in files:
            abs_path = os.path.join(root, filename)
            rel_path = os.path.relpath(abs_path, repo_path)

            if Path(abs_path).suffix.lower() in IGNORE_EXTENSIONS:
                continue

            if is_test_file(filename):
                test_files.append(rel_path)
            else:
                source_files.append(rel_path)

    return sorted(source_files), sorted(test_files)


def clean_workspace(repo_path: str) -> None:
    """Removes the cloned repo from workspace after run."""
    if repo_path and os.path.exists(repo_path):
        shutil.rmtree(repo_path, ignore_errors=True)
        logger.info("Cleaned workspace: %s", repo_path)


def extract_owner_repo(repo_url: str) -> tuple[str, str]:
    """
    'https://github.com/owner/repo' → ('owner', 'repo')
    """
    match = re.match(r"https://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$", repo_url)
    if not match:
        raise ValueError(f"Cannot parse GitHub URL: {repo_url}")
    return match.group(1), match.group(2)


def emit(state: dict, event: str, node: str, **kwargs) -> None:
    """
    Fires observer callback if one is attached to state.
    Backend uses this for SSE streaming.
    """
    observer = state.get("observer")
    if observer and callable(observer):
        try:
            observer({"event": event, "node": node, **kwargs})
        except Exception as e:
            logger.warning("Observer emit failed: %s", e)
