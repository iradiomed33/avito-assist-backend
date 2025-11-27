"""
Централизованная обработка ошибок и исключений FastAPI.
"""

from fastapi import Request, status, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging
import traceback
from typing import Union

logger = logging.getLogger("avito-assist")


async def http_exception_handler(request: Request, exc: HTTPException):
    if exc.status_code == 401 and "WWW-Authenticate" in exc.headers:
        # Basic Auth — отдаём стандартный ответ с попапом
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers=exc.headers  # ← КРИТИЧНО: сохраняем WWW-Authenticate!
        )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "http_error",
            "status_code": exc.status_code,
            "detail": exc.detail,
            "path": request.url.path,
        },
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    Обработчик ошибок валидации Pydantic (422 Unprocessable Entity).
    """
    logger.error(
        "Validation Error: path=%s errors=%s",
        request.url.path,
        exc.errors(),
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "validation_error",
            "detail": exc.errors(),
            "path": request.url.path,
        },
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Обработчик всех необработанных исключений (500 Internal Server Error).
    Логирует полный traceback для отладки.
    """
    logger.error(
        "Unhandled Exception: path=%s exception=%s",
        request.url.path,
        str(exc),
        exc_info=True,  # Логируем полный traceback
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "internal_server_error",
            "detail": "An unexpected error occurred. Please contact support.",
            "path": request.url.path,
        },
    )


def log_request_response(func):
    """
    Декоратор для логирования запросов и ответов.
    Можно использовать как middleware.
    """
    async def wrapper(request: Request, call_next):
        logger.info(
            "Request: method=%s path=%s client=%s",
            request.method,
            request.url.path,
            request.client.host if request.client else "unknown",
        )
        
        try:
            response = await call_next(request)
            logger.info(
                "Response: method=%s path=%s status=%s",
                request.method,
                request.url.path,
                response.status_code,
            )
            return response
        except Exception as exc:
            logger.error(
                "Error during request processing: method=%s path=%s error=%s",
                request.method,
                request.url.path,
                str(exc),
                exc_info=True,
            )
            raise
    
    return wrapper
