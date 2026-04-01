"""FastAPI application entry point for CareSync API."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

import app.models
from app.core.config import settings
from app.core.exception_handlers import register_exception_handlers
from app.core.logging_config import RequestLoggingMiddleware, setup_logging
from app.routers import auth, doses, medications, patients, reports
from app.scheduler.scheduler import scheduler, setup_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: setup on start, cleanup on shutdown."""
    setup_logging()
    logger = structlog.get_logger(__name__)
    logger.info(
        "application_started",
        app_name=settings.app_name,
        environment=settings.environment,
    )
    if settings.enable_scheduler:
        setup_scheduler()
        scheduler.start()
        logger.info("scheduler_started", jobs=len(scheduler.get_jobs()))
    else:
        logger.info("scheduler_disabled")
    yield
    if settings.enable_scheduler:
        scheduler.shutdown()
    logger.info("application_shutdown")


def create_app() -> FastAPI:
    """Construct and configure the FastAPI application."""
    app = FastAPI(
        title=settings.app_name,
        description="REST API for managing medications of elderly patients in care homes.",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # -----------------------------------------------------------------------
    # Middleware (order matters: outermost is applied last)
    # -----------------------------------------------------------------------
    # allow_credentials must be False when allow_origins=["*"] — the combination
    # is rejected by browsers (and by Starlette >=0.36 at runtime). Bearer tokens
    # in the Authorization header are not "credentials" in the CORS sense.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(BaseHTTPMiddleware, dispatch=_security_headers_dispatch)
    app.add_middleware(RequestLoggingMiddleware)

    # -----------------------------------------------------------------------
    # Exception handlers
    # -----------------------------------------------------------------------
    register_exception_handlers(app)

    # -----------------------------------------------------------------------
    # Routers
    # -----------------------------------------------------------------------
    prefix = settings.api_v1_prefix
    app.include_router(auth.router, prefix=prefix)
    app.include_router(patients.router, prefix=prefix)
    app.include_router(medications.router, prefix=prefix)
    app.include_router(doses.router, prefix=prefix)
    app.include_router(reports.router, prefix=prefix)

    # -----------------------------------------------------------------------
    # Health check
    # -----------------------------------------------------------------------
    @app.get("/health", tags=["Ops"], summary="Health check")
    def health() -> JSONResponse:
        return JSONResponse({"status": "ok", "version": "0.1.0"})

    return app


async def _security_headers_dispatch(
    request: object,
    call_next: object,
) -> object:
    """Add basic security headers to every response."""
    from starlette.requests import Request
    from starlette.responses import Response

    assert isinstance(request, Request)
    response: Response = await call_next(request)  # type: ignore[misc, operator]
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


app = create_app()
