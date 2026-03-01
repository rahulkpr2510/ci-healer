# ai-engine/engine/state.py

from typing import TypedDict, Optional, Annotated
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import operator


# ── Enums ─────────────────────────────────────────────────

class BugType(str, Enum):
    LINTING = "LINTING"
    SYNTAX = "SYNTAX"
    LOGIC = "LOGIC"
    TYPE_ERROR = "TYPE_ERROR"
    IMPORT = "IMPORT"
    INDENTATION = "INDENTATION"
    UNKNOWN = "UNKNOWN"


class FixStatus(str, Enum):
    FIXED = "FIXED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class RunStatus(str, Enum):
    RUNNING = "RUNNING"
    PASSED = "PASSED"
    FAILED = "FAILED"


class Language(str, Enum):
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    GO = "go"
    JAVA = "java"
    RUBY = "ruby"
    UNKNOWN = "unknown"


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
    team_name: str
    team_leader: str
    github_token: Optional[str]
    max_iterations: int
    read_only: bool

    # ── Repo context (set by repo_analyzer) ───────────────
    repo_local_path: Optional[str]          # abs path to cloned repo on disk
    repo_owner: Optional[str]
    repo_name: Optional[str]
    branch_name: Optional[str]              # TEAM_NAME_LEADER_NAME_AI_Fix
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
    failures: Annotated[list[Failure], operator.add]
    fixes: Annotated[list[Fix], operator.add]
    ci_runs: Annotated[list[CiRun], operator.add]
    commits: Annotated[list[str], operator.add]   # commit SHAs

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
    team_name: str,
    team_leader: str,
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
        team_name=team_name,
        team_leader=team_leader,
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

        # Control
        current_iteration=0,
        final_status=None,

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
