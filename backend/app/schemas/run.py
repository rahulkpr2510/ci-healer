# backend/app/schemas/run.py
"""
Pydantic v2 response schemas for agent run endpoints.
These enforce strict typing on all JSON responses returned by the backend.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# ── Enums (as literals for Pydantic v2) ────────────────────────────────────

RunStatus = str   # "RUNNING" | "PASSED" | "FAILED"
BugType   = str   # "LINTING" | "SYNTAX" | "LOGIC" | "TYPE_ERROR" | "IMPORT" | "INDENTATION"
FixStatus = str   # "FIXED" | "FAILED" | "SKIPPED"


# ── Sub-schemas ─────────────────────────────────────────────────────────────

class ScoreSchema(BaseModel):
    base_score:          int = Field(100, description="Starting score")
    speed_bonus:         int = Field(0,   description="+10 if run finished in <5 minutes")
    efficiency_penalty:  int = Field(0,   description="-2 per commit over the threshold")
    final_score:         int = Field(0,   description="base + speed_bonus - efficiency_penalty")


class TimingSchema(BaseModel):
    started_at:          Optional[str] = None
    finished_at:         Optional[str] = None
    total_time_seconds:  Optional[float] = None


class FixSchema(BaseModel):
    file:            str              = Field(..., description="Relative file path changed")
    bug_type:        BugType
    line_number:     Optional[int]    = None
    commit_message:  Optional[str]    = None
    status:          FixStatus


class CiEventSchema(BaseModel):
    iteration:        int
    status:           RunStatus
    iteration_label:  Optional[str]   = None
    ran_at:           Optional[str]   = None


# ── Start run ───────────────────────────────────────────────────────────────

class RunRequest(BaseModel):
    repo_url:       str
    branch_prefix:  str   = Field("", max_length=50, description="Optional branch name prefix (e.g. 'MyTeam'). Used to build branch: <prefix>_AI_Fix_N")
    max_iterations: int   = Field(5, ge=1, le=10, description="Max fix iterations (1–10)")
    read_only:      bool  = False


class RunStartResponse(BaseModel):
    run_id:  str
    status:  str = "RUNNING"
    message: str = "Agent run started"


# ── Get run detail ──────────────────────────────────────────────────────────

class RunDetailResponse(BaseModel):
    run_id:                  str
    repo_url:                str
    repo_owner:              str
    repo_name:               str
    team_name:               str
    team_leader:             str
    mode:                    str
    branch_name:             Optional[str] = None
    pr_url:                  Optional[str] = None
    final_status:            RunStatus
    total_failures_detected: int = 0
    total_fixes_applied:     int = 0
    total_commits:           int = 0
    iterations_used:         int = 0
    score:                   ScoreSchema
    timing:                  TimingSchema
    fixes:                   list[FixSchema]      = []
    ci_timeline:             list[CiEventSchema]  = []
    created_at:              str
    # Language & diagnostics (populated from results_json stored on Run)
    primary_language:        Optional[str]        = None
    detected_languages:      list[str]            = []
    agent_errors:            list[str]            = []
    iterations_run:          int                  = 0
    skip_reason:             Optional[str]        = None


# ── Run summary (used in lists) ─────────────────────────────────────────────

class RunSummarySchema(BaseModel):
    run_id:               str
    repo_owner:           str
    repo_name:            str
    repo_url:             str
    final_status:         RunStatus
    total_fixes_applied:  int         = 0
    final_score:          Optional[int] = None
    total_time_seconds:   Optional[float] = None
    started_at:           Optional[str]   = None
