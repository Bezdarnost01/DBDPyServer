import logging
from fastapi import APIRouter, Depends, HTTPException, Response, Request, Body
from sqlalchemy.ext.asyncio import AsyncSession
from schemas.admin import KickUserRequest, SetUserSaveRequest, BanUserRequest
from schemas.config import settings
from crud.users import UserManager
from crud.websocket import WSManager
from crud.sessions import SessionManager
from utils.users import UserWorker
from db.users import get_user_session
from db.sessions import get_sessions_session

router = APIRouter(prefix=settings.api_admin_prefix, tags=["Auth"])

