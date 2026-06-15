import enum
import uuid

from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

class ContentType(str, enum.Enum):
    ESSAY = "ESSAY"
    CODE = "CODE"

class EvaluationStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESS = "PROCESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class EvaluationRequest(Base, TimestampMixin, UUIDPrimaryKeyMixin):
    __tablename__ = "evaluation_requests"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        Comment="Owner of this evluation request.",
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="A short title describing the evaluation request.",
    )

    content_type: Mapped[ContentType] = mapped_column(
        Enum(ContentType, name = "content_type_enum"),
        nullable=False,
        comment="Type of content being evaluated (e.g., ESSAY, CODE).",
    )

    rubric: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Optional grading rubric / criteria in plain text or JSON",
    )
    status: Mapped[EvaluationStatus] = mapped_column(
        Enum(EvaluationStatus, name="evaluation_status_enum"),
        nullable=False,
        default=EvaluationStatus.PENDING,
        index=True,
        comment="Current processing status",
    )

    # ─── Relationships ────────────────────────────────────────────────────────────
    user: Mapped["User"] = relationship("User", back_populates="evaluations_requested")
    result: Mapped["EvaluationResult | None"] = relationship("EvaluationResult", back_populates="request", uselist=False)

    def __repr__(self) -> str:
        return (
            f"<EvaluationRequest(id={self.id}"
            f"type={self.content_type} status={self.status}>"
        )
    
