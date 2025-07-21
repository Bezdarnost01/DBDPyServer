from fastapi import APIRouter, Depends, HTTPException, Response, Request
from sqlalchemy.ext.asyncio import AsyncSession
from schemas.config import settings
from db.users import get_user_session
from db.sessions import get_sessions_session
import time
import asyncio
from crud.sessions import SessionManager
from crud.users import UserManager
from utils.utils import Utils

router = APIRouter(prefix=settings.api_prefix, tags=["Reward"])

@router.get("/messages/list")
async def get_messages_list(limit: int = 100):
    return {"success": True}

@router.get("/messages/claim")
async def claim_reward():
    {"inventories":[],"currencies":[{"id":"Cells","newAmount":25000,"receivedAmount":12500}],"flag":"READ"}