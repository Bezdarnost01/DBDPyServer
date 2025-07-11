import time
from datetime import datetime
from crud.sessions import SessionManager
from db.sessions import get_sessions_session
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, HTTPException, Response, Request

router = APIRouter()

start_time = time.time()

@router.get("/server-status")
async def server_status(db: AsyncSession = Depends(get_sessions_session)):
    uptime = int(time.time() - start_time)
    online = await SessionManager.get_sessions_count(db)
    return {
        "uptime": f"{uptime} seconds",
        "online": online,
        "timestamp": datetime.utcnow().isoformat()
    }
