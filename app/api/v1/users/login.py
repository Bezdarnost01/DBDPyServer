import logging
import uuid
import time
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession
from schemas.config import settings
from db.users import get_user_session
from db.sessions import get_sessions_session
from utils.utils import Utils 
from utils.sessions import SessionWorker
from schemas.users import UserCreate
from crud.users import UserManager
from crud.sessions import SessionManager

router = APIRouter(prefix=settings.api_prefix, tags=["Users"])

SESSION_LENGTH = 60 * 60

@router.post("/auth/provider/steam/login")
async def steam_login(token: str, response: Response,  
                      db_users: AsyncSession = Depends(get_user_session), 
                      db_sessions: AsyncSession = Depends(get_sessions_session)):
    steam_id = Utils.token_to_steam_id(token)
    if not steam_id:
        raise HTTPException(status_code=400, detail="Invalid token")

    user_in = UserCreate(steam_id=steam_id)
    user = await UserManager.create_user(db_users, user_in=user_in)
    if user is None:
        user = await UserManager.get_user(db_users, steam_id=steam_id)
    await UserManager.update_last_login(db_users, steam_id=steam_id)

    cloud_id = user.user_id
    now = int(time.time())
    token_id = str(uuid.uuid4())
    session_id = SessionWorker.gen_bhvr_session(now=now, valid_for=SESSION_LENGTH)
    expire = now + SESSION_LENGTH

    await SessionManager.create_session(db_sessions, bhvr_session=session_id, steam_id=steam_id, expires=expire)

    response.set_cookie(
        key="bhvrSession",
        value=session_id,
        max_age=SESSION_LENGTH,
        httponly=True,
        secure=True,
        samesite="lax",
        path="/"
    )

    payload = {
        "triggerResults": {
            "error": [],
            "success": [None],
        },
        "id": cloud_id,
        "creationDate": now,
        "provider": {
            "providerName": "steam",
            "providerId": steam_id
        },
        "providers": [{
            "providerName": "steam",
            "providerId": steam_id
        }],
        "friends": [],
        "tokenId": token_id,
        "generated": now,
        "expire": expire,
        "userId": cloud_id,
        "token": token_id,
    }
    return payload
