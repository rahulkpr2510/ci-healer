# ai-engine/engine/nodes/static_analyzer.py

import os
import json
import shutil
import subprocess
import logging
import tempfile
from pathlib import Path

from engine.state import AgentState, Language
from engine.nodes.utils import emit

logger = logging.getLogger(__name__)

# ── ESLint rule severity levels for the generated fallback config ──────────
# fmt: off
_ESLINT_FALLBACK_RULES: dict = {
    # Possible errors
    "no-undef":              "error",
    "no-unused-vars":        ["warn", {"args": "none", "caughtErrors": "none"}],
    "no-unreachable":        "error",
    "no-duplicate-case":     "error",
    "no-dupe-keys":          "error",
    "no-dupe-args":          "error",
    "no-empty":              "warn",
    "no-extra-semi":         "warn",
    "no-redeclare":          "error",
    "no-shadow":             "warn",
    "use-isnan":             "error",
    "valid-typeof":          "error",
    # Best practices
    "eqeqeq":               ["warn", "always"],
    "no-eval":               "error",
    "no-implied-eval":       "error",
    "no-var":                "warn",
    "prefer-const":          "warn",
    # Syntax / style
    "semi":                  ["warn", "always"],
    "no-trailing-spaces":    "warn",
    "no-multiple-empty-lines": ["warn", {"max": 2}],
}
# fmt: on

_ESLINT_FALLBACK_CONFIG_V8 = {
    "env":     {"browser": True, "node": True, "es2021": True},
    "parserOptions": {
        "ecmaVersion": "latest",
        "sourceType": "module",
        "ecmaFeatures": {"jsx": True},
    },
    "rules": _ESLINT_FALLBACK_RULES,
}

# ESLint flat-config (v9+) variant written as a JS string
_ESLINT_FLAT_CONFIG_JS = """\
import js from "@eslint/js";
export default [
  js.configs.recommended,
  {
    rules: {
      "no-unused-vars": "warn",
      "no-undef": "error",
      "no-unreachable": "error",
      "no-duplicate-case": "error",
      "no-dupe-keys": "error",
      "no-redeclare": "error",
      "use-isnan": "error",
      "valid-typeof": "error",
      "eqeqeq": ["warn", "always"],
      "no-eval": "error",
      "no-var": "warn",
      "prefer-const": "warn",
      "semi": ["warn", "always"],
    },
  },
];
"""


def static_analyzer(state: AgentState) -> dict:
    """
    Node 3: Run static analysis on ALL repos regardless of language or
    whether a linter config exists inside the repo.

    Language → tools
    ─────────────────────────────────────────────────────────────
    Python      → flake8 (always) + pylint (always)
    JS / JSX    → ESLint (repo config if present, else generated
                  fallback) + node --check syntax validation
    TS / TSX    → ESLint (same strategy) + tsc --noEmit
    Go          → go vet + staticcheck (if installed)
    Java        → basic javac syntax check
    Ruby        → rubocop (if installed)
    Rust        → cargo check (if Cargo.toml present)
    C#          → dotnet build --no-restore (if .csproj present)
    Others      → LLM-only (no local tooling required)
    ─────────────────────────────────────────────────────────────
    Errors from any tool are surfaced with structured file:line output
    so the failure_classifier can parse and fix them.
    """
    emit(state, "node_start", "static", iteration=state["current_iteration"])

    repo_path        = state["repo_local_path"]
    primary_language = state.get("primary_language", Language.UNKNOWN.value)
    agent_errors: list[str] = []
    output_lines: list[str] = []

    dispatch: dict[str, object] = {
        Language.PYTHON.value:     _run_python_analysis,
        Language.JAVASCRIPT.value: _run_js_ts_analysis,
        Language.TYPESCRIPT.value: _run_js_ts_analysis,
        Language.GO.value:         _run_go_analysis,
        Language.JAVA.value:       _run_java_analysis,
        Language.RUBY.value:       _run_ruby_analysis,
        Language.RUST.value:       _run_rust_analysis,
        Language.CSHARP.value:     _run_csharp_analysis,
    }

    runner = dispatch.get(primary_language)
    if runner:
        try:
            output_lines, agent_errors = runner(repo_path, primary_language)  # type: ignore[operator]
        except Exception as exc:
            msg = f"Static analysis runner crashed for {primary_language}: {exc}"
            logger.exception(msg)
            agent_errors.append(msg)
    else:
        logger.info(
            "No dedicated static analyzer for language '%s' — LLM analysis only",
            primary_language,
        )

    raw_output = "\n".join(output_lines)
    logger.info(
        "Static analysis complete: %d findings, %d tool errors",
        len(output_lines), len(agent_errors),
    )

    emit(
        state, "node_end", "static",
        findings_count=len(output_lines),
        tool_errors=agent_errors,
    )

    result: dict = {"static_analysis_output": raw_output}
    if agent_errors:
        result["agent_errors"] = agent_errors
    return result


# ─────────────────────────────────────────────────────────────────
# Python
# ─────────────────────────────────────────────────────────────────

def _run_python_analysis(repo_path: str, _lang: str = "") -> tuple[list[str], list[str]]:
    lines: list[str]  = []
    errors: list[str] = []
    repo_path = str(Path(repo_path).resolve())

    # ── flake8 ────────────────────────────────────────────
    try:
        result = subprocess.run(
            [
                "python3", "-m", "flake8",
                "--max-line-length=120",
                "--format=%(path)s:%(row)d:%(col)d: %(code)s %(text)s",
                ".",
            ],
            capture_output=True, text=True, timeout=60, cwd=repo_path,
        )
        if result.stdout.strip():
            lines.extend(result.stdout.strip().splitlines())
        if result.returncode not in (0, 1) and result.stderr.strip():
            errors.append(f"flake8 exited {result.returncode}: {result.stderr.strip()[:300]}")
    except FileNotFoundError:
        errors.append(
            "flake8 not found in PATH. "
            "Install it with: pip install flake8"
        )
    except subprocess.TimeoutExpired:
        errors.append("flake8 timed out after 60 s")
    except Exception as exc:
        errors.append(f"flake8 unexpected error: {exc}")

    # ── pylint ────────────────────────────────────────────
    try:
        py_files = [
            str(p.relative_to(repo_path))
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
            if result.returncode not in (0, 1, 2, 4, 8, 16, 32) and result.stderr.strip():
                errors.append(f"pylint exited {result.returncode}: {result.stderr.strip()[:300]}")
    except FileNotFoundError:
        errors.append(
            "pylint not found in PATH. "
            "Install it with: pip install pylint"
        )
    except subprocess.TimeoutExpired:
        errors.append("pylint timed out after 90 s")
    except Exception as exc:
        errors.append(f"pylint unexpected error: {exc}")

    return lines, errors


# ─────────────────────────────────────────────────────────────────
# JavaScript / TypeScript  (always runs — no config required)
# ─────────────────────────────────────────────────────────────────

_ESLINT_CONFIG_FILES = [
    ".eslintrc",
    ".eslintrc.js",
    ".eslintrc.cjs",
    ".eslintrc.json",
    ".eslintrc.yaml",
    ".eslintrc.yml",
    "eslint.config.js",
    "eslint.config.cjs",
    "eslint.config.mjs",
    "eslint.config.ts",
]


def _npm_ensure_deps(repo_path: str) -> list[str]:
    """Install node_modules if missing. Returns list of error strings."""
    errors: list[str] = []
    if not os.path.exists(os.path.join(repo_path, "node_modules")):
        pkg_json = os.path.join(repo_path, "package.json")
        if os.path.exists(pkg_json):
            logger.info("Running npm install in %s", repo_path)
            try:
                result = subprocess.run(
                    ["npm", "install", "--prefer-offline", "--no-audit", "--no-fund"],
                    capture_output=True, text=True, timeout=180, cwd=repo_path,
                )
                if result.returncode != 0:
                    errors.append(
                        f"npm install failed (exit {result.returncode}): "
                        f"{result.stderr.strip()[:400]}"
                    )
            except FileNotFoundError:
                errors.append(
                    "npm not found in PATH. Install Node.js to enable JS/TS analysis."
                )
            except subprocess.TimeoutExpired:
                errors.append("npm install timed out after 180 s")
        else:
            logger.info("No package.json in repo — skipping npm install")
    return errors


def _detect_eslint_version(repo_path: str) -> int:
    """Return major ESLint version (8 or 9) available in the repo/global. Falls back to 8."""
    try:
        result = subprocess.run(
            ["npx", "--no-install", "eslint", "--version"],
            capture_output=True, text=True, timeout=15, cwd=repo_path,
        )
        version_str = result.stdout.strip().lstrip("v")
        major = int(version_str.split(".")[0])
        logger.debug("ESLint version detected: %d", major)
        return major
    except Exception:
        return 8  # safe default


def _run_eslint_with_fallback_config(
    repo_path: str,
    is_typescript: bool,
) -> tuple[list[str], list[str]]:
    """
    Runs ESLint. If no config exists in the repo, a minimal config is
    temporarily written so analysis ALWAYS happens.
    Returns (output_lines, error_strings).
    """
    lines:  list[str] = []
    errors: list[str] = []

    has_config = any(
        os.path.exists(os.path.join(repo_path, cfg))
        for cfg in _ESLINT_CONFIG_FILES
    )

    # Also check package.json for "eslintConfig" key
    if not has_config:
        pkg_json_path = os.path.join(repo_path, "package.json")
        if os.path.exists(pkg_json_path):
            try:
                with open(pkg_json_path, encoding="utf-8") as fh:
                    pkg = json.load(fh)
                if "eslintConfig" in pkg:
                    has_config = True
            except Exception:
                pass

    generated_config: str | None = None  # path to temp config if we created one

    if not has_config:
        eslint_ver = _detect_eslint_version(repo_path)
        if eslint_ver >= 9:
            # Flat config (v9+): write eslint.config.mjs
            config_path = os.path.join(repo_path, "eslint.config.mjs")
            try:
                with open(config_path, "w", encoding="utf-8") as fh:
                    fh.write(_ESLINT_FLAT_CONFIG_JS)
                generated_config = config_path
                logger.info(
                    "No ESLint config found — generated temporary flat config (v9+) at %s",
                    config_path,
                )
            except Exception as exc:
                errors.append(f"Could not write temporary ESLint flat config: {exc}")
        else:
            # Legacy config (v8): write .eslintrc.json
            config_path = os.path.join(repo_path, ".eslintrc.json")
            try:
                cfg = dict(_ESLINT_FALLBACK_CONFIG_V8)
                if is_typescript:
                    # Add basic TS parser if @typescript-eslint is installed
                    ts_parser_path = os.path.join(
                        repo_path, "node_modules", "@typescript-eslint", "parser"
                    )
                    if os.path.exists(ts_parser_path):
                        cfg["parser"] = "@typescript-eslint/parser"
                        cfg["plugins"] = ["@typescript-eslint"]
                with open(config_path, "w", encoding="utf-8") as fh:
                    json.dump(cfg, fh, indent=2)
                generated_config = config_path
                logger.info(
                    "No ESLint config found — generated temporary .eslintrc.json at %s",
                    config_path,
                )
            except Exception as exc:
                errors.append(f"Could not write temporary ESLint config: {exc}")

    # ── Determine which file extensions to lint ───────────
    ext_args = (
        ["--ext", ".ts,.tsx,.js,.jsx,.mjs,.cjs"]
        if is_typescript
        else ["--ext", ".js,.jsx,.mjs,.cjs"]
    )

    try:
        cmd = ["npx", "eslint", "--format=compact"] + ext_args + ["."]
        result = subprocess.run(
            cmd,
            capture_output=True, text=True, timeout=120, cwd=repo_path,
            env={**os.environ, "CI": "true"},   # suppress interactive prompts
        )

        stdout = result.stdout.strip()
        stderr = result.stderr.strip()

        if stdout:
            # Filter out noise lines (progress bars, npm warnings, etc.)
            for line in stdout.splitlines():
                if line.strip() and not line.startswith("npm "):
                    lines.append(line)

        # Non-zero exit with no stdout → ESLint itself errored
        if result.returncode not in (0, 1) and not stdout:
            detail = stderr[:500] if stderr else f"exit code {result.returncode}"
            errors.append(f"ESLint exited with error: {detail}")
            logger.warning("ESLint error output: %s", stderr[:300])

    except FileNotFoundError:
        errors.append(
            "npx / ESLint not found. Install Node.js and run: npm install eslint --save-dev"
        )
    except subprocess.TimeoutExpired:
        errors.append("ESLint timed out after 120 s")
    except Exception as exc:
        errors.append(f"ESLint unexpected error: {exc}")
    finally:
        # Always clean up any generated config so we don't pollute the repo
        if generated_config and os.path.exists(generated_config):
            try:
                os.remove(generated_config)
                logger.debug("Removed temporary ESLint config: %s", generated_config)
            except Exception as exc:
                logger.warning("Could not remove temp ESLint config: %s", exc)

    return lines, errors


def _run_node_syntax_check(repo_path: str) -> tuple[list[str], list[str]]:
    """
    Lightweight JS syntax check via `node --check <file>`.
    Catches SyntaxErrors that ESLint might miss or when ESLint isn't available.
    """
    lines:  list[str] = []
    errors: list[str] = []

    js_files = [
        str(p.relative_to(repo_path))
        for p in Path(repo_path).rglob("*.js")
        if "node_modules" not in str(p)
        and ".next" not in str(p)
        and "dist" not in str(p)
        and "build" not in str(p)
    ]

    if not js_files:
        return lines, errors

    # Check up to 100 files to keep it fast
    for rel_path in js_files[:100]:
        try:
            result = subprocess.run(
                ["node", "--check", rel_path],
                capture_output=True, text=True, timeout=10, cwd=repo_path,
            )
            if result.returncode != 0:
                for line in (result.stderr or result.stdout).splitlines():
                    if line.strip():
                        lines.append(line.strip())
        except FileNotFoundError:
            errors.append("node not found in PATH — skipping syntax check")
            break
        except subprocess.TimeoutExpired:
            continue
        except Exception as exc:
            errors.append(f"node --check error on {rel_path}: {exc}")

    return lines, errors


def _run_tsc_check(repo_path: str) -> tuple[list[str], list[str]]:
    """
    Run `tsc --noEmit` to surface TypeScript type errors.
    Works with or without a tsconfig — uses --allowJs if no tsconfig found.
    """
    lines:  list[str] = []
    errors: list[str] = []

    has_tsconfig = os.path.exists(os.path.join(repo_path, "tsconfig.json"))

    cmd = ["npx", "--no-install", "tsc", "--noEmit"]
    if not has_tsconfig:
        # Generate minimal inline flags instead of a file
        cmd += [
            "--allowJs", "--checkJs",
            "--strict", "--target", "ES2020",
            "--moduleResolution", "node",
        ]
        # Point tsc at all TS files explicitly
        ts_files = [
            str(p.relative_to(repo_path))
            for p in Path(repo_path).rglob("*.ts")
            if "node_modules" not in str(p) and "dist" not in str(p)
        ]
        if not ts_files:
            return lines, errors
        cmd += ts_files[:50]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True, text=True, timeout=90, cwd=repo_path,
        )
        combined = (result.stdout + "\n" + result.stderr).strip()
        for line in combined.splitlines():
            stripped = line.strip()
            if stripped and "error TS" in stripped:
                lines.append(stripped)
        if result.returncode not in (0, 1, 2) and not lines:
            errors.append(
                f"tsc exited {result.returncode}: {combined[:300]}"
            )
    except FileNotFoundError:
        logger.debug("tsc not available — skipping TypeScript compiler check")
    except subprocess.TimeoutExpired:
        errors.append("tsc --noEmit timed out after 90 s")
    except Exception as exc:
        errors.append(f"tsc unexpected error: {exc}")

    return lines, errors


def _run_js_ts_analysis(repo_path: str, primary_language: str) -> tuple[list[str], list[str]]:
    """
    Full JS/TS static analysis pipeline — always runs regardless of whether
    the repo ships with an ESLint config.

    Steps (all run; results are merged):
    1. npm install (if package.json exists and node_modules missing)
    2. ESLint  — repo config if present, generated fallback if not
    3. node --check  — lightweight syntax validation for .js files
    4. tsc --noEmit  — TypeScript type errors (TS repos only)
    """
    all_lines:  list[str] = []
    all_errors: list[str] = []

    is_typescript = (primary_language == Language.TYPESCRIPT.value)

    # 1. Ensure deps
    npm_errors = _npm_ensure_deps(repo_path)
    all_errors.extend(npm_errors)

    # 2. ESLint (always — no config is no longer a barrier)
    eslint_lines, eslint_errors = _run_eslint_with_fallback_config(repo_path, is_typescript)
    all_lines.extend(eslint_lines)
    all_errors.extend(eslint_errors)

    logger.info(
        "ESLint completed: %d findings, %d errors",
        len(eslint_lines), len(eslint_errors),
    )

    # 3. node --check  (JS syntax — fast, catches parse errors even if ESLint fails)
    if not is_typescript:
        syntax_lines, syntax_errors = _run_node_syntax_check(repo_path)
        # Only add lines not already captured by ESLint
        for line in syntax_lines:
            if line not in all_lines:
                all_lines.append(line)
        all_errors.extend(syntax_errors)
        logger.info("node --check: %d extra findings", len(syntax_lines))

    # 4. tsc --noEmit (TypeScript only)
    if is_typescript:
        tsc_lines, tsc_errors = _run_tsc_check(repo_path)
        all_lines.extend(tsc_lines)
        all_errors.extend(tsc_errors)
        logger.info("tsc: %d findings", len(tsc_lines))

    return all_lines, all_errors


# ─────────────────────────────────────────────────────────────────
# Go
# ─────────────────────────────────────────────────────────────────

def _run_go_analysis(repo_path: str, _lang: str = "") -> tuple[list[str], list[str]]:
    lines:  list[str] = []
    errors: list[str] = []

    try:
        result = subprocess.run(
            ["go", "vet", "./..."],
            capture_output=True, text=True, timeout=120, cwd=repo_path,
        )
        combined = (result.stdout + "\n" + result.stderr).strip()
        if combined:
            lines.extend(line for line in combined.splitlines() if line.strip())
        if result.returncode not in (0, 1) and not lines:
            errors.append(f"go vet exited {result.returncode}: {combined[:300]}")
    except FileNotFoundError:
        errors.append("go not found in PATH — install Go to enable Go analysis")
    except subprocess.TimeoutExpired:
        errors.append("go vet timed out after 120 s")
    except Exception as exc:
        errors.append(f"go vet error: {exc}")

    # staticcheck if available
    if shutil.which("staticcheck"):
        try:
            result = subprocess.run(
                ["staticcheck", "./..."],
                capture_output=True, text=True, timeout=120, cwd=repo_path,
            )
            if result.stdout.strip():
                lines.extend(result.stdout.strip().splitlines())
        except Exception as exc:
            errors.append(f"staticcheck error: {exc}")

    return lines, errors


# ─────────────────────────────────────────────────────────────────
# Java
# ─────────────────────────────────────────────────────────────────

def _run_java_analysis(repo_path: str, _lang: str = "") -> tuple[list[str], list[str]]:
    lines:  list[str] = []
    errors: list[str] = []

    java_files = [
        str(p.relative_to(repo_path))
        for p in Path(repo_path).rglob("*.java")
        if "target" not in str(p) and ".gradle" not in str(p)
    ]
    if not java_files:
        return lines, errors

    try:
        result = subprocess.run(
            ["javac", "-proc:none", *java_files[:50]],
            capture_output=True, text=True, timeout=120, cwd=repo_path,
        )
        combined = (result.stdout + "\n" + result.stderr).strip()
        if combined:
            lines.extend(line for line in combined.splitlines() if line.strip())
        if result.returncode not in (0, 1) and not lines:
            errors.append(f"javac exited {result.returncode}: {combined[:300]}")
    except FileNotFoundError:
        errors.append("javac not found — install JDK to enable Java analysis")
    except subprocess.TimeoutExpired:
        errors.append("javac timed out after 120 s")
    except Exception as exc:
        errors.append(f"javac error: {exc}")

    return lines, errors


# ─────────────────────────────────────────────────────────────────
# Ruby
# ─────────────────────────────────────────────────────────────────

def _run_ruby_analysis(repo_path: str, _lang: str = "") -> tuple[list[str], list[str]]:
    lines:  list[str] = []
    errors: list[str] = []

    # rubocop
    if shutil.which("rubocop"):
        try:
            result = subprocess.run(
                [
                    "rubocop",
                    "--format", "clang",
                    "--no-color",
                    "--fail-level", "warning",
                ],
                capture_output=True, text=True, timeout=120, cwd=repo_path,
            )
            if result.stdout.strip():
                lines.extend(result.stdout.strip().splitlines())
            if result.returncode not in (0, 1) and not lines:
                errors.append(
                    f"rubocop exited {result.returncode}: {result.stderr.strip()[:300]}"
                )
        except subprocess.TimeoutExpired:
            errors.append("rubocop timed out after 120 s")
        except Exception as exc:
            errors.append(f"rubocop error: {exc}")
    else:
        # Fallback: ruby -c syntax check on each file
        rb_files = [
            str(p.relative_to(repo_path))
            for p in Path(repo_path).rglob("*.rb")
        ]
        for rb_file in rb_files[:50]:
            try:
                result = subprocess.run(
                    ["ruby", "-c", rb_file],
                    capture_output=True, text=True, timeout=10, cwd=repo_path,
                )
                if result.returncode != 0:
                    lines.extend(
                        line for line in (result.stderr or result.stdout).splitlines()
                        if line.strip()
                    )
            except FileNotFoundError:
                errors.append("ruby not found — install Ruby to enable Ruby analysis")
                break
            except Exception as exc:
                errors.append(f"ruby -c error on {rb_file}: {exc}")

    return lines, errors


# ─────────────────────────────────────────────────────────────────
# Rust
# ─────────────────────────────────────────────────────────────────

def _run_rust_analysis(repo_path: str, _lang: str = "") -> tuple[list[str], list[str]]:
    lines:  list[str] = []
    errors: list[str] = []

    if not os.path.exists(os.path.join(repo_path, "Cargo.toml")):
        return lines, ["No Cargo.toml found — cannot run cargo check"]

    try:
        result = subprocess.run(
            ["cargo", "check", "--message-format=short"],
            capture_output=True, text=True, timeout=180, cwd=repo_path,
        )
        combined = (result.stdout + "\n" + result.stderr).strip()
        if combined:
            lines.extend(line for line in combined.splitlines() if line.strip())
        if result.returncode not in (0, 1) and not lines:
            errors.append(f"cargo check exited {result.returncode}: {combined[:300]}")
    except FileNotFoundError:
        errors.append("cargo not found — install Rust toolchain to enable Rust analysis")
    except subprocess.TimeoutExpired:
        errors.append("cargo check timed out after 180 s")
    except Exception as exc:
        errors.append(f"cargo check error: {exc}")

    # clippy if available
    if shutil.which("cargo"):
        try:
            result = subprocess.run(
                ["cargo", "clippy", "--message-format=short", "--", "-D", "warnings"],
                capture_output=True, text=True, timeout=180, cwd=repo_path,
            )
            if result.stdout.strip():
                for line in result.stdout.splitlines():
                    if line.strip() and line not in lines:
                        lines.append(line)
        except Exception as exc:
            errors.append(f"cargo clippy error: {exc}")

    return lines, errors


# ─────────────────────────────────────────────────────────────────
# C#
# ─────────────────────────────────────────────────────────────────

def _run_csharp_analysis(repo_path: str, _lang: str = "") -> tuple[list[str], list[str]]:
    lines:  list[str] = []
    errors: list[str] = []

    csproj_files = list(Path(repo_path).rglob("*.csproj"))
    if not csproj_files:
        return lines, ["No .csproj file found — cannot run dotnet build"]

    try:
        result = subprocess.run(
            [
                "dotnet", "build",
                "--no-restore",
                "-v", "minimal",
                "--nologo",
            ],
            capture_output=True, text=True, timeout=180, cwd=repo_path,
        )
        combined = (result.stdout + "\n" + result.stderr).strip()
        for line in combined.splitlines():
            if ": error " in line or ": warning " in line:
                lines.append(line.strip())
        if result.returncode not in (0, 1) and not lines:
            errors.append(f"dotnet build exited {result.returncode}: {combined[:300]}")
    except FileNotFoundError:
        errors.append("dotnet not found — install .NET SDK to enable C# analysis")
    except subprocess.TimeoutExpired:
        errors.append("dotnet build timed out after 180 s")
    except Exception as exc:
        errors.append(f"dotnet build error: {exc}")

    return lines, errors
