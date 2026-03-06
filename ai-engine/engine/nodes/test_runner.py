# ai-engine/engine/nodes/test_runner.py

import os
import shutil
import subprocess
import logging

from engine.state import AgentState, Language
from engine.nodes.utils import emit

logger = logging.getLogger(__name__)

# Per-language timeouts (seconds)
_TIMEOUT = {
    Language.PYTHON.value:     120,
    Language.JAVASCRIPT.value: 180,
    Language.TYPESCRIPT.value: 180,
    Language.GO.value:         120,
    Language.JAVA.value:       180,
    Language.RUBY.value:       120,
    Language.RUST.value:       180,
    Language.CSHARP.value:     180,
}


def test_runner(state: AgentState) -> dict:
    """
    Node 4: Run tests for ALL supported languages.
    If no test files are found, skips gracefully — static analysis already ran.

    Language → test command
    ──────────────────────────────────────────
    Python     → pytest (falls back to unittest)
    JS/TS      → npm test / yarn test / jest
    Go         → go test ./...
    Java       → mvn test / gradle test
    Ruby       → rspec / minitest (ruby -Itest)
    Rust       → cargo test
    C#         → dotnet test
    Others     → skipped (static analysis only)
    ──────────────────────────────────────────
    On each iteration the test output and pass/fail status are refreshed
    so the agent can confirm whether a fix resolved the problem.
    """
    emit(state, "node_start", "test", iteration=state["current_iteration"])

    repo_path        = state["repo_local_path"]
    has_tests        = state.get("has_tests", False)
    primary_language = state.get("primary_language", "unknown")
    agent_errors: list[str] = []

    if not has_tests:
        logger.info("No test files found — skipping test runner")
        emit(state, "node_end", "test", test_passed=True, skipped=True)
        return {
            "test_output": "No test files found in this repository.",
            "test_passed": True,
            # Reset per-iteration state cleanly
            "static_analysis_output": state.get("static_analysis_output", ""),
        }

    output = ""
    passed = False

    runners = {
        Language.PYTHON.value:     _run_pytest,
        Language.JAVASCRIPT.value: _run_npm_test,
        Language.TYPESCRIPT.value: _run_npm_test,
        Language.GO.value:         _run_go_test,
        Language.JAVA.value:       _run_java_test,
        Language.RUBY.value:       _run_ruby_test,
        Language.RUST.value:       _run_cargo_test,
        Language.CSHARP.value:     _run_dotnet_test,
    }

    runner = runners.get(primary_language)
    if runner:
        output, passed, agent_errors = runner(repo_path)
    else:
        logger.info("No test runner configured for language: %s", primary_language)
        output = f"No test runner configured for {primary_language}."
        passed = True   # don't fail the run if tooling isn't available

    logger.info(
        "Tests %s for %s (iteration %d)",
        "PASSED" if passed else "FAILED",
        primary_language,
        state.get("current_iteration", 1),
    )

    emit(
        state, "node_end", "test",
        test_passed=passed,
        raw_test_output_tail=output[-500:] if output else "",
        tool_errors=agent_errors,
    )

    result: dict = {"test_output": output, "test_passed": passed}
    if agent_errors:
        result["agent_errors"] = agent_errors
    return result


# ─────────────────────────────────────────────────────────────────
# Python
# ─────────────────────────────────────────────────────────────────

def _run_pytest(repo_path: str) -> tuple[str, bool, list[str]]:
    errors: list[str] = []
    try:
        result = subprocess.run(
            ["python3", "-m", "pytest", "--tb=short", "-q", "--no-header"],
            capture_output=True, text=True,
            timeout=_TIMEOUT[Language.PYTHON.value],
            cwd=repo_path,
        )
        output = (result.stdout + result.stderr).strip()
        return output, result.returncode == 0, errors
    except FileNotFoundError:
        # Fallback to unittest discovery
        try:
            result = subprocess.run(
                ["python3", "-m", "unittest", "discover", "-v"],
                capture_output=True, text=True,
                timeout=_TIMEOUT[Language.PYTHON.value],
                cwd=repo_path,
            )
            output = (result.stdout + result.stderr).strip()
            return output, result.returncode == 0, errors
        except FileNotFoundError:
            msg = "python3 not found in PATH — cannot run Python tests"
            return msg, False, [msg]
        except subprocess.TimeoutExpired:
            msg = f"unittest discover timed out after {_TIMEOUT[Language.PYTHON.value]}s"
            return msg, False, [msg]
        except Exception as exc:
            msg = f"unittest discover failed: {exc}"
            return msg, False, [msg]
    except subprocess.TimeoutExpired:
        msg = f"pytest timed out after {_TIMEOUT[Language.PYTHON.value]}s"
        return msg, False, [msg]
    except Exception as exc:
        msg = f"pytest failed to start: {exc}"
        return msg, False, [msg]


# ─────────────────────────────────────────────────────────────────
# JavaScript / TypeScript
# ─────────────────────────────────────────────────────────────────

def _run_npm_test(repo_path: str) -> tuple[str, bool, list[str]]:
    errors: list[str] = []
    timeout = _TIMEOUT[Language.JAVASCRIPT.value]

    if not os.path.exists(os.path.join(repo_path, "package.json")):
        msg = "No package.json found — cannot run JS/TS tests"
        return msg, True, []   # not a hard failure

    # Ensure node_modules — prefer bun (fast), fallback to npm
    if not os.path.exists(os.path.join(repo_path, "node_modules")):
        if shutil.which("bun"):
            install_cmd = ["bun", "install"]
        else:
            install_cmd = ["npm", "install", "--prefer-offline", "--no-audit", "--no-fund"]
        try:
            subprocess.run(
                install_cmd,
                capture_output=True, cwd=repo_path, timeout=180,
            )
        except FileNotFoundError:
            msg = f"{install_cmd[0]} not found in PATH — cannot run JS/TS tests"
            return msg, True, [msg]
        except subprocess.TimeoutExpired:
            msg = f"{install_cmd[0]} install timed out after 180s — tests skipped"
            return msg, False, [msg]

    # Detect test script / framework
    import json as _json
    test_cmd: list[str] | None = None
    has_test_framework = False
    try:
        with open(os.path.join(repo_path, "package.json"), encoding="utf-8") as fh:
            pkg = _json.load(fh)
        scripts = pkg.get("scripts", {})
        all_deps = {
            **pkg.get("dependencies", {}),
            **pkg.get("devDependencies", {}),
        }

        # Determine whether a test framework is actually installed
        _framework_keys = {"jest", "vitest", "mocha", "jasmine", "@jest/core", "ava", "tap"}
        _config_files = [
            "jest.config.js", "jest.config.ts", "jest.config.mjs",
            "vitest.config.ts", "vitest.config.js", "vitest.config.mjs",
        ]
        has_test_framework = bool(_framework_keys & set(all_deps)) or any(
            os.path.exists(os.path.join(repo_path, cfg)) for cfg in _config_files
        )

        if "test" in scripts:
            test_cmd = ["npm", "test", "--", "--watchAll=false", "--passWithNoTests"]
        elif "jest" in scripts or os.path.exists(os.path.join(repo_path, "jest.config.js")):
            test_cmd = ["npx", "jest", "--watchAll=false", "--passWithNoTests"]
        elif "vitest" in scripts:
            test_cmd = ["npx", "vitest", "run", "--passWithNoTests"]
        elif "mocha" in scripts:
            test_cmd = ["npx", "mocha", "--exit"]
    except Exception:
        pass

    if not test_cmd:
        if not has_test_framework:
            # No test framework installed — skip gracefully instead of timing out on npx download
            msg = "No test framework found in dependencies — skipping JS/TS tests"
            logger.info(msg)
            return msg, True, []
        # Framework present in deps but no known script — try jest
        test_cmd = ["npx", "jest", "--watchAll=false", "--passWithNoTests"]

    try:
        result = subprocess.run(
            test_cmd,
            capture_output=True, text=True, timeout=timeout, cwd=repo_path,
        )
        output = (result.stdout + result.stderr).strip()
        return output, result.returncode == 0, errors
    except FileNotFoundError:
        msg = "npm/npx not found in PATH — cannot run JS/TS tests"
        return msg, True, [msg]
    except subprocess.TimeoutExpired:
        msg = f"JS/TS test runner timed out after {timeout}s"
        return msg, False, [msg]
    except Exception as exc:
        msg = f"JS/TS test runner failed: {exc}"
        return msg, False, [msg]


# ─────────────────────────────────────────────────────────────────
# Go
# ─────────────────────────────────────────────────────────────────

def _run_go_test(repo_path: str) -> tuple[str, bool, list[str]]:
    errors: list[str] = []
    try:
        result = subprocess.run(
            ["go", "test", "-v", "./..."],
            capture_output=True, text=True,
            timeout=_TIMEOUT[Language.GO.value],
            cwd=repo_path,
        )
        output = (result.stdout + result.stderr).strip()
        return output, result.returncode == 0, errors
    except FileNotFoundError:
        msg = "go not found in PATH — cannot run Go tests"
        return msg, True, [msg]
    except subprocess.TimeoutExpired:
        msg = f"go test timed out after {_TIMEOUT[Language.GO.value]}s"
        return msg, False, [msg]
    except Exception as exc:
        msg = f"go test failed: {exc}"
        return msg, False, [msg]


# ─────────────────────────────────────────────────────────────────
# Java
# ─────────────────────────────────────────────────────────────────

def _run_java_test(repo_path: str) -> tuple[str, bool, list[str]]:
    errors: list[str] = []
    timeout = _TIMEOUT[Language.JAVA.value]

    # Maven
    if os.path.exists(os.path.join(repo_path, "pom.xml")):
        cmd = ["mvn", "test", "-q", "-B"]
        tool = "mvn"
    # Gradle
    elif os.path.exists(os.path.join(repo_path, "build.gradle")) or \
         os.path.exists(os.path.join(repo_path, "build.gradle.kts")):
        cmd = ["./gradlew", "test", "--info"] if os.path.exists(
            os.path.join(repo_path, "gradlew")
        ) else ["gradle", "test"]
        tool = "gradle"
    else:
        return "No pom.xml or build.gradle found — cannot run Java tests", True, []

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, cwd=repo_path,
        )
        output = (result.stdout + result.stderr).strip()
        return output, result.returncode == 0, errors
    except FileNotFoundError:
        msg = f"{tool} not found in PATH — cannot run Java tests"
        return msg, True, [msg]
    except subprocess.TimeoutExpired:
        msg = f"Java test runner timed out after {timeout}s"
        return msg, False, [msg]
    except Exception as exc:
        msg = f"Java test runner failed: {exc}"
        return msg, False, [msg]


# ─────────────────────────────────────────────────────────────────
# Ruby
# ─────────────────────────────────────────────────────────────────

def _run_ruby_test(repo_path: str) -> tuple[str, bool, list[str]]:
    errors: list[str] = []
    timeout = _TIMEOUT[Language.RUBY.value]

    # RSpec
    if os.path.exists(os.path.join(repo_path, "spec")) or \
       os.path.exists(os.path.join(repo_path, ".rspec")):
        cmd = ["bundle", "exec", "rspec"] if os.path.exists(
            os.path.join(repo_path, "Gemfile")
        ) else ["rspec"]
    # Minitest via rake
    elif os.path.exists(os.path.join(repo_path, "Rakefile")):
        cmd = ["bundle", "exec", "rake", "test"] if os.path.exists(
            os.path.join(repo_path, "Gemfile")
        ) else ["rake", "test"]
    else:
        # Direct ruby test discovery
        cmd = ["ruby", "-Itest", "-Ilib", "test/test_*.rb"]

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, cwd=repo_path,
        )
        output = (result.stdout + result.stderr).strip()
        return output, result.returncode == 0, errors
    except FileNotFoundError:
        msg = "rspec/rake/ruby not found — cannot run Ruby tests"
        return msg, True, [msg]
    except subprocess.TimeoutExpired:
        msg = f"Ruby test runner timed out after {timeout}s"
        return msg, False, [msg]
    except Exception as exc:
        msg = f"Ruby test runner failed: {exc}"
        return msg, False, [msg]


# ─────────────────────────────────────────────────────────────────
# Rust
# ─────────────────────────────────────────────────────────────────

def _run_cargo_test(repo_path: str) -> tuple[str, bool, list[str]]:
    errors: list[str] = []
    if not os.path.exists(os.path.join(repo_path, "Cargo.toml")):
        return "No Cargo.toml — cannot run Rust tests", True, []
    try:
        result = subprocess.run(
            ["cargo", "test"],
            capture_output=True, text=True,
            timeout=_TIMEOUT[Language.RUST.value],
            cwd=repo_path,
        )
        output = (result.stdout + result.stderr).strip()
        return output, result.returncode == 0, errors
    except FileNotFoundError:
        msg = "cargo not found — install Rust toolchain to run Rust tests"
        return msg, True, [msg]
    except subprocess.TimeoutExpired:
        msg = f"cargo test timed out after {_TIMEOUT[Language.RUST.value]}s"
        return msg, False, [msg]
    except Exception as exc:
        msg = f"cargo test failed: {exc}"
        return msg, False, [msg]


# ─────────────────────────────────────────────────────────────────
# C#
# ─────────────────────────────────────────────────────────────────

def _run_dotnet_test(repo_path: str) -> tuple[str, bool, list[str]]:
    errors: list[str] = []
    from pathlib import Path as _Path
    if not list(_Path(repo_path).rglob("*.csproj")):
        return "No .csproj found — cannot run C# tests", True, []
    try:
        result = subprocess.run(
            ["dotnet", "test", "--no-build", "--logger", "console;verbosity=minimal"],
            capture_output=True, text=True,
            timeout=_TIMEOUT[Language.CSHARP.value],
            cwd=repo_path,
        )
        output = (result.stdout + result.stderr).strip()
        return output, result.returncode == 0, errors
    except FileNotFoundError:
        msg = "dotnet not found — install .NET SDK to run C# tests"
        return msg, True, [msg]
    except subprocess.TimeoutExpired:
        msg = f"dotnet test timed out after {_TIMEOUT[Language.CSHARP.value]}s"
        return msg, False, [msg]
    except Exception as exc:
        msg = f"dotnet test failed: {exc}"
        return msg, False, [msg]

