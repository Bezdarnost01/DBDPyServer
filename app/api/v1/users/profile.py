from fastapi import APIRouter, Depends, HTTPException, Response, Request
from sqlalchemy.ext.asyncio import AsyncSession
from schemas.config import settings
from db.users import get_user_session
from db.sessions import get_sessions_session
from crud.sessions import SessionManager
from crud.users import UserManager

router = APIRouter(prefix=settings.api_prefix, tags=["Users"])

@router.post("/players/ban/status")
async def check_ban(
    request: Request,
    db_users: AsyncSession = Depends(get_user_session),
    db_sessions: AsyncSession = Depends(get_sessions_session),
):
    bhvr_session = request.cookies.get("bhvrSession")
    if not bhvr_session:
        raise HTTPException(status_code=401, detail="No session cookie")
    
    steam_id = await SessionManager.get_steam_id_by_session(db_sessions, bhvr_session)
    if not steam_id:
        raise HTTPException(status_code=401, detail="Session not found")

    user = await UserManager.get_user(db_users, steam_id=steam_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {"isBanned": bool(getattr(user, "is_banned", False))}
