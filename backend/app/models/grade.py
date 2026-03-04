from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class GradingJob(Base):
    __tablename__ = "grading_jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    assignment_id: Mapped[int] = mapped_column(
        ForeignKey("assignments.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued")
    total: Mapped[int] = mapped_column(nullable=False, default=0)
    graded: Mapped[int] = mapped_column(nullable=False, default=0)
    errors: Mapped[int] = mapped_column(nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    assignment: Mapped["Assignment"] = relationship("Assignment")  # noqa: F821


class GradeResult(Base):
    __tablename__ = "grade_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    assignment_id: Mapped[int] = mapped_column(
        ForeignKey("assignments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    ripple_resource_id: Mapped[int] = mapped_column(
        ForeignKey("ripple_resources.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    criterion_grades: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    overall_feedback: Mapped[str] = mapped_column(Text, nullable=False, default="")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    graded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    assignment: Mapped["Assignment"] = relationship("Assignment")  # noqa: F821
    ripple_resource: Mapped["RippleResource"] = relationship("RippleResource")  # noqa: F821

    __table_args__ = (
        UniqueConstraint("assignment_id", "ripple_resource_id", name="uq_grade_result_assignment_resource"),
    )
