"""
app/core/dependencies.py
─────────────────────────
FastAPI dependency injection functions shared across routers.

Pattern: Dependency Injection via FastAPI's ``Depends()`` mechanism.
This keeps routers thin — they declare WHAT they need, not HOW to get it.
"""

import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User
from app.services.user_service import user_service

# OAuth2PasswordBearer extracts the Bearer token from the Authorization header.
# ``tokenUrl`` points to the login endpoint — used by Swagger UI's "Authorize" button.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Decode the JWT token and return the authenticated User ORM object.

    This is the primary authentication dependency. All protected routes
    that need the current user should declare ``Depends(get_current_user)``.

    Args:
        token: JWT string extracted from the ``Authorization: Bearer <token>`` header.
        db: Active async database session.

    Returns:
        The authenticated User ORM object.

    Raises:
        HTTPException(401): If the token is invalid, expired, or the user doesn't exist.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
        user_id_str: str | None = payload.get("sub")
        if user_id_str is None:
            raise credentials_exception
        user_id = uuid.UUID(user_id_str)
    except (JWTError, ValueError):
        raise credentials_exception

    user = await user_service.get_by_id(db, user_id)
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Ensure the current authenticated user is active (not soft-deleted/banned).

    Chain this after ``get_current_user`` for endpoints that require an active account.

    Args:
        current_user: User object from ``get_current_user``.

    Returns:
        The active User ORM object.

    Raises:
        HTTPException(403): If the user account is deactivated.
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated. Please contact support.",
        )
    return current_user


async def get_current_superuser(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """
    Ensure the current user has superuser (admin) privileges.

    Args:
        current_user: Active user from ``get_current_active_user``.

    Returns:
        The superuser User ORM object.

    Raises:
        HTTPException(403): If the user is not a superuser.
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions. Superuser access required.",
        )
    return current_user
