"""
Custom exception classes and global exception handlers for FastAPI.
"""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse


# ── Domain Exceptions ─────────────────────────────────────────────────────────

class AppException(Exception):
    """Base application exception."""
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    detail: str = "An unexpected error occurred."

    def __init__(self, detail: str | None = None):
        if detail:
            self.detail = detail
        super().__init__(self.detail)


class NotFoundError(AppException):
    status_code = status.HTTP_404_NOT_FOUND
    detail = "Resource not found."


class AlreadyExistsError(AppException):
    status_code = status.HTTP_409_CONFLICT
    detail = "Resource already exists."


class AuthenticationError(AppException):
    status_code = status.HTTP_401_UNAUTHORIZED
    detail = "Authentication failed."


class AuthorizationError(AppException):
    status_code = status.HTTP_403_FORBIDDEN
    detail = "You do not have permission to perform this action."


class ValidationError(AppException):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    detail = "Validation error."


class VectorStoreError(AppException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    detail = "Vector store operation failed."


class LLMError(AppException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    detail = "LLM service error."


class EmbeddingError(AppException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    detail = "Embedding service error."


# ── Exception Handlers ────────────────────────────────────────────────────────

import traceback
from app.core.logging import get_logger

logger = get_logger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    """Register all custom exception handlers on the FastAPI app."""

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail, "type": type(exc).__name__},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        tb = traceback.format_exc()
        logger.error(
            "Unhandled exception occurred",
            url=str(request.url),
            method=request.method,
            error_type=type(exc).__name__,
            error=str(exc),
            traceback=tb,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error.", "type": "InternalServerError"},
        )
