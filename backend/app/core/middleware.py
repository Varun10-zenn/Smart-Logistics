"""
Middleware: Request ID injection and global error handlers.
"""
import uuid
import logging
import traceback
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Attach a unique request_id to every request and propagate it in responses."""

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


def _get_request_id(request: Request) -> str:
    return getattr(request.state, "request_id", str(uuid.uuid4()))


def _error_body(code: str, message: str, details, request_id: str) -> dict:
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details,
            "request_id": request_id,
        }
    }


def register_exception_handlers(app: FastAPI) -> None:
    """Register all global exception handlers on the FastAPI app."""

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        request_id = _get_request_id(request)
        detail = exc.detail

        # If the detail is already our structured dict, pass it through
        if isinstance(detail, dict) and "code" in detail:
            body = {
                "error": {
                    **detail,
                    "request_id": request_id,
                }
            }
        else:
            # Map common HTTP status codes to our error codes
            code_map = {
                400: "BAD_REQUEST",
                401: "UNAUTHORIZED",
                403: "FORBIDDEN",
                404: "NOT_FOUND",
                409: "CONFLICT",
                422: "VALIDATION_ERROR",
                500: "INTERNAL_ERROR",
                503: "SERVICE_UNAVAILABLE",
            }
            code = code_map.get(exc.status_code, "ERROR")
            body = _error_body(
                code=code,
                message=str(detail) if not isinstance(detail, dict) else str(detail),
                details={},
                request_id=request_id,
            )

        return JSONResponse(status_code=exc.status_code, content=body)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        request_id = _get_request_id(request)
        field_errors = []
        for error in exc.errors():
            loc = " -> ".join(str(l) for l in error.get("loc", []))
            field_errors.append({"field": loc, "issue": error.get("msg", "")})
        body = _error_body(
            code="VALIDATION_ERROR",
            message="Request validation failed.",
            details=field_errors,
            request_id=request_id,
        )
        return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=body)

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        request_id = _get_request_id(request)
        logger.error(f"[{request_id}] Unhandled exception: {exc}\n{traceback.format_exc()}")
        body = _error_body(
            code="INTERNAL_ERROR",
            message="An unexpected error occurred. Please try again later.",
            details={},
            request_id=request_id,
        )
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=body)
