import logging
import asyncio
import time
import sys
from fastapi import FastAPI
import redis.asyncio as redis

from api.v1 import routers
from middleware.http_middleware import log_http_request_time
from models import init_all_databases
from schemas.config import settings
from services.lobby import LobbyManager
from crud.sessions import SessionManager
from db.sessions import sessions_sessionmaker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler("log/log.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)

logging.getLogger("httpx").setLevel(logging.WARNING)

async def regular_session_cleanup():
    while True:
        async with sessions_sessionmaker() as db:
            try:
                await SessionManager.remove_expired_sessions(db)
            except Exception as e:
                logging.error(f"Error during session cleanup: {e}")
        await asyncio.sleep(settings.cleanup_interval)

async def cleanup_dead_lobbies(redis, lobby_manager, check_interval=20):
    while True:
        open_lobbies = await redis.smembers("lobbies:open")
        int(time.time())
        for match_id in open_lobbies:
            ping = await redis.get(f"lobby_ping:{match_id}")
            if ping is None:
                await lobby_manager.delete_match(match_id)
        await asyncio.sleep(check_interval)

async def main(app: FastAPI):
    await init_all_databases()
    app.state.redis = redis.from_url(settings.redis_url, decode_responses=True)
    app.state.lobby_manager = LobbyManager(app.state.redis)  # <-- Вот тут создаём и сохраняем!
    asyncio.create_task(regular_session_cleanup())
    asyncio.create_task(cleanup_dead_lobbies(app.state.redis, app.state.lobby_manager))  # используем app.state.lobby_manager
    yield
    await app.state.redis.close()

app = FastAPI(lifespan=main)

app.middleware("http")(log_http_request_time)

for router in routers:
    app.include_router(router)

