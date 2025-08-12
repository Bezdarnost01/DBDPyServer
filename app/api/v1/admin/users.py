import logging
from fastapi import APIRouter, Depends, HTTPException, Response, Request, Body
from sqlalchemy.ext.asyncio import AsyncSession
from schemas.admin import KickUserRequest, SetUserSaveRequest
from schemas.config import settings
from crud.users import UserManager
from crud.websocket import WSManager
from crud.sessions import SessionManager
from utils.users import UserWorker
from db.users import get_user_session
from db.sessions import get_sessions_session

router = APIRouter(prefix=settings.api_admin_prefix, tags=["Admin"])

ws_manager = WSManager()

@router.put("/kick")
async def kick_user(
    request: Request,
    body: KickUserRequest,
    db_users: AsyncSession = Depends(get_user_session), 
    db_sessions: AsyncSession = Depends(get_sessions_session)
):
    if request.client.host not in settings.ip_admin_list:
        raise HTTPException(403, detail="Forbidden")

    kicked = []
    if body.bhvr_session:
        user_id = await SessionManager.get_user_id_by_session(db=db_sessions, bhvr_session=body.bhvr_session)
        if not user_id:
            raise HTTPException(404, detail="Session not found")
        await SessionManager.delete_session(db=db_sessions, bhvr_session=body.bhvr_session)
        await ws_manager.disconnect(user_id=user_id, db=db_sessions)
        kicked.append({"by": "bhvr_session", "user_id": user_id})

    if body.user_id:
        user = await SessionManager.get_user_session_by_user_id(db=db_sessions, user_id=body.user_id)
        if not user:
            raise HTTPException(404, detail="Session not found")
        await SessionManager.delete_session(db=db_sessions, user_id=body.user_id)
        await ws_manager.disconnect(user_id=body.user_id, db=db_sessions)
        kicked.append({"by": "user_id", "user_id": body.user_id})

    if body.steam_id:
        user_profile = await UserManager.get_user_profile(db=db_users, steam_id=body.steam_id)
        if not user_profile:
            raise HTTPException(404, detail="User not found")
        user = await SessionManager.get_user_session_by_user_id(db=db_sessions, user_id=user_profile.user_id)

        if not user:
            raise HTTPException(404, detail="Session not found")
        await SessionManager.delete_session(db=db_sessions, user_id=user.user_id)
        await ws_manager.disconnect(user_id=user.user_id, db=db_sessions)
        kicked.append({"by": "steam_id", "user_id": user.user_id})

    if body.steam_name:
        user_profile = await UserManager.get_user_profile_by_name(db=db_users, user_name=body.steam_name)
        if not user_profile:
            raise HTTPException(404, detail="User not found")
        user = await SessionManager.get_user_session_by_user_id(db=db_sessions, user_id=user_profile.user_id)
        if not user:
            raise HTTPException(404, detail="Session not found")
        await SessionManager.delete_session(db=db_sessions, user_id=user.user_id)
        await ws_manager.disconnect(user_id=user.user_id, db=db_sessions)
        kicked.append({"by": "steam_name", "user_id": user.user_id})

    if not kicked:
        raise HTTPException(400, detail="No valid kick target provided")
    return {"status": "ok", "kicked": kicked}

@router.put("/give_bloodpoints/{user_id}/{count}")
async def give_bloodpoints(request: Request,
    user_id: str,
    count: int,
    db_users: AsyncSession = Depends(get_user_session)
):
    if request.client.host not in settings.ip_admin_list:
        raise HTTPException(403, detail="Forbidden")
    
    user = await UserManager.get_user(db=db_users, user_id=user_id)

    if not user:
        raise HTTPException(404, "User not found")
    
    result = await UserWorker.set_experience_in_save(db=db_users, user_id=user_id, new_experience=count)

    return result

@router.get("/get_user_save/{user_id}")
async def get_user_save(request: Request,
    user_id: str,
    db_users: AsyncSession = Depends(get_user_session)
):
    if request.client.host not in settings.ip_admin_list:
        raise HTTPException(403, detail="Forbidden")
    
    user = await UserManager.get_user(db=db_users, user_id=user_id)

    if not user:
        raise HTTPException(404, "User not found")
    
    result = await UserWorker.get_user_json_save(db=db_users, user_id=user_id)

    return result

@router.put("/set_user_save/{user_id}")
async def set_user_save(request: Request,
    user_id: str,
    body: dict = Body(),
    db_users: AsyncSession = Depends(get_user_session)
):
    if request.client.host not in settings.ip_admin_list:
        raise HTTPException(403, detail="Forbidden")
    
    user = await UserManager.get_user(db=db_users, user_id=user_id)

    if not user:
        raise HTTPException(404, "User not found")
    
    result = await UserWorker.set_user_save(db=db_users, user_id=user_id, save_json=body)

    return result