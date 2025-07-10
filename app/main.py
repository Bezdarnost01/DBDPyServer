import logging
import asyncio
import uvicorn
import sys
from fastapi import FastAPI

from api.v1 import routers
from models import init_all_databases

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler("log/log.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)

async def main(app: FastAPI):
    await init_all_databases()
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
