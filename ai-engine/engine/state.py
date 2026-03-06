# ai-engine/engine/state.py

from typing import TypedDict, Optional, Annotated
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import operator


# ── Enums ─────────────────────────────────────────────────

class BugType(str, Enum):
    LINTING      = "LINTING"
    SYNTAX       = "SYNTAX"
    LOGIC        = "LOGIC"
    TYPE_ERROR   = "TYPE_ERROR"
    IMPORT       = "IMPORT"
    INDENTATION  = "INDENTATION"
    COMPILATION  = "COMPILATION"   # build / compile error
    RUNTIME      = "RUNTIME"       # runtime / test-execution error
    DEPENDENCY   = "DEPENDENCY"    # missing module / gem / package
    SECURITY     = "SECURITY"      # security lint (e.g. bandit, eslint-security)
    FORMATTING   = "FORMATTING"    # style / formatting (gofmt, rustfmt, black)
    UNKNOWN      = "UNKNOWN"


class FixStatus(str, Enum):
    FIXED   = "FIXED"
    FAILED  = "FAILED"
    SKIPPED = "SKIPPED"


class RunStatus(str, Enum):
    RUNNING   = "RUNNING"
    PASSED    = "PASSED"
    FAILED    = "FAILED"
    NO_ISSUES = "NO_ISSUES"   # repo analysed but nothing to fix/heal


class Language(str, Enum):
    # Tier-1 — full static + test + fix support
    PYTHON     = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    GO         = "go"
    JAVA       = "java"
    RUBY       = "ruby"
    RUST       = "rust"
    CSHARP     = "csharp"
    # Tier-2 — static analysis + LLM fix (no integrated test runner)
    C          = "c"
    CPP        = "cpp"
    PHP        = "php"
    SWIFT      = "swift"
    KOTLIN     = "kotlin"
    SCALA      = "scala"
    SHELL      = "shell"
    R          = "r"
    DART       = "dart"
    LUA        = "lua"
    ELIXIR     = "elixir"
    HASKELL    = "haskell"
    # Fallback
    UNKNOWN    = "unknown"


# ── Sub-dataclasses ───────────────────────────────────────
# These are the structured objects stored inside AgentState lists

@dataclass
class Failure:
    file: str
    line: int
    bug_type: BugType
    description: str
    raw_output: str = ""

    def to_agent_output(self) -> dict:
        return {
            "file": self.file,
            "line": self.line,
            "bug_type": self.bug_type.value,
            "description": self.description,
        }


@dataclass
class Fix:
    file: str
    line: int
    bug_type: BugType
    commit_message: str
    status: FixStatus
    diff: str = ""
    before_snippet: str = ""
    after_snippet: str = ""


@dataclass
class CiRun:
    iteration: int
    status: RunStatus
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    @property
    def iteration_label(self) -> str:
        return f"{self.iteration}/?"   # max filled in by orchestrator


@dataclass
class ScoreCard:
    base_score: int = 100
    speed_bonus: int = 0
    efficiency_penalty: int = 0

    @property
    def final_score(self) -> int:
        return max(0, self.base_score + self.speed_bonus - self.efficiency_penalty)

    def model_dump(self) -> dict:
        return {
            "base_score": self.base_score,
            "speed_bonus": self.speed_bonus,
            "efficiency_penalty": self.efficiency_penalty,
            "final_score": self.final_score,
        }


# ── Core AgentState ───────────────────────────────────────
# TypedDict so LangGraph can serialize/checkpoint it

class AgentState(TypedDict):

    # ── Run inputs (set once at start) ────────────────────
    repo_url: str
    branch_prefix: str          # optional prefix for fix branch name
    github_token: Optional[str]
    max_iterations: int
    read_only: bool

    # ── Repo context (set by repo_analyzer) ───────────────
    repo_local_path: Optional[str]          # abs path to cloned repo on disk
    repo_owner: Optional[str]
    repo_name: Optional[str]
    branch_name: Optional[str]              # CI_HEALER_AI_FIX_N or PREFIX_AI_FIX_N
    default_branch: Optional[str]           # main / master

    # ── Language + structure (set by language_detector) ───
    primary_language: Optional[str]         # Language enum value
    detected_languages: list[str]
    has_tests: bool                         # True if test files found
    test_files: list[str]                   # relative paths to test files
    source_files: list[str]                 # all non-test source files

    # ── Test + analysis output ────────────────────────────
    test_output: Optional[str]              # raw stdout from test runner
    test_passed: bool
    static_analysis_output: Optional[str]  # raw output from linter

    # ── Agent findings (appended by each node) ────────────
    # Annotated with operator.add so LangGraph merges lists across nodes
    failures: Annotated[list[Failure], operator.add]   # cumulative history
    fixes:    Annotated[list[Fix],     operator.add]   # cumulative history
    ci_runs:  Annotated[list[CiRun],   operator.add]
    commits:  Annotated[list[str],     operator.add]   # commit SHAs

    # ── Per-iteration state (overwritten each iteration, NOT accumulated) ─
    # These hold only the CURRENT iteration's findings so nodes don't
    # re-process already-fixed issues from previous iterations.
    current_iteration_failures: list[Failure]   # set by failure_classifier
    current_iteration_fixes:    list[Fix]        # set by fix_generator + patch_applier

    # ── Agent-level errors (tool failures, infra errors — not code bugs) ─
    agent_errors: Annotated[list[str], operator.add]

    # ── Iteration control ─────────────────────────────────
    current_iteration: int
    final_status: Optional[str]             # RunStatus value

    # ── PR + git output ───────────────────────────────────
    pr_url: Optional[str]

    # ── Timing ────────────────────────────────────────────
    start_time: Optional[str]               # ISO timestamp
    end_time: Optional[str]
    total_time_seconds: Optional[float]

    # ── Score ─────────────────────────────────────────────
    score: Optional[ScoreCard]

    # ── Skip / no-op reason ──────────────────────────────────
    # Set by nodes when they cannot act (unsupported language,
    # no failures found, tooling unavailable, etc.).
    # finalize() promotes final_status → NO_ISSUES when this is set
    # and no fixes were applied.
    skip_reason: Optional[str]

    # ── Observer callback (not serialized) ────────────────
    # Lets backend receive real-time node events for SSE streaming
    observer: Optional[object]


# ── Computed helpers on state dict ────────────────────────

def get_total_failures(state: AgentState) -> int:
    return len(state.get("failures", []))


def get_total_fixes_applied(state: AgentState) -> int:
    return len([f for f in state.get("fixes", []) if f.status == FixStatus.FIXED])


def build_initial_state(
    repo_url: str,
    branch_prefix: str = "",
    github_token: Optional[str] = None,
    max_iterations: int = 5,
    read_only: bool = False,
    observer=None,
) -> AgentState:
    """
    Factory function — call this in orchestrator.py to seed a clean state.
    """
    return AgentState(
        # Inputs
        repo_url=repo_url,
        branch_prefix=branch_prefix,
        github_token=github_token,
        max_iterations=max_iterations,
        read_only=read_only,

        # Repo context
        repo_local_path=None,
        repo_owner=None,
        repo_name=None,
        branch_name=None,
        default_branch="main",

        # Language
        primary_language=None,
        detected_languages=[],
        has_tests=False,
        test_files=[],
        source_files=[],

        # Test output
        test_output=None,
        test_passed=False,
        static_analysis_output=None,

        # Findings
        failures=[],
        fixes=[],
        ci_runs=[],
        commits=[],

        # Per-iteration (reset each loop)
        current_iteration_failures=[],
        current_iteration_fixes=[],

        # Agent-level errors
        agent_errors=[],

        # Control
        current_iteration=1,
        final_status=None,
        skip_reason=None,

        # Git
        pr_url=None,

        # Timing
        start_time=datetime.now(timezone.utc).isoformat(),
        end_time=None,
        total_time_seconds=None,

        # Score
        score=ScoreCard(),

        # Observer
        observer=observer,
    )
