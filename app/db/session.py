from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,       # Log SQL queries khi DEBUG=True
    pool_pre_ping=True,
    pool_size=10,              # Số kết nối thường trực trong pool
    max_overflow=20,           # Số kết nối bổ sung khi pool đầy
)

# ─── Session Factory ────────────────────────────────────────────────────────────
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,    # Quan trọng: tránh lỗi MissingGreenlet sau commit
    autocommit=False,
    autoflush=False,
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that yields an async database session.

    Sử dụng ``async with`` để đảm bảo session luôn được đóng sau khi request
    hoàn thành, kể cả khi có exception (RAII pattern).

    Yields:
        AsyncSession: An active SQLAlchemy async session.

    Example::

        @router.get("/items")
        async def list_items(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(Item))
            return result.scalars().all()
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()