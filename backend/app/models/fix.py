# backend/app/models/fix.py

from sqlalchemy import String, Integer, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from datetime import datetime
from sqlalchemy import DateTime
from app.db.database import Base


class Fix(Base):
    __tablename__ = "fixes"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    run_id: Mapped[int] = mapped_column(
        ForeignKey("runs.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Fix details — maps exactly to PS dashboard table columns
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    bug_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    # LINTING | SYNTAX | LOGIC | TYPE_ERROR | IMPORT | INDENTATION
    line_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    commit_message: Mapped[str | None] = mapped_column(String(512), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    # FIXED | FAILED

    # Diff context
    diff: Mapped[str | None] = mapped_column(Text, nullable=True)
    before_snippet: Mapped[str | None] = mapped_column(Text, nullable=True)
    after_snippet: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationship
    run: Mapped["Run"] = relationship("Run", back_populates="fixes")

    def __repr__(self) -> str:
        return f"<Fix {self.bug_type} {self.file_path}:{self.line_number} {self.status}>"
