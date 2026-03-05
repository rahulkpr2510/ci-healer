# ai-engine/api/schemas.py

from pydantic import BaseModel, Field
from typing import Optional


class EngineRunRequest(BaseModel):
    run_id: Optional[str] = None   # backend passes its own UUID for log correlation
    repo_url: str
    team_name:      str = Field(..., min_length=1, max_length=100)
    team_leader:    str = Field(..., min_length=1, max_length=100)
    github_token: Optional[str] = None
    max_iterations: int = Field(5, ge=1, le=10)
    read_only: bool = False


class FixResult(BaseModel):
    file: str
    bug_type: str
    line_number: Optional[int] = None
    commit_message: Optional[str] = None
    status: str          # FIXED | FAILED | SKIPPED


class CiRunResult(BaseModel):
    iteration: int
    status: str
    timestamp: str
    iteration_label: str


class ScoreResult(BaseModel):
    base_score: int
    speed_bonus: int
    efficiency_penalty: int
    final_score: int


class EngineRunResult(BaseModel):
    final_status: str
    branch_name: Optional[str] = None
    pr_url: Optional[str] = None
    total_failures: int
    total_fixes_applied: int
    total_commits: int
    total_time_seconds: Optional[float] = None
    skip_reason: Optional[str] = None   # set when final_status == NO_ISSUES
    primary_language: Optional[str] = None
    detected_languages: list[str] = []
    iterations_run: int = 1
    score: ScoreResult
    fixes: list[FixResult]
    ci_timeline: list[CiRunResult]
    agent_output: list[dict]
    agent_errors: list[str] = []   # tool-level errors (missing tools, timeouts, etc)
    results_json: Optional[dict] = None
