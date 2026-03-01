# ai-engine/api/schemas.py

from pydantic import BaseModel
from typing import Optional


class EngineRunRequest(BaseModel):
    run_id: Optional[str] = None   # backend passes its own UUID for log correlation
    repo_url: str
    team_name: str
    team_leader: str
    github_token: Optional[str] = None
    max_iterations: int = 5
    read_only: bool = False


class FixResult(BaseModel):
    file: str
    bug_type: str
    line_number: int
    commit_message: str
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
    score: ScoreResult
    fixes: list[FixResult]
    ci_timeline: list[CiRunResult]
    agent_output: list[dict]
    results_json: Optional[dict] = None
