"""
app/schemas/evaluation_request.py
──────────────────────────────────
Pydantic v2 schemas for EvaluationRequest entity.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.evaluation_request import ContentType, EvaluationStatus


class EvaluationRequestBase(BaseModel):
    """Fields common to all EvaluationRequest schemas."""

    title: str = Field(
        min_length=1,
        max_length=500,
        description="Short descriptive title for this evaluation",
    )
    content_type: ContentType = Field(
        description="Type of content: ESSAY | CODE"
    )
    content: str = Field(
        min_length=1,
        description="The raw content to be evaluated (essay text, code, etc.)",
    )
    rubric: str | None = Field(
        default=None,
        description="Optional grading rubric / scoring criteria",
    )


class EvaluationRequestCreate(EvaluationRequestBase):
    """
    Input schema for creating a new evaluation request.

    user_id is injected from the authenticated JWT — NOT from the request body —
    to prevent users from submitting requests on behalf of other users.
    """

    pass  # All fields inherited from Base


class EvaluationRequestUpdate(BaseModel):
    """
    Input schema for updating an evaluation request.

    Only PENDING requests can be updated (enforced at service layer).
    """

    title: str | None = Field(default=None, min_length=1, max_length=500)
    rubric: str | None = Field(default=None)
    status: EvaluationStatus | None = Field(default=None)


class EvaluationRequestResponse(EvaluationRequestBase):
    """Safe output schema with computed fields and relationship data."""

    id: uuid.UUID
    user_id: uuid.UUID
    status: EvaluationStatus
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class EvaluationRequestSummary(BaseModel):
    """
    Lightweight summary for list views — avoids sending full ``content`` text
    in paginated lists for performance.
    """

    id: uuid.UUID
    title: str
    content_type: ContentType
    status: EvaluationStatus
    created_at: datetime

    model_config = {"from_attributes": True}
