import time
import uuid
from typing import Annotated

from crud.sessions import SessionManager
from crud.users import UserManager
from db.sessions import get_sessions_session
from db.users import get_user_session
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from schemas.config import settings
from sqlalchemy.ext.asyncio import AsyncSession
from utils.sessions import SessionWorker
from utils.utils import Utils

router = APIRouter(prefix=settings.api_prefix, tags=["Users"])

SESSION_LENGTH = 60 * 60

@router.post("/auth/provider/steam/login")
async def steam_login(token: str, response: Response,
                      db_users: Annotated[AsyncSession, Depends(get_user_session)],
                      db_sessions: Annotated[AsyncSession, Depends(get_sessions_session)]):
    """Функция `steam_login` выполняет прикладную задачу приложения.
    
    Параметры:
        token (str): Параметр `token`.
        response (Response): HTTP-ответ.
        db_users (Annotated[AsyncSession, Depends(get_user_session)]): Подключение к базе данных.
        db_sessions (Annotated[AsyncSession, Depends(get_sessions_session)]): Объект сессии.
    
    Возвращает:
        Any: Результат выполнения функции.
    """

    steam_id = Utils.token_to_steam_id(token)
    if not steam_id:
        raise HTTPException(status_code=400, detail="Invalid token")

    user = await UserManager.get_user(db_users, steam_id=steam_id)
    if user is None:
        raise HTTPException(status_code=403, detail="Login via launcher first")

    if user.is_banned:
        raise HTTPException(status_code=401, detail="You`re banned")
    await UserManager.update_last_login(db_users, steam_id=steam_id)

    cloud_id = user.user_id
    now = int(time.time())
    token_id = str(uuid.uuid4())
    session_id = SessionWorker.gen_bhvr_session(now=now, valid_for=SESSION_LENGTH)
    expire = now + SESSION_LENGTH

    await SessionManager.create_session(db_sessions, bhvr_session=session_id, user_id=user.user_id, steam_id=steam_id, expires=expire)

    response.set_cookie(
        key="bhvrSession",
        value=session_id,
        max_age=SESSION_LENGTH,
        httponly=True,
        secure=True,
        samesite="lax",
        path="/",
    )

    return {
        "triggerResults": {
            "error": [],
            "success": [None],
        },
        "id": cloud_id,
        "creationDate": now,
        "provider": {
            "providerName": "steam",
            "providerId": steam_id,
        },
        "providers": [{
            "providerName": "steam",
            "providerId": steam_id,
        }],
        "friends": [],
        "tokenId": token_id,
        "generated": now,
        "expire": expire,
        "userId": cloud_id,
        "token": token_id,
    }

@router.post("/me/logout")
async def logout(request: Request,
                 db_session: Annotated[AsyncSession, Depends(get_sessions_session)]) -> None:
    """Функция `logout` выполняет прикладную задачу приложения.
    
    Параметры:
        request (Request): Входящий HTTP-запрос.
        db_session (Annotated[AsyncSession, Depends(get_sessions_session)]): Объект сессии.
    
    Возвращает:
        None: Функция не возвращает значение.
    """

    bhvr_session = request.cookies.get("bhvrSession")
    if not bhvr_session:
        raise HTTPException(status_code=401, detail="No session cookie")

    await SessionManager.delete_session(db=db_session, bhvr_session=bhvr_session)

@router.post("/me/richPresence")
async def rich_presence(request: Request,
                        db_users: Annotated[AsyncSession, Depends(get_user_session)],
                        db_sessions: Annotated[AsyncSession, Depends(get_sessions_session)]):
    """Функция `rich_presence` выполняет прикладную задачу приложения.
    
    Параметры:
        request (Request): Входящий HTTP-запрос.
        db_users (Annotated[AsyncSession, Depends(get_user_session)]): Подключение к базе данных.
        db_sessions (Annotated[AsyncSession, Depends(get_sessions_session)]): Объект сессии.
    
    Возвращает:
        Any: Результат выполнения функции.
    """

    body = await request.json()

    game_state = body.get("gameState", "InMenus")
    game_version = body.get("gameVersion", "8.6.1_2377945live")
    rich_presence_status = body.get("gameSpecificData", {}).get("richPresenceStatus", "InMenus")
    online = body.get("online", True)
    user_type = body.get("userType", None)

    if user_type == "player":
        bhvr_session = request.cookies.get("bhvrSession")
        if not bhvr_session:
            raise HTTPException(status_code=401, detail="No session cookie")

        user_id = await SessionManager.get_user_id_by_session(db_sessions, bhvr_session)
        if not user_id:
            raise HTTPException(status_code=401, detail="Session not found")

        await UserManager.update_user_profile(db=db_users, user_id=user_id, user_state=game_state)

    return {
        "currentProvider": "steam",
        "gameSpecificData": {
            "richPresenceStatus": rich_presence_status,
            "richPresencePlatform": "steam",
        },
        "gameState": game_state,
        "gameVersion": game_version,
        "online": online,
        "userType": user_type,
    }
