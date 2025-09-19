import logging
import time
from collections.abc import Awaitable, Callable

from fastapi import Request

logger = logging.getLogger("myapp.http")

async def log_http_request_time(
    request: Request,
    call_next: Callable[[Request], Awaitable],
):
    """Функция `log_http_request_time` выполняет прикладную задачу приложения.
    
    Параметры:
        request (Request): Входящий HTTP-запрос.
        call_next (Callable[[Request], Awaitable]): Параметр `call_next`.
    
    Возвращает:
        Any: Результат выполнения функции.
    """

    start_time = time.perf_counter()
    response = await call_next(request)
    process_time = time.perf_counter() - start_time
    if process_time > 1.0:
        logger.warning(
            f"Долгий HTTP-запрос: {request.method} {request.url.path} — {process_time:.3f} сек",
        )
    return response
