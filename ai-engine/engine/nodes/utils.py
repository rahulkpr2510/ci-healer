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
    ".mypy_cache", ".tox", "eggs", "*.egg-info", "target",    # Java/Rust build
    ".gradle", ".mvn", "vendor",                               # Go/PHP vendor
    ".bundle", "tmp",                                          # Ruby
    "Pods",                                                    # Swift CocoaPods
    ".dart_tool", ".pub-cache",                               # Dart
    "_build", "deps",                                         # Elixir
    ".stack-work",                                            # Haskell
    "obj", "bin",                                             # .NET
    "cmake-build-debug", "cmake-build-release",              # CMake
}

IGNORE_EXTENSIONS = {
    # Compiled / binary
    ".pyc", ".pyo", ".class", ".jar", ".war", ".ear",
    ".o", ".a", ".so", ".dll", ".exe", ".lib",
    ".out", ".bin",
    # Lock / generated
    ".lock", ".sum",
    # Assets
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico",
    ".woff", ".woff2", ".ttf", ".eot",
    # Documents / archives
    ".pdf", ".zip", ".tar", ".gz", ".bz2", ".xz",
    # IDE
    ".iml", ".ipr", ".iws",
}

# ── Test-file pattern registry ────────────────────────────
TEST_FILENAME_PATTERNS: list[str] = [
    # Python
    r"test_.*\.py$",
    r".*_test\.py$",
    r"tests?\.py$",
    # JavaScript / TypeScript
    r".*\.test\.(js|ts|jsx|tsx|mjs|cjs)$",
    r".*\.spec\.(js|ts|jsx|tsx|mjs|cjs)$",
    r"__tests__/.*\.(js|ts|jsx|tsx)$",
    # Java
    r".*Test\.java$",
    r".*Tests\.java$",
    r".*Spec\.java$",
    # Go
    r".*_test\.go$",
    # Ruby
    r".*_spec\.rb$",
    r".*_test\.rb$",
    r"test_.*\.rb$",
    # Rust
    # Rust keeps tests inside source files, but integration tests live in tests/
    r"tests/.*\.rs$",
    # C#
    r".*Test\.cs$",
    r".*Tests\.cs$",
    r".*Spec\.cs$",
    # C / C++
    r"test_.*\.(c|cpp|cc)$",
    r".*_test\.(c|cpp|cc)$",
    r".*Test\.(c|cpp|cc)$",
    # PHP
    r".*Test\.php$",
    r".*Spec\.php$",
    # Swift
    r".*Tests\.swift$",
    r".*Spec\.swift$",
    # Kotlin
    r".*Test\.kt$",
    r".*Spec\.kt$",
    # Shell
    r"test_.*\.sh$",
    r".*_test\.sh$",
    # Dart
    r".*_test\.dart$",
    # Elixir
    r".*_test\.exs$",
    # Haskell
    r".*Spec\.hs$",
    r".*Test\.hs$",
    # Generic
    r".*[Tt]est.*\.[a-z]+$",
]

# Directories that typically contain only tests
TEST_DIRS: set[str] = {
    "test", "tests", "spec", "specs", "__tests__",
    "test_suite", "integration_tests", "e2e",
}


def is_test_file(path: str) -> bool:
    filename  = os.path.basename(path)
    parts     = Path(path).parts
    # Check directory name
    if any(part.lower() in TEST_DIRS for part in parts[:-1]):
        # Extra check: if the dir is 'tests' then any source file inside is a test
        ext = Path(path).suffix.lower()
        # Only treat as test if it has a source extension (not README, config, etc.)
        if ext in {".py", ".js", ".ts", ".rb", ".go", ".java", ".rs", ".cs",
                   ".cpp", ".c", ".php", ".swift", ".kt", ".dart", ".ex", ".exs"}:
            return True
    return any(re.search(pattern, filename) for pattern in TEST_FILENAME_PATTERNS)


def is_source_file(path: str) -> bool:
    ext = Path(path).suffix.lower()
    return ext not in IGNORE_EXTENSIONS and not is_test_file(path)


def walk_repo(repo_path: str) -> tuple[list[str], list[str]]:
    """
    Returns (source_files, test_files) as relative paths.
    Skips ignored dirs and binary/lock extensions.
    """
    source_files: list[str] = []
    test_files:   list[str] = []

    for root, dirs, files in os.walk(repo_path):
        rel_root = os.path.relpath(root, repo_path)

        # Prune ignored directories in-place
        dirs[:] = [
            d for d in dirs
            if d not in IGNORE_DIRS
            and not d.startswith(".")
            and not d.endswith(".egg-info")
        ]

        for filename in files:
            abs_path = os.path.join(root, filename)
            rel_path = os.path.relpath(abs_path, repo_path)

            if Path(abs_path).suffix.lower() in IGNORE_EXTENSIONS:
                continue

            if is_test_file(rel_path):
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
    Also handles SSH URLs: git@github.com:owner/repo.git
    """
    # HTTPS
    match = re.match(r"https://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$", repo_url)
    if match:
        return match.group(1), match.group(2)
    # SSH
    match = re.match(r"git@github\.com:([^/]+)/([^/]+?)(?:\.git)?$", repo_url)
    if match:
        return match.group(1), match.group(2)
    raise ValueError(
        f"Cannot parse GitHub URL: {repo_url!r}. "
        "Expected format: https://github.com/owner/repo or git@github.com:owner/repo.git"
    )


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

