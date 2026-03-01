# ai-engine/engine/config.py

import re
import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from typing import Optional


class EngineSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── LLM Provider ─────────────────────────────────────
    # "groq"   → Groq API (free tier, very fast, recommended)
    # "gemini" → Google Gemini API
    LLM_PROVIDER: str = "groq"

    # ── Groq (free tier — https://console.groq.com) ───────
    # Models: llama-3.3-70b-versatile, llama-3.1-8b-instant,
    #         deepseek-r1-distill-llama-70b, mixtral-8x7b-32768
    GROQ_API_KEY: Optional[str] = None
    GROQ_MODEL: str = "llama-3.3-70b-versatile"

    # ── Gemini (fallback) ─────────────────────────────────
    GOOGLE_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-2.5-flash"

    # ── Shared LLM settings ───────────────────────────────
    LLM_TEMPERATURE: float = 0.2       # low = more deterministic fixes
    LLM_MAX_TOKENS: int = 8192

    # ── Agent behaviour ───────────────────────────────────
    DEFAULT_MAX_ITERATIONS: int = 5
    RETRY_LIMIT: int = 5
    SPEED_BONUS_THRESHOLD_SECONDS: int = 300   # 5 min → +10 pts
    EFFICIENCY_PENALTY_THRESHOLD: int = 20     # >20 commits → -2 per extra

    # ── Git ───────────────────────────────────────────────
    GIT_AUTHOR_NAME: str = "CI Healer Agent"
    GIT_AUTHOR_EMAIL: str = "agent@cihealer.dev"
    GIT_COMMIT_PREFIX: str = "[AI-AGENT]"

    # ── Workspace ─────────────────────────────────────────
    WORKSPACE_DIR: str = "/workspace"

    # ── Internal API ──────────────────────────────────────
    ENGINE_HOST: str = "0.0.0.0"
    ENGINE_PORT: int = 8001

    @field_validator("LLM_PROVIDER", mode="before")
    @classmethod
    def validate_provider(cls, v: str) -> str:
        v = v.strip().lower()
        if v not in ("groq", "gemini"):
            raise ValueError("LLM_PROVIDER must be 'groq' or 'gemini'")
        return v

    def validate_keys(self) -> None:
        """Call once at startup to ensure the active provider has a valid key."""
        if self.LLM_PROVIDER == "groq":
            if not self.GROQ_API_KEY or self.GROQ_API_KEY == "your_groq_api_key_here":
                raise ValueError(
                    "GROQ_API_KEY is not set. Get a free key at https://console.groq.com "
                    "then set it in ai-engine/.env"
                )
        else:
            if not self.GOOGLE_API_KEY or self.GOOGLE_API_KEY == "your_google_api_key_here":
                raise ValueError(
                    "GOOGLE_API_KEY is not set. Get a free key at https://aistudio.google.com"
                )

    @property
    def workspace_path(self) -> str:
        """Absolute path, expands ~ for local dev."""
        return os.path.expanduser(self.WORKSPACE_DIR)

    @property
    def active_model(self) -> str:
        return self.GROQ_MODEL if self.LLM_PROVIDER == "groq" else self.GEMINI_MODEL


engine_settings = EngineSettings()


# ── LLM factory ───────────────────────────────────────────
# Returns a LangChain chat model based on LLM_PROVIDER.
# All nodes import `llm` or call `get_llm()` — provider is transparent.

def get_llm(temperature: float | None = None):
    t = temperature if temperature is not None else engine_settings.LLM_TEMPERATURE

    if engine_settings.LLM_PROVIDER == "groq":
        if not engine_settings.GROQ_API_KEY:
            raise ValueError(
                "GROQ_API_KEY is not set. Get a free key at https://console.groq.com"
            )
        from langchain_groq import ChatGroq
        return ChatGroq(
            model=engine_settings.GROQ_MODEL,
            groq_api_key=engine_settings.GROQ_API_KEY,
            temperature=t,
            max_tokens=engine_settings.LLM_MAX_TOKENS,
        )

    # gemini fallback
    if not engine_settings.GOOGLE_API_KEY:
        raise ValueError(
            "GOOGLE_API_KEY is not set. Get a free key at https://aistudio.google.com"
        )
    from langchain_google_genai import ChatGoogleGenerativeAI
    return ChatGoogleGenerativeAI(
        model=engine_settings.GEMINI_MODEL,
        google_api_key=engine_settings.GOOGLE_API_KEY,
        temperature=t,
        max_output_tokens=engine_settings.LLM_MAX_TOKENS,
        convert_system_message_to_human=True,
    )


# Lazy singleton — instantiated once on first import
llm = get_llm()


# ── Branch name formatter ─────────────────────────────────
# PS requirement: TEAM_NAME_LEADER_NAME_AI_Fix  (all caps, underscores)

def format_branch_name(team_name: str, leader_name: str) -> str:
    """
    Examples:
      "Slytherin", "Rahul Kapoor"  → SLYTHERIN_RAHUL_KAPOOR_AI_Fix
      "Code Warriors", "John Doe"  → CODE_WARRIORS_JOHN_DOE_AI_Fix
    """
    def sanitize(s: str) -> str:
        s = s.upper().strip()
        s = re.sub(r"[^A-Z0-9\s]", "", s)   # remove special chars
        s = re.sub(r"\s+", "_", s)           # spaces → underscores
        return s

    team = sanitize(team_name)
    leader = sanitize(leader_name)
    return f"{team}_{leader}_AI_Fix"


# ── Commit message builder ────────────────────────────────

def format_commit_message(bug_type: str, file_path: str, line: int, description: str) -> str:
    """
    Ensures every commit has the mandatory [AI-AGENT] prefix.
    Example: [AI-AGENT] Fix LINTING in src/utils.py:15 - remove unused import
    """
    prefix = engine_settings.GIT_COMMIT_PREFIX
    short_desc = description[:80] if len(description) > 80 else description
    return f"{prefix} Fix {bug_type} in {file_path}:{line} - {short_desc}"


# ── Score calculator ──────────────────────────────────────

def calculate_score(
    total_time_seconds: float,
    total_commits: int,
) -> dict:
    """
    PS scoring rules:
      Base:              100 pts
      Speed bonus:       +10 if completed in < 5 min
      Efficiency penalty: -2 per commit over 20
    """
    base = 100
    speed_bonus = 10 if total_time_seconds < engine_settings.SPEED_BONUS_THRESHOLD_SECONDS else 0
    extra_commits = max(0, total_commits - engine_settings.EFFICIENCY_PENALTY_THRESHOLD)
    penalty = extra_commits * 2
    return {
        "base_score": base,
        "speed_bonus": speed_bonus,
        "efficiency_penalty": penalty,
        "final_score": max(0, base + speed_bonus - penalty),
    }
