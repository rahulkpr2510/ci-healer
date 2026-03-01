# ai-engine/tools/analysis_tools.py
"""
Static analysis and test runner helpers.

Thin wrappers around flake8, pylint, eslint, pytest, and npm test
so the agent nodes don't need to embed subprocess logic directly.
All functions return plain strings / booleans to keep nodes clean.
"""

from __future__ import annotations

import logging
import os
import subprocess
from typing import Optional

logger = logging.getLogger(__name__)


# ── Timeout defaults ──────────────────────────────────────────────────────────
PYTHON_TEST_TIMEOUT = 120   # seconds
JS_TEST_TIMEOUT = 180


# ── Python static analysis ────────────────────────────────────────────────────

def run_flake8(repo_path: str, max_line_length: int = 120) -> str:
    """
    Run flake8 on the repo.
    Returns the combined stdout+stderr output as a string (empty if no issues).
    """
    try:
        result = subprocess.run(
            [
                "flake8", ".",
                f"--max-line-length={max_line_length}",
                "--format=%(path)s:%(row)d:%(col)d: %(code)s %(text)s",
                "--exclude=.git,.venv,__pycache__,node_modules,.next,dist,build,migrations",
            ],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=60,
        )
        return (result.stdout + result.stderr).strip()
    except FileNotFoundError:
        logger.debug("flake8 not installed")
        return ""
    except subprocess.TimeoutExpired:
        logger.warning("flake8 timed out")
        return ""
    except Exception as e:
        logger.error("flake8 error: %s", e)
        return ""


def run_pylint(repo_path: str, source_files: list[str]) -> str:
    """
    Run pylint on *source_files* (relative paths).
    Only passes files that actually exist.
    Returns the combined stdout+stderr output.
    """
    if not source_files:
        return ""

    existing = [f for f in source_files if os.path.isfile(os.path.join(repo_path, f))]
    if not existing:
        return ""

    try:
        result = subprocess.run(
            [
                "pylint",
                "--output-format=text",
                "--score=no",
                "--disable=C0114,C0115,C0116,C0301,R0903,R0801",  # suppress docstrings / line-len
            ] + existing,
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=90,
        )
        return (result.stdout + result.stderr).strip()
    except FileNotFoundError:
        logger.debug("pylint not installed")
        return ""
    except subprocess.TimeoutExpired:
        logger.warning("pylint timed out")
        return ""
    except Exception as e:
        logger.error("pylint error: %s", e)
        return ""


# ── JavaScript / TypeScript static analysis ───────────────────────────────────

def run_eslint(repo_path: str) -> str:
    """
    Run eslint on the repo (only if an eslint config file is present).
    Returns the compact-format output string.
    """
    config_files = [
        ".eslintrc", ".eslintrc.js", ".eslintrc.json", ".eslintrc.cjs",
        "eslint.config.js", "eslint.config.mjs", "eslint.config.cjs",
    ]
    has_config = any(
        os.path.isfile(os.path.join(repo_path, cf)) for cf in config_files
    )
    if not has_config:
        logger.debug("No eslint config found — skipping")
        return ""

    try:
        result = subprocess.run(
            ["npx", "--yes", "eslint", ".", "--format=compact",
             "--ext", ".js,.jsx,.ts,.tsx"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=90,
        )
        return (result.stdout + result.stderr).strip()
    except FileNotFoundError:
        logger.debug("npx not available — skipping eslint")
        return ""
    except subprocess.TimeoutExpired:
        logger.warning("eslint timed out")
        return ""
    except Exception as e:
        logger.error("eslint error: %s", e)
        return ""


# ── Python test runner ────────────────────────────────────────────────────────

def run_pytest(repo_path: str) -> tuple[str, bool]:
    """
    Run pytest with short tracebacks.
    Returns (output_string, passed: bool).
    """
    try:
        result = subprocess.run(
            ["python", "-m", "pytest", "--tb=short", "-q", "--no-header"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=PYTHON_TEST_TIMEOUT,
        )
        output = (result.stdout + result.stderr).strip()
        passed = result.returncode == 0
        return output, passed
    except FileNotFoundError:
        logger.warning("pytest not found — trying pytest directly")
        try:
            result = subprocess.run(
                ["pytest", "--tb=short", "-q", "--no-header"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=PYTHON_TEST_TIMEOUT,
            )
            output = (result.stdout + result.stderr).strip()
            return output, result.returncode == 0
        except Exception as e:
            return f"pytest not available: {e}", False
    except subprocess.TimeoutExpired:
        return f"pytest timed out after {PYTHON_TEST_TIMEOUT}s", False
    except Exception as e:
        return f"pytest error: {e}", False


# ── JavaScript / TypeScript test runner ──────────────────────────────────────

def run_npm_test(repo_path: str) -> tuple[str, bool]:
    """
    Run `npm test -- --watchAll=false` and return (output, passed).
    Assumes npm is available and package.json has a 'test' script.
    """
    try:
        result = subprocess.run(
            ["npm", "test", "--", "--watchAll=false", "--ci"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=JS_TEST_TIMEOUT,
            env={**os.environ, "CI": "true"},
        )
        output = (result.stdout + result.stderr).strip()
        return output, result.returncode == 0
    except FileNotFoundError:
        return "npm not available", False
    except subprocess.TimeoutExpired:
        return f"npm test timed out after {JS_TEST_TIMEOUT}s", False
    except Exception as e:
        return f"npm test error: {e}", False


# ── Generic helpers ───────────────────────────────────────────────────────────

def has_python_tests(repo_path: str, test_files: list[str]) -> bool:
    """Return True if there are any Python test files."""
    return any(f.endswith(".py") for f in test_files)


def has_js_tests(repo_path: str, test_files: list[str]) -> bool:
    """Return True if there are any JS/TS test files."""
    js_exts = (".test.js", ".spec.js", ".test.ts", ".spec.ts", ".test.jsx", ".spec.jsx")
    return any(f.endswith(js_exts) for f in test_files)


def detect_package_manager(repo_path: str) -> Optional[str]:
    """Detect the JS package manager (npm / yarn / pnpm)."""
    if os.path.isfile(os.path.join(repo_path, "pnpm-lock.yaml")):
        return "pnpm"
    if os.path.isfile(os.path.join(repo_path, "yarn.lock")):
        return "yarn"
    if os.path.isfile(os.path.join(repo_path, "package-lock.json")):
        return "npm"
    if os.path.isfile(os.path.join(repo_path, "package.json")):
        return "npm"
    return None
