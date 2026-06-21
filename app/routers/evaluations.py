"""
app/routers/evaluations.py
───────────────────────────
Evaluation request management endpoints.

All endpoints require authentication. Users can only access their own requests
(enforced at service layer by filtering on user_id).
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_active_user
from app.db.session import get_db
from app.models.evaluation_request import EvaluationStatus
from app.models.user import User
from app.schemas.common import PagedResponse
from app.schemas.evaluation_request import (
    EvaluationRequestCreate,
    EvaluationRequestResponse,
    EvaluationRequestSummary,
    EvaluationRequestUpdate,
)
from app.schemas.evaluation_result import EvaluationResultResponse
from app.services.evaluation_service import evaluation_service

router = APIRouter(prefix="/evaluations", tags=["Evaluations"])


@router.post(
    "/",
    response_model=EvaluationRequestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a new evaluation request",
)
async def create_evaluation(
    request_in: EvaluationRequestCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> EvaluationRequestResponse:
    """
    Submit content for evaluation by the Multi-Agent judge pipeline.

    The request is created with status **PENDING**. The agent pipeline
    will pick it up asynchronously and update the status to PROCESSING,
    then COMPLETED (or FAILED).

    - **title**: Short description of what you're submitting.
    - **content_type**: ESSAY | CODE | QA | GENERAL
    - **content**: The raw text/code to be evaluated.
    - **rubric**: Optional grading criteria (plain text or JSON string).
    """
    eval_request = await evaluation_service.create_request(
        db, request_in, current_user.id
    )
    return EvaluationRequestResponse.model_validate(eval_request)


@router.get(
    "/",
    response_model=PagedResponse[EvaluationRequestSummary],
    summary="List my evaluation requests (paginated)",
)
async def list_evaluations(
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    status_filter: Optional[EvaluationStatus] = Query(
        default=None, alias="status", description="Filter by status"
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> PagedResponse[EvaluationRequestSummary]:
    """
    Retrieve a paginated list of the current user's evaluation requests.

    Results are ordered by ``created_at`` descending (newest first).
    Use the ``status`` query parameter to filter by lifecycle state.
    """
    items, total = await evaluation_service.list_requests(
        db,
        user_id=current_user.id,
        page=page,
        page_size=page_size,
        status_filter=status_filter,
    )
    total_pages = max(1, -(-total // page_size))  # Ceiling division

    return PagedResponse(
        items=[EvaluationRequestSummary.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get(
    "/{request_id}",
    response_model=EvaluationRequestResponse,
    summary="Get full details of an evaluation request",
)
async def get_evaluation(
    request_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> EvaluationRequestResponse:
    """
    Retrieve the full details of a specific evaluation request.

    Returns 403 if the request belongs to a different user (not 404,
    to avoid leaking whether the resource exists).
    """
    eval_request = await evaluation_service.get_request_by_id(db, request_id)
    if eval_request is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evaluation request '{request_id}' not found.",
        )
    if eval_request.user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this resource.",
        )
    return EvaluationRequestResponse.model_validate(eval_request)


@router.patch(
    "/{request_id}",
    response_model=EvaluationRequestResponse,
    summary="Update a PENDING evaluation request",
)
async def update_evaluation(
    request_id: uuid.UUID,
    update_in: EvaluationRequestUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> EvaluationRequestResponse:
    """
    Update a PENDING evaluation request (PATCH semantics — partial update).

    Requests in COMPLETED or FAILED state cannot be modified.
    """
    eval_request = await evaluation_service.get_request_by_id(db, request_id)
    if eval_request is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evaluation request '{request_id}' not found.",
        )
    if eval_request.user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to modify this resource.",
        )
    try:
        updated = await evaluation_service.update_request(db, eval_request, update_in)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )
    return EvaluationRequestResponse.model_validate(updated)


@router.get(
    "/{request_id}/result",
    response_model=EvaluationResultResponse,
    summary="Get the evaluation result for a request",
)
async def get_evaluation_result(
    request_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> EvaluationResultResponse:
    """
    Retrieve the grading result for a completed evaluation request.

    Returns 404 if the evaluation has not completed yet (result not available).
    Poll ``GET /evaluations/{id}`` to check the status before calling this.
    """
    # Verify the parent request exists and belongs to the user
    eval_request = await evaluation_service.get_request_by_id(db, request_id)
    if eval_request is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evaluation request '{request_id}' not found.",
        )
    if eval_request.user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this resource.",
        )

    result = await evaluation_service.get_result_by_request_id(db, request_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"Result not yet available for request '{request_id}'. "
                f"Current status: {eval_request.status.value}."
            ),
        )

    return EvaluationResultResponse.from_orm_with_percentage(result)
