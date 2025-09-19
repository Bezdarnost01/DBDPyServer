import datetime
import time
from typing import Annotated

from crud.sessions import SessionManager
from db.sessions import get_sessions_session
from fastapi import APIRouter, Depends, Request
from fastapi.responses import PlainTextResponse
from services.queue import MatchQueue
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()

start_time = time.time()


@router.get("/server-status")
async def server_status(request: Request, db: Annotated[AsyncSession, Depends(get_sessions_session)]):
    """Функция `server_status` выполняет прикладную задачу приложения.
    
    Параметры:
        request (Request): Входящий HTTP-запрос.
        db (Annotated[AsyncSession, Depends(get_sessions_session)]): Подключение к базе данных.
    
    Возвращает:
        Any: Результат выполнения функции.
    """

    uptime = int(time.time() - start_time)
    online = await SessionManager.get_sessions_count(db)

    redis = request.app.state.redis
    lobby_manager = request.app.state.lobby_manager
    queue_a = MatchQueue(redis, side="A", lobby_manager=lobby_manager)
    queue_b = MatchQueue(redis, side="B", lobby_manager=lobby_manager)

    stats_a = await queue_a.get_stats()
    stats_b = await queue_b.get_stats()

    return {
        "uptime": f"{uptime} seconds",
        "online": online,
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "queues": {
            "A": stats_a,
            "B": stats_b,
            "totalOpenLobbies": stats_a["openLobbies"],
            "totalQueued": stats_a["queue"] + stats_b["queue"],
        },
    }


def get_date_string_minus_2_hours() -> str:
    """Функция `get_date_string_minus_2_hours` выполняет прикладную задачу приложения.
    
    Параметры:
        Отсутствуют.
    
    Возвращает:
        str: Результат выполнения функции.
    """

    now = datetime.datetime.utcnow() + datetime.timedelta(hours=3)
    now -= datetime.timedelta(hours=4)
    return f"{now.year}{now.month:02d}{now.day:02d}{now.hour:02d}"


def xor_cipher(data, key):
    """Функция `xor_cipher` выполняет прикладную задачу приложения.
    
    Параметры:
        data (Any): Структура данных.
        key (Any): Параметр `key`.
    
    Возвращает:
        Any: Результат выполнения функции.
    """

    return "".join(chr(ord(data[i]) ^ ord(key[i % len(key)])) for i in range(len(data)))


@router.get("/getkey", response_class=PlainTextResponse)
def getkey():
    """Функция `getkey` выполняет прикладную задачу приложения.
    
    Параметры:
        Отсутствуют.
    
    Возвращает:
        Any: Результат выполнения функции.
    """

    date_str = get_date_string_minus_2_hours()
    encryption_key = "dbdclub"
    return xor_cipher(date_str, encryption_key)
