"""FastAPI exception handlers that map domain exceptions to HTTP responses."""

import structlog
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.exceptions import (
    ConflictError,
    DomainValidationError,
    ExternalServiceError,
    ForbiddenError,
    NotFoundError,
)

logger = structlog.get_logger(__name__)


def _error_body(code: str, message: str) -> dict[str, object]:
    return {"error": {"code": code, "message": message}}


def register_exception_handlers(app: FastAPI) -> None:
    """Register all domain exception handlers on the FastAPI application.

    Args:
        app: The FastAPI application instance.
    """

    @app.exception_handler(NotFoundError)
    async def not_found_handler(request: Request, exc: NotFoundError) -> JSONResponse:
        logger.info("not_found", path=request.url.path, detail=exc.message)
        return JSONResponse(
            status_code=404,
            content=_error_body("NOT_FOUND", exc.message),
        )

    @app.exception_handler(ConflictError)
    async def conflict_handler(request: Request, exc: ConflictError) -> JSONResponse:
        logger.info("conflict", path=request.url.path, detail=exc.message)
        return JSONResponse(
            status_code=409,
            content=_error_body("CONFLICT", exc.message),
        )

    @app.exception_handler(DomainValidationError)
    async def domain_validation_handler(request: Request, exc: DomainValidationError) -> JSONResponse:
        logger.info("domain_validation_error", path=request.url.path, detail=exc.message)
        return JSONResponse(
            status_code=422,
            content=_error_body("DOMAIN_VALIDATION_ERROR", exc.message),
        )

    @app.exception_handler(ForbiddenError)
    async def forbidden_handler(request: Request, exc: ForbiddenError) -> JSONResponse:
        logger.info("forbidden", path=request.url.path, detail=exc.message)
        return JSONResponse(
            status_code=403,
            content=_error_body("FORBIDDEN", exc.message),
        )

    @app.exception_handler(ExternalServiceError)
    async def external_service_handler(request: Request, exc: ExternalServiceError) -> JSONResponse:
        logger.warning("external_service_error", path=request.url.path, detail=exc.message)
        return JSONResponse(
            status_code=503,
            content=_error_body("EXTERNAL_SERVICE_ERROR", exc.message),
        )

    @app.exception_handler(Exception)
    async def generic_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled_exception", path=request.url.path, exc_info=exc)
        return JSONResponse(
            status_code=500,
            content=_error_body("INTERNAL_SERVER_ERROR", "An unexpected error occurred."),
        )
