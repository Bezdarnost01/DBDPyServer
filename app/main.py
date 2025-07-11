import logging
import asyncio
import uvicorn
import sys
from fastapi import FastAPI

from api.v1 import routers
from models import init_all_databases
from schemas.config import settings
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

async def regular_session_cleanup():
    while True:
        async with sessions_sessionmaker() as db:
            try:
                await SessionManager.remove_expired_sessions(db)
            except Exception as e:
                logging.error(f"Error during session cleanup: {e}")
        await asyncio.sleep(settings.cleanup_interval)

async def main(app: FastAPI):
    await init_all_databases()
    asyncio.create_task(regular_session_cleanup())
    yield

app = FastAPI(lifespan=main)

for router in routers:
    app.include_router(router)

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=443,
        reload=True,
        ssl_keyfile="/etc/letsencrypt/live/dbdclub.live/privkey.pem",
        ssl_certfile="/etc/letsencrypt/live/dbdclub.live/fullchain.pem"
    )
