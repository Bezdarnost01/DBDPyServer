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

@router.post("/players/friends/sync")
async def friends_sync(req: Request,
                       db_users: AsyncSession = Depends(get_user_session),
                       db_sessions: AsyncSession = Depends(get_sessions_session)
):
    
    bhvr_session = req.cookies.get("bhvrSession")
    if not bhvr_session:
        raise HTTPException(status_code=401, detail="No session cookie")
    user_id = await SessionManager.get_user_id_by_session(db_sessions, bhvr_session)
    if not user_id:
        raise HTTPException(status_code=401, detail="Session not found")

    body = await req.json()
    ids = body.get("ids", [])
    cid = user_id

    chunks = [ids[i:i+100] for i in range(0, len(ids), 100)]
    name_tasks = [Utils.fetch_names_batch(chunk) for chunk in chunks]
    results = await asyncio.gather(*name_tasks)

    steamid_to_name = {}
    for d in results:
        steamid_to_name.update(d)

    friends = []
    for sid in ids:
        pname = steamid_to_name.get(sid, "Unknown")
        friends.append({
            "userId": cid,
            "friendId": sid,
            "status": "confirmed",
            "platformIds": {"steam": sid},
            "friendPlayerName": {
                "userId": sid,
                "providerPlayerNames": {"steam": pname},
                "playerName": pname
            },
            "favorite": False,
            "mute": False,
            "isKrakenOnlyFriend": False
        })
    return {"list": friends}