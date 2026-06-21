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
    if settings.DEBUG:
        try:
            # In debug mode, auto-create tables on startup for convenience.
            # In production, use proper migrations instead.
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
        except Exception as e:
            import logging
            logging.warning(
                f"[lifespan] Could not connect to database on startup: {e}\n"
                "Server will still start. Ensure PostgreSQL is running before making API calls."
            )
    yield

    await engine.dispose()

def create_application() -> FastAPI:
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

    # CORS middleware - adjust origins as needed for your frontend
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

