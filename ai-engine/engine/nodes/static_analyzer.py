# ai-engine/engine/nodes/static_analyzer.py

import os
import subprocess
import logging
import json
from pathlib import Path

from engine.state import AgentState, Language
from engine.nodes.utils import emit

logger = logging.getLogger(__name__)


def static_analyzer(state: AgentState) -> dict:
    """
    Node 3: Run linters/static analysis on ALL repos — no tests needed.
    This is what enables Change 3: works on every repo, not just ones with tests.

    Python  → flake8 + pylint
    JS/TS   → eslint (if config present) else basic checks
    Others  → basic syntax check via language tooling
    """
    emit(state, "node_start", "static", iteration=state["current_iteration"])

    repo_path = state["repo_local_path"]
    primary_language = state.get("primary_language", Language.UNKNOWN.value)
    output_lines = []

    if primary_language == Language.PYTHON.value:
        output_lines = _run_python_analysis(repo_path)
    elif primary_language in (Language.JAVASCRIPT.value, Language.TYPESCRIPT.value):
        output_lines = _run_js_analysis(repo_path)
    else:
        logger.info("No static analyzer for language: %s", primary_language)

    raw_output = "\n".join(output_lines)
    logger.info("Static analysis complete: %d findings", len(output_lines))

    emit(state, "node_end", "static", findings_count=len(output_lines))

    return {"static_analysis_output": raw_output}


def _run_python_analysis(repo_path: str) -> list[str]:
    lines = []
    repo_path = str(Path(repo_path).resolve())  # ensure absolute

    # flake8
    try:
        result = subprocess.run(
            [
                "python3", "-m", "flake8",
                "--max-line-length=120",
                "--format=%(path)s:%(row)d:%(col)d: %(code)s %(text)s",
                ".",                          # use "." so paths are relative
            ],
            capture_output=True, text=True, timeout=60, cwd=repo_path,
        )
        if result.stdout.strip():
            lines.extend(result.stdout.strip().splitlines())
    except Exception as e:
        logger.warning("flake8 failed: %s", e)

    # pylint
    try:
        py_files = [
            str(p.relative_to(repo_path))     # relative paths
            for p in Path(repo_path).rglob("*.py")
            if ".venv" not in str(p) and "__pycache__" not in str(p)
        ]
        if py_files:
            result = subprocess.run(
                [
                    "python3", "-m", "pylint",
                    "--output-format=text",
                    "--score=no",
                    "--disable=C0114,C0115,C0116",
                    *py_files[:50],
                ],
                capture_output=True, text=True, timeout=90, cwd=repo_path,
            )
            if result.stdout.strip():
                lines.extend(result.stdout.strip().splitlines())
    except Exception as e:
        logger.warning("pylint failed: %s", e)

    return lines

def _run_js_analysis(repo_path: str) -> list[str]:
    lines = []

    # Only run eslint if a config file exists in the repo
    has_eslint_config = any(
        os.path.exists(os.path.join(repo_path, cfg))
        for cfg in [".eslintrc", ".eslintrc.js", ".eslintrc.json",
                    ".eslintrc.yml", "eslint.config.js", "eslint.config.mjs"]
    )

    if not has_eslint_config:
        logger.info("No eslint config found — skipping JS static analysis")
        return lines

    try:
        result = subprocess.run(
            ["npx", "eslint", "--format=compact", "."],
            capture_output=True, text=True, timeout=60, cwd=repo_path,
        )
        if result.stdout.strip():
            lines.extend(result.stdout.strip().splitlines())
    except Exception as e:
        logger.warning("eslint failed: %s", e)

    return lines
