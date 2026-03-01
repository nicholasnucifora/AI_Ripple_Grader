from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Assignment(Base):
    __tablename__ = "assignments"

    id: Mapped[int] = mapped_column(primary_key=True)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    marking_criteria: Mapped[str] = mapped_column(Text, nullable=False, default="")
    strictness: Mapped[str] = mapped_column(
        String(16), nullable=False, default="standard"
    )  # "lenient" | "standard" | "strict"
    created_by: Mapped[str] = mapped_column(
        ForeignKey("users.user_id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    class_: Mapped["Class"] = relationship("Class", back_populates="assignments")  # noqa: F821
    submissions: Mapped[list["Submission"]] = relationship(  # noqa: F821
        "Submission", back_populates="assignment", cascade="all, delete-orphan"
    )
