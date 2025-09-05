import uuid
import time
from fastapi import APIRouter, Depends, HTTPException, Response, Request
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

    if user.is_banned:
        raise HTTPException(status_code=401, detail="You`re banned")

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

@router.post("/me/logout")
async def logout(request: Request,
                 db_session: AsyncSession = Depends(get_sessions_session)):
    
    bhvr_session = request.cookies.get("bhvrSession")
    if not bhvr_session:
        raise HTTPException(status_code=401, detail="No session cookie")
    
    await SessionManager.delete_session(db=db_session, bhvr_session=bhvr_session)

@router.post("/me/richPresence")
async def rich_presence(request: Request,
                        db_users: AsyncSession = Depends(get_user_session),
                        db_sessions: AsyncSession = Depends(get_sessions_session)):
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
            "richPresencePlatform": "steam"
        },
        "gameState": game_state,
        "gameVersion": game_version,
        "online": online,
        "userType": user_type
    }