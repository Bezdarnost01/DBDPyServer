import asyncio
import logging
import sys

import redis.asyncio as redis
from api.v1 import routers
from crud.sessions import SessionManager
from db.sessions import sessions_sessionmaker
from fastapi import FastAPI
from middleware.http_middleware import log_http_request_time
from models import init_all_databases
from schemas.config import settings
from services.lobby import LobbyManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler("log/log.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)

logging.getLogger("httpx").setLevel(logging.WARNING)

async def regular_session_cleanup() -> None:
    """Функция `regular_session_cleanup` выполняет прикладную задачу приложения.
    
    Параметры:
        Отсутствуют.
    
    Возвращает:
        None: Функция не возвращает значение.
    """

    while True:
        async with sessions_sessionmaker() as db:
            try:
                await SessionManager.remove_expired_sessions(db)
            except Exception as exc:  # pragma: no cover - defensive logging
                logging.exception("Error during session cleanup: %s", exc)
        await asyncio.sleep(settings.cleanup_interval)


async def cleanup_dead_lobbies(
    redis_client: redis.Redis,
    lobby_manager: LobbyManager,
    check_interval: int = 20,
) -> None:
    """Функция `cleanup_dead_lobbies` выполняет прикладную задачу приложения.
    
    Параметры:
        redis_client (redis.Redis): Подключение к Redis.
        lobby_manager (LobbyManager): Менеджер бизнес-логики.
        check_interval (int): Параметр `check_interval`. Значение по умолчанию: 20.
    
    Возвращает:
        None: Функция не возвращает значение.
    """

    while True:
        open_lobbies = await redis_client.smembers("lobbies:open")
        stale_matches = []
        for match_id in open_lobbies:
            ping = await redis_client.get(f"lobby_ping:{match_id}")
            if ping is None:
                stale_matches.append(match_id)

        for match_id in stale_matches:
            await lobby_manager.delete_match(match_id)

        await asyncio.sleep(check_interval)


async def main(app: FastAPI):
    """Функция `main` выполняет прикладную задачу приложения.
    
    Параметры:
        app (FastAPI): Параметр `app`.
    
    Возвращает:
        Any: Результат выполнения функции.
    """

    await init_all_databases()
    app.state.redis = redis.from_url(settings.redis_url, decode_responses=True)
    app.state.lobby_manager = LobbyManager(app.state.redis)
    asyncio.create_task(regular_session_cleanup())
    asyncio.create_task(
        cleanup_dead_lobbies(app.state.redis, app.state.lobby_manager)
    )
    yield
    await app.state.redis.close()

app = FastAPI(lifespan=main)

app.middleware("http")(log_http_request_time)

for router in routers:
    app.include_router(router)

