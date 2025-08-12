import os
import time
from crud.sessions import SessionManager
from db.sessions import get_sessions_session
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, HTTPException, Response, Request
from fastapi.responses import PlainTextResponse
import datetime

router = APIRouter()

start_time = time.time()

@router.get("/server-status")
async def server_status(db: AsyncSession = Depends(get_sessions_session)):
    from datetime import datetime, timedelta
    uptime = int(time.time() - start_time)
    online = await SessionManager.get_sessions_count(db)
    return {
        "uptime": f"{uptime} seconds",
        "online": online,
        "timestamp": datetime.utcnow().isoformat()
    }

def get_date_string_minus_2_hours():
    now = datetime.datetime.utcnow() + datetime.timedelta(hours=3)  # Moscow time
    now -= datetime.timedelta(hours=4)
    return f"{now.year}{now.month:02d}{now.day:02d}{now.hour:02d}"

def xor_cipher(data, key):
    return ''.join(chr(ord(data[i]) ^ ord(key[i % len(key)])) for i in range(len(data)))

@router.get("/getkey", response_class=PlainTextResponse)
def getkey():
    date_str = get_date_string_minus_2_hours()
    encryption_key = "dbdclub"
    encrypted_key = xor_cipher(date_str, encryption_key)
    return encrypted_key