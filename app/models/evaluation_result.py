import uuid

from sqlalchemy import ForeignKey, String, Text, Enum, Float, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSON

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

class EvaluationResult(Base, TimestampMixin, UUIDPrimaryKeyMixin):
    __tablename__ = "evaluation_results"

    request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evaluation_requests.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
        comment="The evaluation request this result belongs to.",
    )

    score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Achieved score (e.g., 8.5).",
    )

    feedback: Mapped[dict] = mapped_column(
        JSON,
        nullable = False,
        default = dict,
        comment="Per-criterion breakdown scores keyed by rubric criteria"
    )

    model_used: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        commment="Name/version of the evaluation model used (e.g., GPT-4).",
    )

    processing_time_ms: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Wall-clock time in milliseconds for the full evaluation pipeline",
    )

    request: Mapped["EvaluationRequest"] = relationship(  # noqa: F821
        "EvaluationRequest",
        back_populates="result",
    )

    def __repr__(self) -> str:
        return (
            f"<EvaluationResult id={self.id} "
            f"score={self.score}/{self.max_score} "
            f"model={self.model_used!r}>"
        )