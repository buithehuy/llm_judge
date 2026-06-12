"""
app/db/base.py
──────────────
SQLAlchemy declarative base and common mixin classes.

Pattern: Mixin-based model design — các field chung (id, timestamps) được tách
vào Mixin riêng, giúp các ORM model kế thừa không bị lặp code.

"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """
    SQLAlchemy declarative base class.

    Tất cả ORM models đều kế thừa từ đây để Alembic có thể auto-detect
    schema changes thông qua `target_metadata`.
    """

    pass


class TimestampMixin:
    """
    Mixin that adds ``created_at`` and ``updated_at`` timestamp columns.

    - ``created_at``: Set once at INSERT time via server-side DEFAULT.
    - ``updated_at``: Updated automatically on every UPDATE via onupdate trigger.

    Dùng ``func.now()`` thay vì Python's ``datetime.now()`` để đảm bảo
    timestamps được set bởi database server, tránh timezone drift.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class UUIDPrimaryKeyMixin:
    """
    Mixin that adds a UUID v4 primary key column named ``id``.

    Dùng UUID thay vì auto-increment integer để:
    1. Tránh lộ số lượng records trong URL (security).
    2. Dễ merge/replicate data giữa các environments (không conflict).
    3. ID có thể được generate ở client trước khi insert (offline-first).
    """

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
