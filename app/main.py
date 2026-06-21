"""
app/main.py
────────────
FastAPI application entry point.

Responsibilities:
1. Create and configure the FastAPI app instance.
2. Register CORS middleware.
3. Mount all API routers with versioned prefix.
4. Define startup/shutdown lifecycle events (DB table creation for dev).
5. Add root health check endpoint.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.db.base import Base
from app.db.session import engine
from app.routers import auth, evaluations, users

# Import all models so Alembic/SQLAlchemy sees them in metadata
import app.models.user  # noqa: F401
import app.models.evaluation_request  # noqa: F401
import app.models.evaluation_result  # noqa: F401


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager (startup/shutdown).

    On startup:
      - In DEBUG mode, auto-creates all tables (convenient for development).
      - In production, Alembic migrations should be used instead.

    On shutdown:
      - Disposes the connection pool gracefully.
    """
    # ─── Startup ───────────────────────────────────────────────────────────────
    if settings.DEBUG:
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
        except Exception as e:
            import logging
            logging.warning(
                f"[lifespan] Could not connect to database on startup: {e}\n"
                "Server will still start. Ensure PostgreSQL is running before making API calls."
            )

    yield  # Application runs here

    # ─── Shutdown ──────────────────────────────────────────────────────────────
    await engine.dispose()


def create_application() -> FastAPI:
    """
    Factory function that creates and configures the FastAPI application.

    Using a factory pattern (instead of module-level instantiation) makes
    it easy to create test instances with different configurations.

    Returns:
        Configured FastAPI application instance.
    """
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=(
            "**LLM-as-a-Judge** — Multi-Agent Evaluation & Auto-Grader Platform.\n\n"
            "Submit essays, code snippets, or Q&A pairs for structured AI evaluation "
            "using a LangGraph Multi-Agent pipeline with RAG-powered rubric retrieval."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # ─── CORS ──────────────────────────────────────────────────────────────────
    # "null" origin xuất hiện khi mở file HTML trực tiếp (file:// protocol).
    # Thêm vào để frontend hoạt động ngay mà không cần HTTP server riêng.
    dev_origins = [
        "null",                      # file:// protocol (mở HTML trực tiếp)
        "http://localhost",
        "http://localhost:3000",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://localhost:8080",
    ]
    allowed_origins = list(set(settings.CORS_ORIGINS + dev_origins)) if settings.DEBUG else settings.CORS_ORIGINS or ["*"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_origin_regex=r"http://localhost:\d+" if settings.DEBUG else None,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ─── Routers ───────────────────────────────────────────────────────────────
    API_PREFIX = "/api/v1"
    app.include_router(auth.router, prefix=API_PREFIX)
    app.include_router(users.router, prefix=API_PREFIX)
    app.include_router(evaluations.router, prefix=API_PREFIX)

    # ─── Health Check ──────────────────────────────────────────────────────────
    @app.get("/health", tags=["Health"], summary="Health check")
    async def health_check() -> dict:
        """
        Simple health check endpoint for load balancers and monitoring.

        Returns 200 OK when the application is running.
        """
        return {
            "status": "healthy",
            "app": settings.APP_NAME,
            "version": settings.APP_VERSION,
        }

    return app


app = create_application()
