# ai-engine/engine/nodes/failure_classifier.py

import re
import logging
from langchain_core.messages import HumanMessage

from engine.state import AgentState, Failure, BugType
from engine.config import llm
from engine.nodes.utils import emit

logger = logging.getLogger(__name__)

# ── Rule-based classification (fast, no LLM) ─────────────
RULE_PATTERNS: list[tuple[re.Pattern, BugType]] = [
    (re.compile(r"F401|unused.import|imported but unused", re.I), BugType.IMPORT),
    (re.compile(r"E1|W0611|W0614|unused-import", re.I), BugType.IMPORT),
    (re.compile(r"E1\d\d|SyntaxError|invalid syntax|unexpected EOF", re.I), BugType.SYNTAX),
    (re.compile(r"E1\d\d|W0311|W0312|indentation|unexpected indent|unindent", re.I), BugType.INDENTATION),
    (re.compile(r"E711|E712|W0612|undefined.name|NameError|AttributeError", re.I), BugType.LOGIC),
    (re.compile(r"E0001|pylint.*error|flake8.*E9", re.I), BugType.SYNTAX),
    (re.compile(r"mypy|type.error|TypeEr|incompatible type|no attribute", re.I), BugType.TYPE_ERROR),
    (re.compile(r"E1|W[0-9]|flake8.*W", re.I), BugType.LINTING),
]


def _classify_rule_based(text: str) -> BugType:
    for pattern, bug_type in RULE_PATTERNS:
        if pattern.search(text):
            return bug_type
    return BugType.LINTING  # default


def _parse_file_line(raw_line: str) -> tuple[str, int]:
    """Extract file path and line number from linter output."""
    # Format: path/to/file.py:15:4: E302 ...
    match = re.match(r"^([^:]+):(\d+)(?::\d+)?:", raw_line)
    if match:
        return match.group(1), int(match.group(2))
    return "unknown", 0


def failure_classifier(state: AgentState) -> dict:
    """
    Node 5: Parse static analysis + test output into structured Failure objects.
    Uses rule-based classification first, LLM only for ambiguous cases.
    """
    emit(state, "node_start", "classify", iteration=state["current_iteration"])

    static_output = state.get("static_analysis_output", "") or ""
    test_output = state.get("test_output", "") or ""
    repo_path = state.get("repo_local_path", "")

    failures: list[Failure] = []
    seen: set[str] = set()  # deduplicate by file:line:type

    # ── Parse static analysis output ─────────────────────
    for line in static_output.splitlines():
        line = line.strip()
        if not line or line.startswith("*") or line.startswith("-"):
            continue

        file_path, line_no = _parse_file_line(line)
        if file_path == "unknown":
            continue

        # Make path relative to repo
        if repo_path and file_path.startswith(repo_path):
            file_path = file_path[len(repo_path):].lstrip("/")

        bug_type = _classify_rule_based(line)
        dedup_key = f"{file_path}:{line_no}:{bug_type}"

        if dedup_key in seen:
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
        test_failures = _parse_test_output(test_output, repo_path)
        for f in test_failures:
            key = f"{f.file}:{f.line}:{f.bug_type}"
            if key not in seen:
                seen.add(key)
                failures.append(f)

    logger.info("Classified %d failures", len(failures))

    for f in failures[:3]:  # emit first 3 for SSE
        emit(state, "node_end", "classify",
             latest_failure=f.to_agent_output(),
             failures_count=len(failures))

    if not failures:
        emit(state, "node_end", "classify", failures_count=0)

    return {"failures": failures}


def _parse_test_output(test_output: str, repo_path: str) -> list[Failure]:
    failures = []
    lines = test_output.splitlines()

    for i, line in enumerate(lines):
        # pytest FAILED lines
        match = re.search(r"FAILED\s+([^:]+)::(\w+)", line)
        if match:
            file_path = match.group(1)
            failures.append(Failure(
                file=file_path,
                line=0,
                bug_type=BugType.LOGIC,
                description=line.strip(),
                raw_output=line.strip(),
            ))

        # Python traceback lines with file + line
        match = re.match(r'\s+File "([^"]+)", line (\d+)', line)
        if match:
            file_path = match.group(1)
            line_no = int(match.group(2))
            if repo_path and file_path.startswith(repo_path):
                file_path = file_path[len(repo_path):].lstrip("/")
            context = lines[i + 1].strip() if i + 1 < len(lines) else ""
            bug_type = _classify_rule_based(context or line)
            key = f"{file_path}:{line_no}"
            failures.append(Failure(
                file=file_path,
                line=line_no,
                bug_type=bug_type,
                description=context or line.strip(),
                raw_output=line.strip(),
            ))

    return failures
