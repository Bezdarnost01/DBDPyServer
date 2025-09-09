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
    """
    Возвращает текущий статус сервера.

    **Поля ответа:**

    - **uptime** (`str`): время работы сервера с момента запуска в секундах
      (например `"12345 seconds"`).

    - **online** (`int`): количество активных пользовательских сессий
      (берётся через `SessionManager.get_sessions_count`).

    - **timestamp** (`str`): текущая метка времени в UTC формате ISO8601
      (например `"2025-09-07T19:52:13.123456"`).

    - **queues** (`dict`): статистика очередей матчмейкера.

      - **A** (`dict`): состояние очереди игроков стороны A (киллеры).
        - `openLobbies` (`int`): количество открытых лобби (готовы, но матч не стартовал).
        - `queueA` (`int`): количество игроков A в очереди.
        - `queueB` (`int`): количество игроков B (для этого инстанса обычно `0`).
        - `queuedTotal` (`int`): общее число игроков A+B в этой очереди.

      - **B** (`dict`): состояние очереди игроков стороны B (сурвы).
        - `openLobbies` (`int`): количество открытых лобби, ожидающих игроков B.
        - `queueA` (`int`): количество игроков A (обычно `0`).
        - `queueB` (`int`): количество игроков B, ожидающих слота.
        - `queuedTotal` (`int`): общее число игроков A+B в этой очереди.

      - **totalOpenLobbies** (`int`): общее количество открытых лобби по обеим сторонам.
      - **totalQueued** (`int`): суммарное количество игроков в очереди (A+B).
    """
    uptime = int(time.time() - start_time)
    online = await SessionManager.get_sessions_count(db)

    # Создаём очереди на лету (как в /match)
    redis = request.app.state.redis
    lobby_manager = request.app.state.lobby_manager
    queue_a = MatchQueue(redis, side="A", lobby_manager=lobby_manager)
    queue_b = MatchQueue(redis, side="B", lobby_manager=lobby_manager)

    stats_a = await queue_a.get_stats()  # {"openLobbies": X, "queue": lenA}
    stats_b = await queue_b.get_stats()  # {"openLobbies": X, "queue": lenB}

    return {
        "uptime": f"{uptime} seconds",
        "online": online,
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "queues": {
            "A": stats_a,
            "B": stats_b,
            "totalOpenLobbies": stats_a["openLobbies"],           # = stats_b["openLobbies"]
            "totalQueued": stats_a["queue"] + stats_b["queue"],
        },
    }

def get_date_string_minus_2_hours() -> str:
    now = datetime.datetime.utcnow() + datetime.timedelta(hours=3)  # Moscow time
    now -= datetime.timedelta(hours=4)
    return f"{now.year}{now.month:02d}{now.day:02d}{now.hour:02d}"

def xor_cipher(data, key):
    return "".join(chr(ord(data[i]) ^ ord(key[i % len(key)])) for i in range(len(data)))

@router.get("/getkey", response_class=PlainTextResponse)
def getkey():
    date_str = get_date_string_minus_2_hours()
    encryption_key = "dbdclub"
    return xor_cipher(date_str, encryption_key)
