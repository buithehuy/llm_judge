"""
app/models/evaluation_request.py
─────────────────────────────────
SQLAlchemy ORM model for EvaluationRequest — the core input entity.
"""

import enum
import uuid

from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ContentType(str, enum.Enum):
    """
    Type of content being evaluated.

    Using ``str`` as mixin allows Pydantic to serialize the enum value
    directly as a string without extra configuration.
    """

    ESSAY = "ESSAY"
    CODE = "CODE"
    QA = "QA"
    GENERAL = "GENERAL"


class EvaluationStatus(str, enum.Enum):
    """
    Lifecycle status of an evaluation request.

    State machine:
        PENDING → PROCESSING → COMPLETED
                             ↘ FAILED
    """

    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class EvaluationRequest(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    Represents a single evaluation job submitted by a user.

    The ``content`` field holds the raw text to be evaluated (essay, code, etc.).
    The ``rubric`` field holds optional grading criteria in plain text or JSON string.
    """

    __tablename__ = "evaluation_requests"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Owner of this evaluation request",
    )
    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Short descriptive title for this evaluation",
    )
    content_type: Mapped[ContentType] = mapped_column(
        Enum(ContentType, name="content_type_enum"),
        nullable=False,
        comment="Type of content to evaluate",
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="The raw content (essay text, code snippet, Q&A pair, etc.)",
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

    # ─── Relationships ──────────────────────────────────────────────────────────
    user: Mapped["User"] = relationship(  # noqa: F821
        "User",
        back_populates="evaluation_requests",
    )
    result: Mapped["EvaluationResult | None"] = relationship(  # noqa: F821
        "EvaluationResult",
        back_populates="request",
        uselist=False,  # one-to-one
    )

    def __repr__(self) -> str:
        return (
            f"<EvaluationRequest id={self.id} "
            f"type={self.content_type} status={self.status}>"
        )
