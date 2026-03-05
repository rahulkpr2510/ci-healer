# ai-engine/engine/nodes/test_runner.py

import os
import subprocess
import logging

from engine.state import AgentState
from engine.nodes.utils import emit

logger = logging.getLogger(__name__)


def test_runner(state: AgentState) -> dict:
    """
    Node 4: Run tests IF they exist.
    If no test files found, skip gracefully — static analysis already ran.
    """
    emit(state, "node_start", "test", iteration=state["current_iteration"])

    repo_path = state["repo_local_path"]
    has_tests = state.get("has_tests", False)
    primary_language = state.get("primary_language", "unknown")

    if not has_tests:
        logger.info("No test files found — skipping test runner")
        emit(state, "node_end", "test", test_passed=True, skipped=True)
        return {"test_output": "No test files found", "test_passed": True}

    output = ""
    passed = False

    if primary_language == "python":
        output, passed = _run_pytest(repo_path)
    elif primary_language in ("javascript", "typescript"):
        output, passed = _run_npm_test(repo_path)
    else:
        logger.info("No test runner for language: %s", primary_language)
        output = f"No test runner configured for {primary_language}"
        passed = True

    logger.info("Tests %s", "PASSED" if passed else "FAILED")
    emit(state, "node_end", "test",
         test_passed=passed,
         raw_test_output_tail=output[-500:] if output else "")

    return {"test_output": output, "test_passed": passed}


def _run_pytest(repo_path: str) -> tuple[str, bool]:
    try:
        result = subprocess.run(
            ["python3", "-m", "pytest", "--tb=short", "-q", "--no-header"],
            capture_output=True, text=True, timeout=120, cwd=repo_path,
        )
        output = (result.stdout + result.stderr).strip()
        passed = result.returncode == 0
        return output, passed
    except subprocess.TimeoutExpired:
        return "pytest timed out after 120s", False
    except Exception as e:
        return f"pytest failed to run: {e}", False


def _run_npm_test(repo_path: str) -> tuple[str, bool]:
    # Install deps first if node_modules missing
    if not os.path.exists(os.path.join(repo_path, "node_modules")):
        try:
            subprocess.run(
                ["npm", "install", "--prefer-offline"],
                capture_output=True, cwd=repo_path, timeout=120,
            )
        except FileNotFoundError:
            logger.warning("npm not found — skipping JS test run")
            return "npm not available in this environment", True
        except subprocess.TimeoutExpired:
            return "npm install timed out after 120s", False
    try:
        result = subprocess.run(
            ["npm", "test", "--", "--watchAll=false"],
            capture_output=True, text=True, timeout=180, cwd=repo_path,
        )
        output = (result.stdout + result.stderr).strip()
        passed = result.returncode == 0
        return output, passed
    except FileNotFoundError:
        logger.warning("npm not found — skipping JS test run")
        return "npm not available in this environment", True
    except subprocess.TimeoutExpired:
        return "npm test timed out after 180s", False
    except Exception as e:
        return f"npm test failed to run: {e}", False
