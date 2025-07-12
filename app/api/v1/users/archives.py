from fastapi import APIRouter, Depends, HTTPException, Response, Request
from sqlalchemy.ext.asyncio import AsyncSession
from schemas.config import settings
from db.users import get_user_session
from db.sessions import get_sessions_session
from crud.sessions import SessionManager
from crud.users import UserManager
from utils.utils import Utils

router = APIRouter(prefix=settings.api_prefix, tags=["Archives"])

@router.get("/archives/stories/get/activeNode")
async def get_active_node():
    return {"activeNode":[]}

@router.post("/archives/rewards/claim-old-tracks")
async def get_active_rewards():
    return {"rewards":[]}