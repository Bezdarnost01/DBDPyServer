import logging
import uuid
import time
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession
from schemas.config import settings
from db.users import get_async_session
from utils.utils import Utils 
from utils.sessions import SessionWorker
from schemas.users import UserCreate
from crud.users import UserManager
# from crud.sessions import SessionManager   # предположим, будешь делать такую CRUD для сессий

router = APIRouter(prefix=settings.api_prefix, tags=["Users"])

SESSION_LENGTH = 60 * 30  # 30 минут (секунд)

@router.post("/auth/provider/steam/login")
async def steam_login(
    token: str,
    response: Response,  # чтобы выставлять куки
    db: AsyncSession = Depends(get_async_session),
):
    steam_id = Utils.token_to_steam_id(token)
    if not steam_id:
        raise HTTPException(status_code=400, detail="Invalid token")

    # Создать или получить пользователя
    user_in = UserCreate(steam_id=steam_id)
    user = await UserManager.create_user(db, user_in=user_in)
    if user is None:
        user = await UserManager.get_user(db, steam_id=steam_id)
    await UserManager.update_last_login(db, steam_id=steam_id)

    # Генерим cloud_id (user_id)
    cloud_id = user.user_id
    now = int(time.time())
    token_id = str(uuid.uuid4())
    session_id = SessionWorker.gen_bhvr_session(now=now, valid_for=SESSION_LENGTH)
    expire = now + SESSION_LENGTH

    # Здесь можно добавить создание записи сессии в базу (псевдокод):
    # await SessionManager.create_session(db, user_id=cloud_id, token_id=token_id, bhvr_session=session_id, expire=expire)

    # Выставить bhvrSession как cookie
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
        # опционально: можешь добавить поля platform/os/lang/ip, если тебе надо
    }
    return payload
