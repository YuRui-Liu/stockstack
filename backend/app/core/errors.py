from typing import Any
from uuid import UUID, uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class AppError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int,
        field_errors: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.field_errors = field_errors or {}


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", str(uuid4()))


def _response(request: Request, error: AppError) -> JSONResponse:
    request_id = _request_id(request)
    return JSONResponse(
        status_code=error.status_code,
        content={
            "code": error.code,
            "message": error.message,
            "field_errors": error.field_errors,
            "request_id": request_id,
        },
        headers={"X-Request-ID": request_id},
    )


def _valid_request_id(value: str | None) -> bool:
    if not value or len(value) > 128:
        return False
    return all(character.isalnum() or character in "-_.:" for character in value)


def install_error_handling(application: FastAPI) -> None:
    @application.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        supplied = request.headers.get("X-Request-ID")
        request.state.request_id = supplied if _valid_request_id(supplied) else str(UUID(int=uuid4().int))
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        return response

    @application.exception_handler(AppError)
    async def app_error_handler(request: Request, error: AppError) -> JSONResponse:
        return _response(request, error)

    @application.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, error: RequestValidationError
    ) -> JSONResponse:
        field_errors: dict[str, list[str]] = {}
        for item in error.errors():
            path = ".".join(str(part) for part in item["loc"] if part not in {"body", "query", "path"})
            field_errors.setdefault(path or "request", []).append(item["msg"])
        return _response(
            request,
            AppError("validation_error", "Request validation failed", 400, field_errors),
        )

    @application.exception_handler(Exception)
    async def unknown_error_handler(request: Request, _error: Exception) -> JSONResponse:
        return _response(
            request,
            AppError("internal_error", "An unexpected error occurred", 500),
        )
