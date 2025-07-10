import logging
from fastapi import APIRouter
from fastapi import Depends, HTTPException
from crud.users import UserManager
from schemas.users import UserCreate
from sqlalchemy.ext.asyncio import AsyncSession
from schemas.config import settings
from db.users import get_async_session
from utils.utils import Utils

router = APIRouter(prefix=settings.api_prefix, tags=["Users"])

@router.post("/auth/provider/steam/login")
async def steam_login(
    token: str,
    db: AsyncSession = Depends(get_async_session),
):
    steam_id = Utils.token_to_steam_id(token)
    if not steam_id:
        raise HTTPException(status_code=400, detail="Invalid token")

    user_in = UserCreate(steam_id=steam_id)
    user = await UserManager.create_user(db, user_in=user_in)
    if user is None:
        user = await UserManager.get_user(db, steam_id=steam_id)
        return {"status": "exists", "user_id": user.user_id}

    return {"status": "created", "user_id": user.user_id}
