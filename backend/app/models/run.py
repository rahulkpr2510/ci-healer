# backend/app/models/run.py

from sqlalchemy import String, Integer, Float, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from datetime import datetime
from app.db.database import Base


class Run(Base):
    __tablename__ = "runs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    run_id: Mapped[str] = mapped_column(String(36), unique=True, index=True, nullable=False)  # UUID

    # Owner
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Repo identity — indexed for fast per-repo history queries
    repo_url: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    repo_owner: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    repo_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    # Run inputs
    team_name: Mapped[str] = mapped_column(String(255), nullable=False)
    team_leader: Mapped[str] = mapped_column(String(255), nullable=False)
    mode: Mapped[str] = mapped_column(String(50), default="run-agent", nullable=False)
    max_iterations: Mapped[int] = mapped_column(Integer, default=5, nullable=False)

    # Run outputs
    branch_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    pr_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    final_status: Mapped[str] = mapped_column(
        String(20), default="RUNNING", nullable=False, index=True
    )  # RUNNING | PASSED | FAILED

    # Counts
    total_failures_detected: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_fixes_applied: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_commits: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    iterations_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Score
    base_score: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    speed_bonus: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    efficiency_penalty: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    final_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Timing
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    total_time_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Full results blob (results.json stored as text)
    results_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="runs")
    fixes: Mapped[list["Fix"]] = relationship(
        "Fix", back_populates="run", cascade="all, delete-orphan"
    )
    ci_events: Mapped[list["CiEvent"]] = relationship(
        "CiEvent", back_populates="run", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Run {self.run_id} repo={self.repo_name} status={self.final_status}>"
