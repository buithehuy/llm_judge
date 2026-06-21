"""
app/services/user_service.py
─────────────────────────────
Business logic for User CRUD operations.

Pattern: Service Layer — tách biệt business logic khỏi router (HTTP layer)
và database (ORM layer). Router chỉ xử lý HTTP, Service xử lý business rules,
Model/DB xử lý persistence.
"""

import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate


class UserService:
    """
    Service class encapsulating all User-related business operations.

    Methods are ``async`` to support non-blocking database I/O.
    All methods receive a ``db`` session injected by FastAPI's DI system.
    """

    async def get_by_id(self, db: AsyncSession, user_id: uuid.UUID) -> Optional[User]:
        """
        Retrieve a user by their UUID primary key.

        Args:
            db: Active async database session.
            user_id: The UUID of the user to retrieve.

        Returns:
            The User ORM object, or None if not found.
        """
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_email(self, db: AsyncSession, email: str) -> Optional[User]:
        """
        Retrieve a user by their email address (case-insensitive lookup).

        Args:
            db: Active async database session.
            email: The email address to look up.

        Returns:
            The User ORM object, or None if not found.
        """
        result = await db.execute(
            select(User).where(User.email == email.lower().strip())
        )
        return result.scalar_one_or_none()

    async def create(self, db: AsyncSession, user_in: UserCreate) -> User:
        """
        Create a new user account.

        Performs email uniqueness check before insertion.
        Password is hashed before storage — plain text is NEVER persisted.

        Args:
            db: Active async database session.
            user_in: Validated user creation data.

        Returns:
            The newly created User ORM object.

        Raises:
            ValueError: If a user with the same email already exists.
        """
        # Check for duplicate email
        existing = await self.get_by_email(db, user_in.email)
        if existing is not None:
            raise ValueError(f"User with email '{user_in.email}' already exists.")

        user = User(
            email=user_in.email.lower().strip(),
            hashed_password=hash_password(user_in.password),
            full_name=user_in.full_name,
            is_active=True,
            is_superuser=False,
        )
        db.add(user)
        await db.flush()   # flush to get the generated UUID before commit
        await db.refresh(user)
        return user

    async def update(
        self, db: AsyncSession, user: User, user_in: UserUpdate
    ) -> User:
        """
        Update a user's profile fields.

        Applies only the fields that were explicitly set in the request
        (PATCH semantics via ``exclude_unset=True``).

        Args:
            db: Active async database session.
            user: The existing User ORM object to update.
            user_in: Validated partial update data.

        Returns:
            The updated User ORM object.
        """
        update_data = user_in.model_dump(exclude_unset=True)

        # Hash new password if provided
        if "password" in update_data:
            update_data["hashed_password"] = hash_password(update_data.pop("password"))

        for field, value in update_data.items():
            setattr(user, field, value)

        db.add(user)
        await db.flush()
        await db.refresh(user)
        return user

    async def authenticate(
        self, db: AsyncSession, email: str, password: str
    ) -> Optional[User]:
        """
        Verify email/password credentials and return the user if valid.

        Returns None (not raises) on failure to prevent timing oracle attacks
        when differentiating "user not found" vs "wrong password".

        Args:
            db: Active async database session.
            email: The user's email.
            password: The plain-text password to verify.

        Returns:
            The authenticated User object, or None if credentials are invalid.
        """
        user = await self.get_by_email(db, email)
        if user is None:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user


# Module-level singleton (stateless, safe to share)
user_service = UserService()
