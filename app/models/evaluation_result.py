"""
app/models/evaluation_result.py
────────────────────────────────
SQLAlchemy ORM model for EvaluationResult — the structured output of the judge.
"""

import uuid

from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class EvaluationResult(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    Stores the structured evaluation output from the Multi-Agent judge pipeline.

    Design decisions:
    - ``score`` and ``max_score`` are Float to support partial credit (e.g., 8.5/10).
    - ``feedback`` is JSON to allow rich, structured critique from the LLM.
    - ``detailed_scores`` is JSON to store per-criterion scores (rubric breakdown).
    - ``agent_trace`` is JSON to store the full LangGraph execution trace for
      auditability and debugging (critical for a judge system).
    - ``processing_time_ms`` enables performance monitoring and SLA tracking.
    """

    __tablename__ = "evaluation_results"

    request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evaluation_requests.id", ondelete="CASCADE"),
        unique=True,           # Enforces one-to-one at DB level
        nullable=False,
        index=True,
        comment="The evaluation request this result belongs to",
    )

    # ─── Scores ────────────────────────────────────────────────────────────────
    score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Achieved score (e.g., 8.5)",
    )
    max_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=10.0,
        comment="Maximum possible score (e.g., 10.0)",
    )

    # ─── Structured Output ─────────────────────────────────────────────────────
    feedback: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        comment="Rich structured feedback from the judge (summary, strengths, weaknesses)",
    )
    detailed_scores: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        comment="Per-criterion breakdown scores keyed by rubric criteria",
    )
    agent_trace: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        comment="Full LangGraph agent execution trace for auditability",
    )

    # ─── Metadata ──────────────────────────────────────────────────────────────
    model_used: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Name/version of the LLM model used for evaluation",
    )
    processing_time_ms: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Wall-clock time in milliseconds for the full evaluation pipeline",
    )

    # ─── Relationships ──────────────────────────────────────────────────────────
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
