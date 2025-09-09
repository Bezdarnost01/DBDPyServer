import logging
import time

from fastapi import Request

logger = logging.getLogger("myapp.http")

async def log_http_request_time(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    if process_time > 1.0:
        logger.warning(
            f"Долгий HTTP-запрос: {request.method} {request.url.path} — {process_time:.3f} сек",
        )
    return response
