# backend/app/models/ci_event.py

from sqlalchemy import String, Integer, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from datetime import datetime
from app.db.database import Base


class CiEvent(Base):
    __tablename__ = "ci_events"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    run_id: Mapped[int] = mapped_column(
        ForeignKey("runs.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Per-iteration CI data — maps to PS timeline requirements
    iteration: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # PASSED | FAILED
    iteration_label: Mapped[str | None] = mapped_column(String(20), nullable=True)  # e.g. "3/5"

    # Timestamp of this CI run
    ran_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationship
    run: Mapped["Run"] = relationship("Run", back_populates="ci_events")

    def __repr__(self) -> str:
        return f"<CiEvent iteration={self.iteration} status={self.status}>"
