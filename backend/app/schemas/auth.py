# backend/app/schemas/auth.py
"""Pydantic response schemas for auth endpoints."""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel


class UserResponse(BaseModel):
    id:                 int
    github_id:          int
    github_username:    str
    github_email:       Optional[str]  = None
    github_avatar_url:  Optional[str]  = None
    created_at:         str
    last_login_at:      Optional[str]  = None


class LogoutResponse(BaseModel):
    message: str = "Logged out successfully"
