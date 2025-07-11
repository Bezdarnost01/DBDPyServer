from functools import wraps
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import Response
from crud.sessions import SessionManager

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
