"""
app/services/evaluation_service.py
────────────────────────────────────
Business logic for EvaluationRequest and EvaluationResult operations.

Pattern: Service Layer + Repository Pattern hybrid — the service owns
business rules (e.g., "cannot update a COMPLETED request") while
delegating raw DB queries to SQLAlchemy expressions.
"""

import uuid
from typing import Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.evaluation_request import EvaluationRequest, EvaluationStatus
from app.models.evaluation_result import EvaluationResult
from app.schemas.evaluation_request import EvaluationRequestCreate, EvaluationRequestUpdate
from app.schemas.evaluation_result import EvaluationResultCreate


class EvaluationService:
    """
    Service class for managing evaluation requests and their results.
    """

    # ─── EvaluationRequest Methods ─────────────────────────────────────────────

    async def create_request(
        self,
        db: AsyncSession,
        request_in: EvaluationRequestCreate,
        user_id: uuid.UUID,
    ) -> EvaluationRequest:
        """
        Create a new evaluation request in PENDING state.

        Args:
            db: Active async database session.
            request_in: Validated request creation data.
            user_id: UUID of the authenticated requesting user.

        Returns:
            The newly created EvaluationRequest ORM object.
        """
        eval_request = EvaluationRequest(
            user_id=user_id,
            title=request_in.title,
            content_type=request_in.content_type,
            content=request_in.content,
            rubric=request_in.rubric,
            status=EvaluationStatus.PENDING,
        )
        db.add(eval_request)
        await db.flush()
        await db.refresh(eval_request)
        return eval_request

    async def get_request_by_id(
        self, db: AsyncSession, request_id: uuid.UUID
    ) -> Optional[EvaluationRequest]:
        """
        Retrieve a single evaluation request by ID, eagerly loading its result.

        Uses ``selectinload`` (separate IN query) over ``joinedload`` to avoid
        Cartesian product issues when the result relationship is optional.

        Args:
            db: Active async database session.
            request_id: UUID of the request.

        Returns:
            EvaluationRequest with result pre-loaded, or None.
        """
        stmt = (
            select(EvaluationRequest)
            .where(EvaluationRequest.id == request_id)
            .options(selectinload(EvaluationRequest.result))
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_requests(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
        status_filter: Optional[EvaluationStatus] = None,
    ) -> Tuple[list[EvaluationRequest], int]:
        """
        Paginated list of a user's evaluation requests.

        Args:
            db: Active async database session.
            user_id: Filter requests to this user only.
            page: 1-indexed page number.
            page_size: Items per page.
            status_filter: Optional status filter (e.g., show only PENDING).

        Returns:
            Tuple of (list of EvaluationRequest objects, total count).
        """
        base_query = select(EvaluationRequest).where(
            EvaluationRequest.user_id == user_id
        )
        if status_filter is not None:
            base_query = base_query.where(EvaluationRequest.status == status_filter)

        # Count total matching records (without pagination)
        count_stmt = select(func.count()).select_from(base_query.subquery())
        total: int = (await db.execute(count_stmt)).scalar_one()

        # Fetch paginated page
        offset = (page - 1) * page_size
        items_stmt = (
            base_query.order_by(EvaluationRequest.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        rows = await db.execute(items_stmt)
        items = list(rows.scalars().all())

        return items, total

    async def update_request(
        self,
        db: AsyncSession,
        eval_request: EvaluationRequest,
        update_in: EvaluationRequestUpdate,
    ) -> EvaluationRequest:
        """
        Update an evaluation request's mutable fields.

        Business rule: Cannot update a COMPLETED or FAILED request.

        Args:
            db: Active async database session.
            eval_request: The existing EvaluationRequest ORM object.
            update_in: Partial update data (PATCH semantics).

        Returns:
            The updated EvaluationRequest ORM object.

        Raises:
            ValueError: If the request is in a terminal state.
        """
        if eval_request.status in (EvaluationStatus.COMPLETED, EvaluationStatus.FAILED):
            raise ValueError(
                f"Cannot update request in terminal state '{eval_request.status.value}'."
            )

        update_data = update_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(eval_request, field, value)

        db.add(eval_request)
        await db.flush()
        await db.refresh(eval_request)
        return eval_request

    async def update_status(
        self,
        db: AsyncSession,
        eval_request: EvaluationRequest,
        new_status: EvaluationStatus,
    ) -> EvaluationRequest:
        """
        Update only the status field of an evaluation request.

        This is called internally by the agent pipeline when transitioning states.

        Args:
            db: Active async database session.
            eval_request: The request whose status will change.
            new_status: The new status to set.

        Returns:
            The updated EvaluationRequest ORM object.
        """
        eval_request.status = new_status
        db.add(eval_request)
        await db.flush()
        await db.refresh(eval_request)
        return eval_request

    # ─── EvaluationResult Methods ───────────────────────────────────────────────

    async def save_result(
        self,
        db: AsyncSession,
        result_in: EvaluationResultCreate,
    ) -> EvaluationResult:
        """
        Persist the structured evaluation result from the agent pipeline.

        Automatically transitions the parent request to COMPLETED status.

        Args:
            db: Active async database session.
            result_in: Structured result data from the judge agent.

        Returns:
            The newly created EvaluationResult ORM object.

        Raises:
            ValueError: If the associated request is not found or already has a result.
        """
        # Validate the parent request exists
        eval_request = await self.get_request_by_id(db, result_in.request_id)
        if eval_request is None:
            raise ValueError(f"EvaluationRequest '{result_in.request_id}' not found.")
        if eval_request.result is not None:
            raise ValueError(
                f"Result already exists for request '{result_in.request_id}'."
            )

        # Persist the result
        result = EvaluationResult(
            request_id=result_in.request_id,
            score=result_in.score,
            max_score=result_in.max_score,
            feedback=result_in.feedback,
            detailed_scores=result_in.detailed_scores,
            agent_trace=result_in.agent_trace,
            model_used=result_in.model_used,
            processing_time_ms=result_in.processing_time_ms,
        )
        db.add(result)

        # Transition request status to COMPLETED
        eval_request.status = EvaluationStatus.COMPLETED
        db.add(eval_request)

        await db.flush()
        await db.refresh(result)
        return result

    async def get_result_by_request_id(
        self, db: AsyncSession, request_id: uuid.UUID
    ) -> Optional[EvaluationResult]:
        """
        Retrieve the evaluation result for a specific request.

        Args:
            db: Active async database session.
            request_id: UUID of the parent evaluation request.

        Returns:
            EvaluationResult ORM object, or None if not yet evaluated.
        """
        stmt = select(EvaluationResult).where(
            EvaluationResult.request_id == request_id
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()


# Module-level singleton
evaluation_service = EvaluationService()
