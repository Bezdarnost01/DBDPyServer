from functools import wraps
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession
from crud.sessions import SessionManager
import logging
import time
import functools
import inspect
import traceback
import os
from typing import Any, Callable

def refresh_session(func):
    """
    Декоратор для авто-рефреша жизни сессии по bhvrSession.
    Используй на роуте, где нужно продлевать жизнь сессии.

    Аргументы:
        func: async endpoint function, которая обязательно принимает
            request: Request и db: AsyncSession (или через Depends)

    Пример:
        @router.get("/profile")
        @refresh_session
        async def profile(request: Request, db: AsyncSession = Depends(get_async_session)):
            ...
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Получаем Request и AsyncSession
        request = kwargs.get("request") or next((a for a in args if isinstance(a, Request)), None)
        db = kwargs.get("db") or next((a for a in args if isinstance(a, AsyncSession)), None)
        # Достаем bhvrSession
        bhvr_session = request.cookies.get("bhvrSession") if request else None
        if bhvr_session and db:
            await SessionManager.refresh_session_if_needed(db, bhvr_session)
        # Продолжаем выполнение обработчика
        return await func(*args, **kwargs)
    return wrapper

def setup_call_logger(file_path: str = "trace.log") -> logging.Logger:
    """
    Создаёт/возвращает логгер для call-трейсов.
    """
    logger = logging.getLogger("call-trace")
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)
    os.makedirs(os.path.dirname(file_path) or ".", exist_ok=True)
    fh = logging.FileHandler(file_path, encoding="utf-8")
    fmt = "%(asctime)s | %(levelname)s | %(message)s"
    fh.setFormatter(logging.Formatter(fmt))
    logger.addHandler(fh)
    return logger


def log_call(file_path: str = "trace.log") -> Callable:
    """
    Декоратор.  Пример:
        @log_call("logs/trace.log")
        async def my_route(...):
            ...
    """
    logger = setup_call_logger(file_path)

    def decorator(fn: Callable) -> Callable:
        is_async = inspect.iscoroutinefunction(fn)

        @functools.wraps(fn)
        async def async_wrapper(*args, **kwargs):
            return await _run(fn, args, kwargs, logger, is_async=True)

        @functools.wraps(fn)
        def sync_wrapper(*args, **kwargs):
            return _run(fn, args, kwargs, logger, is_async=False)

        return async_wrapper if is_async else sync_wrapper

    return decorator


async def _run(fn, args, kwargs, logger, is_async: bool):
    t0 = time.perf_counter()
    call_id = f"{fn.__module__}.{fn.__name__}"

    def _short(v: Any, limit: int = 120):
        s = repr(v)
        return s if len(s) <= limit else s[:limit] + "…"

    try:
        logger.debug(
            "CALL %s | args=%s kwargs=%s",
            call_id,
            [_short(a) for a in args],
            {k: _short(v) for k, v in kwargs.items()},
        )

        result = await fn(*args, **kwargs) if is_async else fn(*args, **kwargs)
        dt = (time.perf_counter() - t0) * 1000

        size = "-"
        if isinstance(result, (bytes, str, list, dict, tuple, set)):
            size = len(result)
        logger.debug(
            "OK   %s | %.1f ms | result=%s (%s)",
            call_id,
            dt,
            _short(result, 80),
            size,
        )
        return result

    except Exception as exc:
        dt = (time.perf_counter() - t0) * 1000
        logger.error(
            "ERR  %s | %.1f ms | %s\n%s",
            call_id,
            dt,
            exc,
            traceback.format_exc(limit=6),
        )
        raise

