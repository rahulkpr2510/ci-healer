# ai-engine/engine/nodes/failure_classifier.py

import re
import logging
from langchain_core.messages import HumanMessage

from engine.state import AgentState, Failure, BugType
from engine.config import llm
from engine.nodes.utils import emit

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────
# Rule-based bug-type classification
# ─────────────────────────────────────────────────────────────────

RULE_PATTERNS: list[tuple[re.Pattern, BugType]] = [
    # Import / undefined
    (re.compile(r"F401|unused.import|imported but unused|W0611|W0614|unused-import"
                r"|no-unused-vars|'[^']+' is defined but never used", re.I), BugType.IMPORT),
    (re.compile(r"ModuleNotFoundError|ImportError|cannot find module|module not found"
                r"|no-undef|'[^']+' is not defined|unresolved import", re.I), BugType.DEPENDENCY),
    # Syntax
    (re.compile(r"SyntaxError|invalid syntax|unexpected EOF|unexpected token"
                r"|Unexpected token|Parsing error|E0001|error TS1\d{3}", re.I), BugType.SYNTAX),
    # Compilation
    (re.compile(r"error: |E\d{4}|cannot find symbol|undefined symbol|undeclared identifier"
                r"|does not exist|cannot resolve", re.I), BugType.COMPILATION),
    # Indentation
    (re.compile(r"W0311|W0312|E1\d\d|IndentationError|unexpected indent|unindent"
                r"|mixed tabs and spaces", re.I), BugType.INDENTATION),
    # Type errors
    (re.compile(r"TypeError|TypeEr|incompatible type|type error|error TS2\d{3}"
                r"|no attribute|AttributeError|type .* is not assignable", re.I), BugType.TYPE_ERROR),
    # Logic / runtime
    (re.compile(r"NameError|AssertionError|FAILED|FAIL|RuntimeError|ZeroDivision"
                r"|IndexError|KeyError|ValueError|no-unreachable|eqeqeq"
                r"|use-isnan|valid-typeof", re.I), BugType.LOGIC),
    # Security
    (re.compile(r"no-eval|no-implied-eval|bandit|security|B[0-9]{3}", re.I), BugType.SECURITY),
    # Formatting
    (re.compile(r"gofmt|rustfmt|black|prettier|trailing.whitespace|no-trailing-spaces"
                r"|semi.*error|extra-semi", re.I), BugType.FORMATTING),
    # Linting catch-all
    (re.compile(r"E[0-9]|W[0-9]|C[0-9]|R[0-9]|flake8|pylint|eslint|rubocop"
                r"|go vet|clippy|warning", re.I), BugType.LINTING),
]


def _classify_rule_based(text: str) -> BugType:
    for pattern, bug_type in RULE_PATTERNS:
        if pattern.search(text):
            return bug_type
    return BugType.LINTING  # safe default


# ─────────────────────────────────────────────────────────────────
# Output-format parsers — each returns (file_path, line_no) or None
# ─────────────────────────────────────────────────────────────────

def _parse_standard(line: str) -> tuple[str, int] | None:
    """Standard  path/to/file.ext:LINE:COL: message"""
    m = re.match(r"^([^:]+):(\d+)(?::\d+)?[:\s]", line)
    if m:
        return m.group(1).strip(), int(m.group(2))
    return None


def _parse_eslint_compact(line: str) -> tuple[str, int] | None:
    """ESLint compact:  /abs/path/file.js: line 5, col 3, Error - ..."""
    m = re.match(r"^(.+?):\s+line (\d+),\s+col \d+[,\s]", line)
    if m:
        return m.group(1).strip(), int(m.group(2))
    return None


def _parse_tsc(line: str) -> tuple[str, int] | None:
    """TypeScript tsc:  src/foo.ts(12,3): error TS2322: ..."""
    m = re.match(r"^([^(]+)\((\d+),\d+\):\s+(?:error|warning)", line)
    if m:
        return m.group(1).strip(), int(m.group(2))
    return None


def _parse_go_vet(line: str) -> tuple[str, int] | None:
    """go vet / staticcheck:  ./path/file.go:15:3: ..."""
    m = re.match(r"^\.?/?([\w./\-]+\.go):(\d+)(?::\d+)?:", line)
    if m:
        return m.group(1).strip(), int(m.group(2))
    return None


def _parse_cargo(line: str) -> tuple[str, int] | None:
    """cargo check short:  src/main.rs:10:5: ..."""
    m = re.match(r"^([^:\s]+\.rs):(\d+)(?::\d+)?:", line)
    if m:
        return m.group(1).strip(), int(m.group(2))
    return None


def _parse_java(line: str) -> tuple[str, int] | None:
    """javac:  src/Foo.java:25: error: ..."""
    m = re.match(r"^(.+\.java):(\d+):\s+(?:error|warning|note):", line)
    if m:
        return m.group(1).strip(), int(m.group(2))
    return None


def _parse_rubocop(line: str) -> tuple[str, int] | None:
    """rubocop --format clang:  path/file.rb:10:3: C: Layout/..."""
    m = re.match(r"^([^:]+\.rb):(\d+):\d+: [CWEF]:", line)
    if m:
        return m.group(1).strip(), int(m.group(2))
    return None


def _parse_dotnet(line: str) -> tuple[str, int] | None:
    """MSBuild/dotnet:  src/Foo.cs(12,5): error CS..."""
    m = re.match(r"^([^(]+\.cs)\((\d+),\d+\):\s+(?:error|warning)", line)
    if m:
        return m.group(1).strip(), int(m.group(2))
    return None


# Ordered list of parsers — first match wins
_PARSERS = [
    _parse_eslint_compact,
    _parse_tsc,
    _parse_go_vet,
    _parse_cargo,
    _parse_java,
    _parse_rubocop,
    _parse_dotnet,
    _parse_standard,
]


def _parse_file_line(raw_line: str) -> tuple[str, int]:
    for parser in _PARSERS:
        result = parser(raw_line)
        if result:
            return result
    return "unknown", 0


# ─────────────────────────────────────────────────────────────────
# Main node
# ─────────────────────────────────────────────────────────────────

def failure_classifier(state: AgentState) -> dict:
    """
    Node 5: Parse static analysis + test output into structured Failure objects.

    Key behaviours:
    - Runs after EACH iteration — only looks at the CURRENT iteration's outputs
    - Deduplicates against previously seen failures from prior iterations so the
      fix generator doesn't re-attempt already-fixed issues
    - Uses multi-format parsers so Python/JS/TS/Go/Java/Ruby/Rust/C# all work
    - Rule-based classification first; falls back to BugType.LINTING when no
      pattern matches
    """
    emit(state, "node_start", "classify", iteration=state["current_iteration"])

    static_output = state.get("static_analysis_output", "") or ""
    test_output   = state.get("test_output", "") or ""
    repo_path     = state.get("repo_local_path", "")

    # ── Build a set of failures already fixed in prior iterations ─
    prior_fixed_keys: set[str] = set()
    for fix in state.get("fixes", []):
        from engine.state import FixStatus
        if fix.status == FixStatus.FIXED:
            prior_fixed_keys.add(f"{fix.file}:{fix.line}")

    failures: list[Failure] = []
    seen: set[str] = set()  # dedup within THIS iteration

    # ── Parse static analysis output ─────────────────────
    for line in static_output.splitlines():
        line = line.strip()
        if not line:
            continue
        # Skip pure header/separator lines
        if re.match(r"^[-=*]+$", line) or line.startswith("Your code has been rated"):
            continue

        file_path, line_no = _parse_file_line(line)
        if file_path == "unknown":
            continue

        # Normalise path — strip leading repo_path prefix
        file_path = _normalise_path(file_path, repo_path)

        bug_type  = _classify_rule_based(line)
        dedup_key = f"{file_path}:{line_no}:{bug_type}"
        prior_key = f"{file_path}:{line_no}"

        if dedup_key in seen:
            continue
        if prior_key in prior_fixed_keys:
            logger.debug("Skipping already-fixed failure: %s", prior_key)
            continue

        seen.add(dedup_key)
        failures.append(Failure(
            file=file_path,
            line=line_no,
            bug_type=bug_type,
            description=line,
            raw_output=line,
        ))

    # ── Parse test failures (if tests exist and failed) ───
    if not state.get("test_passed", True) and test_output:
        for f in _parse_test_output(test_output, repo_path):
            key   = f"{f.file}:{f.line}:{f.bug_type}"
            prior = f"{f.file}:{f.line}"
            if key not in seen and prior not in prior_fixed_keys:
                seen.add(key)
                failures.append(f)

    logger.info(
        "Classified %d failures in iteration %d",
        len(failures), state.get("current_iteration", 1),
    )

    for f in failures[:3]:
        emit(state, "node_end", "classify",
             latest_failure=f.to_agent_output(),
             failures_count=len(failures))

    # ── Build skip reason when nothing left to fix ────────
    skip_reason: str | None = state.get("skip_reason")
    if not failures and not skip_reason:
        parts: list[str] = []
        static_out  = (state.get("static_analysis_output") or "").strip()
        test_out    = (state.get("test_output") or "").strip()
        has_tests   = state.get("has_tests", False)
        test_passed = state.get("test_passed", True)

        agent_errors   = state.get("agent_errors", [])
        tool_available = not any(
            "not found" in e.lower() or "not available" in e.lower()
            for e in agent_errors
        )

        if static_out:
            parts.append("static analysis found 0 actionable issues")
        elif not tool_available:
            parts.append("static analysis tooling not available in this environment")
        else:
            parts.append("no static analysis issues detected")

        if has_tests and test_passed:
            parts.append("all tests are passing")
        elif has_tests and "not available" in test_out.lower():
            parts.append("test runner not available in this environment")
        elif not has_tests:
            parts.append("no test files found in repo")

        skip_reason = "No issues to fix — " + " and ".join(parts) + "."
        logger.info("No failures found. Skip reason: %s", skip_reason)
        emit(state, "node_end", "classify", failures_count=0, skip_reason=skip_reason)

    return {
        "failures": failures,
        "current_iteration_failures": failures,
        "skip_reason": skip_reason,
    }


# ─────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────

def _normalise_path(file_path: str, repo_path: str) -> str:
    """Strip repo_path prefix and leading slashes for a clean relative path."""
    if repo_path and file_path.startswith(repo_path):
        file_path = file_path[len(repo_path):].lstrip("/\\")
    # Strip leading './' if present
    if file_path.startswith("./"):
        file_path = file_path[2:]
    return file_path


def _parse_test_output(test_output: str, repo_path: str) -> list[Failure]:
    failures: list[Failure] = []
    lines = test_output.splitlines()

    for i, line in enumerate(lines):
        # pytest FAILED lines: FAILED path/to/test.py::test_name
        m = re.search(r"FAILED\s+([\w/.\-]+\.py)::(\w+)", line)
        if m:
            failures.append(Failure(
                file=_normalise_path(m.group(1), repo_path),
                line=0,
                bug_type=BugType.LOGIC,
                description=line.strip(),
                raw_output=line.strip(),
            ))

        # Python traceback: File "path", line N
        m = re.match(r'\s+File "([^"]+)", line (\d+)', line)
        if m:
            fp  = _normalise_path(m.group(1), repo_path)
            ln  = int(m.group(2))
            ctx = lines[i + 1].strip() if i + 1 < len(lines) else ""
            failures.append(Failure(
                file=fp,
                line=ln,
                bug_type=_classify_rule_based(ctx or line),
                description=ctx or line.strip(),
                raw_output=line.strip(),
            ))

        # Jest / Mocha: ✕ or ✗ test names with file context
        m = re.search(r"([\w/.\-]+\.(js|ts|jsx|tsx)):(\d+):\d+", line)
        if m:
            failures.append(Failure(
                file=_normalise_path(m.group(1), repo_path),
                line=int(m.group(3)),
                bug_type=BugType.LOGIC,
                description=line.strip(),
                raw_output=line.strip(),
            ))

        # Go test failures:  --- FAIL: TestFoo (file.go:15)
        m = re.search(r"--- FAIL: \w+ \(([\w/.\-]+\.go):(\d+)\)", line)
        if m:
            failures.append(Failure(
                file=_normalise_path(m.group(1), repo_path),
                line=int(m.group(2)),
                bug_type=BugType.LOGIC,
                description=line.strip(),
                raw_output=line.strip(),
            ))

    return failures
