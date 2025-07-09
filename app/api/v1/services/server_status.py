from fastapi import APIRouter
import time
from datetime import datetime

router = APIRouter()

start_time = time.time()

@router.get("/server-status")
async def server_status():
    uptime = int(time.time() - start_time)
    online = 0
    return {
        "uptime": f"{uptime} seconds",
        "online": online,
        "timestamp": datetime.utcnow().isoformat()
    }
