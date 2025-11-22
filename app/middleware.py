"""
Middleware для FastAPI приложения.
"""

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import logging
import time
from typing import Callable

logger = logging.getLogger("avito-assist.middleware")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware для логирования всех входящих запросов и исходящих ответов.
    Также замеряет время выполнения запроса.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Генерируем уникальный ID запроса
        request_id = id(request)
        
        # Логируем начало обработки запроса
        logger.info(
            "Request started: request_id=%s method=%s path=%s client=%s",
            request_id,
            request.method,
            request.url.path,
            request.client.host if request.client else "unknown",
            extra={
                "extra_fields": {
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                }
            },
        )
        
        # Замеряем время выполнения
        start_time = time.time()
        
        try:
            # Обрабатываем запрос
            response = await call_next(request)
            
            # Считаем время выполнения
            duration_ms = (time.time() - start_time) * 1000
            
            # Логируем успешный ответ
            logger.info(
                "Request completed: request_id=%s method=%s path=%s status=%s duration=%.2fms",
                request_id,
                request.method,
                request.url.path,
                response.status_code,
                duration_ms,
                extra={
                    "extra_fields": {
                        "request_id": request_id,
                        "status_code": response.status_code,
                        "duration_ms": duration_ms,
                    }
                },
            )
            
            # Добавляем заголовок с временем выполнения
            response.headers["X-Process-Time"] = f"{duration_ms:.2f}ms"
            
            return response
            
        except Exception as exc:
            duration_ms = (time.time() - start_time) * 1000
            
            logger.error(
                "Request failed: request_id=%s method=%s path=%s error=%s duration=%.2fms",
                request_id,
                request.method,
                request.url.path,
                str(exc),
                duration_ms,
                exc_info=True,
                extra={
                    "extra_fields": {
                        "request_id": request_id,
                        "error": str(exc),
                        "duration_ms": duration_ms,
                    }
                },
            )
            
            raise
