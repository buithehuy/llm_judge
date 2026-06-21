"""
app/routers/users.py
─────────────────────
User profile management endpoints (requires authentication).
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_active_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import UserResponse, UserUpdate
from app.services.user_service import user_service

router = APIRouter(prefix="/users", tags=["Users"])


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile",
)
async def get_me(
    current_user: User = Depends(get_current_active_user),
) -> UserResponse:
    """
    Retrieve the profile of the currently authenticated user.

    No parameters needed — identity is determined from the JWT token.
    """
    return UserResponse.model_validate(current_user)


@router.put(
    "/me",
    response_model=UserResponse,
    summary="Update current user profile",
)
async def update_me(
    user_in: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> UserResponse:
    """
    Update the current user's profile (PATCH semantics).

    Only the fields you include in the request body will be updated.
    Omitting a field leaves it unchanged.

    - **full_name**: Update display name.
    - **password**: Change password (minimum 8 characters).
    """
    updated_user = await user_service.update(db, current_user, user_in)
    return UserResponse.model_validate(updated_user)
