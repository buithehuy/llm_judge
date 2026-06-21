"""
app/routers/auth.py
───────────────────
Authentication endpoints: register and login.

Uses OAuth2PasswordRequestForm for the login endpoint to be compatible
with standard OAuth2 clients and Swagger UI's built-in auth flow.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.db.session import get_db
from app.schemas.common import TokenResponse
from app.schemas.user import UserCreate, UserResponse
from app.services.user_service import user_service

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
)
async def register(
    user_in: UserCreate,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """
    Register a new user account.

    - **email**: Must be unique across the platform.
    - **password**: Minimum 8 characters. Stored as a bcrypt hash.
    - **full_name**: Optional display name.

    Returns the created user profile (no password in response).
    """
    try:
        user = await user_service.create(db, user_in)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )
    return UserResponse.model_validate(user)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login and receive a JWT access token",
)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """
    Authenticate with email and password.

    Uses OAuth2 Password Flow (``application/x-www-form-urlencoded``):
    - **username**: Your registered email address.
    - **password**: Your account password.

    Returns a Bearer JWT token. Include it in subsequent requests as:
    ``Authorization: Bearer <token>``
    """
    user = await user_service.authenticate(db, form_data.username, form_data.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated.",
        )

    access_token = create_access_token(subject=str(user.id))
    return TokenResponse(access_token=access_token)
