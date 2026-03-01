# backend/app/schemas/history.py
"""Pydantic response schemas for history and analytics endpoints."""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel

from app.schemas.run import RunSummarySchema


# ── History ──────────────────────────────────────────────────────────────────

class RepoHistoryResponse(BaseModel):
    owner:     str
    repo:      str
    total:     int
    page:      int
    page_size: int
    runs:      list[RunSummarySchema]


class AllHistoryResponse(BaseModel):
    runs: list[RunSummarySchema]


# ── Analytics ─────────────────────────────────────────────────────────────────

class AnalyticsSummarySchema(BaseModel):
    total_runs:        int   = 0
    passed:            int   = 0
    failed:            int   = 0
    pass_rate:         float = 0.0
    avg_time_seconds:  float = 0.0
    avg_score:         float = 0.0
    avg_fixes_per_run: float = 0.0
    total_fixes_ever:  int   = 0


class RepoAnalyticsResponse(BaseModel):
    owner:                 str
    repo:                  str
    summary:               AnalyticsSummarySchema
    bug_type_distribution: dict[str, int]         = {}
    recent_runs:           list[RunSummarySchema]  = []


class DashboardSummaryResponse(BaseModel):
    total_runs:          int         = 0
    unique_repos:        int         = 0
    total_fixes_applied: int         = 0
    pass_rate:           float       = 0.0
    repos:               list[str]   = []


# ── Repos ─────────────────────────────────────────────────────────────────────

class RepoSchema(BaseModel):
    id:             int
    full_name:      str
    owner:          str
    name:           str
    html_url:       str
    description:    Optional[str]  = None
    private:        bool           = False
    default_branch: str            = "main"
    updated_at:     Optional[str]  = None
    language:       Optional[str]  = None


class ReposResponse(BaseModel):
    repos: list[RepoSchema]
    count: int
