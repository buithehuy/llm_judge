"""
app/schemas/evaluation_result.py
─────────────────────────────────
Pydantic v2 schemas for EvaluationResult entity.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class EvaluationResultCreate(BaseModel):
    """
    Input schema used internally by the Agent pipeline to save results.

    NOT exposed as a direct API input for end users — only the
    agent orchestrator calls this after completing evaluation.
    """

    request_id: uuid.UUID
    score: float = Field(ge=0.0, description="Achieved score")
    max_score: float = Field(gt=0.0, default=10.0, description="Maximum possible score")
    feedback: dict = Field(
        default_factory=dict,
        description="Structured feedback: {summary, strengths, weaknesses, suggestions}",
    )
    detailed_scores: dict = Field(
        default_factory=dict,
        description="Per-criterion scores: {criterion_name: score}",
    )
    agent_trace: dict = Field(
        default_factory=dict,
        description="Full LangGraph execution trace for audit purposes",
    )
    model_used: str = Field(
        max_length=100,
        description="Model identifier (e.g., 'gpt-4o-2024-11-20')",
    )
    processing_time_ms: int = Field(
        ge=0,
        description="Total wall-clock processing time in milliseconds",
    )


class EvaluationResultResponse(BaseModel):
    """
    Full evaluation result output schema.

    Includes computed properties like ``score_percentage`` for frontend convenience.
    """

    id: uuid.UUID
    request_id: uuid.UUID
    score: float
    max_score: float
    score_percentage: float = Field(
        description="Score as a percentage of max_score (computed)"
    )
    feedback: dict
    detailed_scores: dict
    agent_trace: dict
    model_used: str
    processing_time_ms: int
    created_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_with_percentage(
        cls, result: "EvaluationResult"  # noqa: F821
    ) -> "EvaluationResultResponse":
        """
        Factory method that computes ``score_percentage`` from ORM object.

        Args:
            result: An EvaluationResult ORM instance.

        Returns:
            A fully populated EvaluationResultResponse schema.
        """
        data = cls.model_validate(result)
        data.score_percentage = round((result.score / result.max_score) * 100, 2)
        return data
