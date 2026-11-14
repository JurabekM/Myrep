from typing import Any

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

PROBLEM_JSON = "application/problem+json"


class ProblemError(Exception):
    """RFC 7807 (problem+json) formatidagi biznes xatoligi."""

    def __init__(self, status: int, title: str, detail: str | None = None) -> None:
        super().__init__(title)
        self.status = status
        self.title = title
        self.detail = detail


def _problem(status: int, title: str, detail: Any, instance: str) -> JSONResponse:
    body = {
        "type": "about:blank",
        "title": title,
        "status": status,
        "detail": detail,
        "instance": instance,
    }
    return JSONResponse(body, status_code=status, media_type=PROBLEM_JSON)


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ProblemError)
    async def _problem_error(request: Request, exc: ProblemError) -> JSONResponse:
        return _problem(exc.status, exc.title, exc.detail, request.url.path)

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return _problem(exc.status_code, str(exc.detail), None, request.url.path)

    @app.exception_handler(RequestValidationError)
    async def _validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        return _problem(422, "Ma'lumot noto'g'ri", jsonable_encoder(exc.errors()), request.url.path)
