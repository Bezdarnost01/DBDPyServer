from fastapi import APIRouter, Depends, HTTPException, Response, Request
from sqlalchemy.ext.asyncio import AsyncSession
from schemas.config import settings
from db.sessions import get_sessions_session
from db.users import get_user_session
from dependency.redis import Redis
from fastapi import Body
from crud.sessions import SessionManager
from schemas.queue import QueueRequest, CustomData
import logging
import time
import json
from services.lobby import LobbyManager
from services.queue import MatchQueue

logger = logging.getLogger(__name__) 

router = APIRouter(prefix=settings.api_prefix, tags=["Match"])

@router.post("/queue")
async def queue_player(
    request: Request,
    body: QueueRequest = Body(),
    redis = Depends(Redis.get_redis),
    db_sessions: AsyncSession = Depends(get_sessions_session),
    db_users: AsyncSession = Depends(get_user_session)
):
    bhvr_session = request.cookies.get("bhvrSession")
    if not bhvr_session:
        raise HTTPException(status_code=401, detail="No session cookie")
    
    user_id = await SessionManager.get_user_id_by_session(db_sessions, bhvr_session)
    if not user_id:
        raise HTTPException(status_code=401, detail="Session not found")

    session_obj = {
        "bhvrSession": bhvr_session,
        "clientIds": {
            "userId": user_id
        },
        "side": body.side.upper()
    }
    lobby_manager = request.app.state.lobby_manager
    match_queue = MatchQueue(redis, body.side.upper(), lobby_manager)

    if not body.checkOnly:
        await match_queue.add_player(
            bhvr_session=bhvr_session,
            user_id=user_id,
            side=body.side.upper()
        )
        return {
            "queueData": {
                "ETA": -10000,
                "position": 0,
                "sizeA": 1 if body.side.upper() == 'A' else 0,
                "sizeB": 1 if body.side.upper() == 'B' else 0,
                "stable": False
            },
            "status": "QUEUED"
        }
    else:
        response = await match_queue.get_queue_status(session_obj)
        return response

@router.post("/match/{match_id}/register")
async def match_register(
    match_id: str, 
    request: Request,
    redis = Depends(Redis.get_redis),
    db_sessions: AsyncSession = Depends(get_sessions_session),
    db_users: AsyncSession = Depends(get_user_session)
):
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=500, detail="Invalid JSON")

    session_settings = body.get("customData", {}).get("SessionSettings")

    lobby_manager = request.app.state.lobby_manager
    lobby = await lobby_manager.register_match(match_id, session_settings)
    if lobby is None:
        raise HTTPException(status_code=500, detail="Lobby not found or error")
    
    response = {
        "matchId": lobby["id"],
        "category": "live-413207-live:None:Windows:all::1:4:0:G:2",
        "creationDateTime": int(time.time()),
        "status": "OPENED",
        "creator": lobby["host"]["userId"],
        "customData": {
            "SessionSettings": lobby.get("sessionSettings", "")
        },
        "version": 2,
        "props": {
            "countA": 1,
            "countB": 4,
            "gameMode": "None",
            "platform": "UniversalXPlay",
            "CrossplayOptOut": "false",
            "isDedicated": False
        },
        "sideA": [
            lobby["host"]["userId"]
        ],
        "sideB": [p["userId"] for p in lobby["nonHosts"]]
    }

    return response

async def create_match_response(lobby_manager: LobbyManager, match_id: str, killed: bool = False):
    lobby = await lobby_manager.get_lobby_by_id(match_id)
    if not lobby:
        lobby = await lobby_manager.get_killed_lobby_by_id(match_id)
        killed = True
    if not lobby:
        return {}
    return {
        "matchId": match_id,
        "category": "live-413207-live:None:Windows:all::1:4:0:G:2",
        "creationDateTime": int(time.time()),
        "status": "CLOSED" if killed else "OPENED",
        "creator": lobby["host"]["userId"],
        "customData": {
            "SessionSettings": lobby.get("sessionSettings", "")
        },
        "version": 2,
        "props": {
            "countA": 1,
            "countB": 4,
            "gameMode": "None",
            "platform": "UniversalXPlay",
            "CrossplayOptOut": "false",
            "isDedicated": False
        },
        "sideA": [lobby["host"]["userId"]],
        "sideB": [p["userId"] for p in lobby.get("nonHosts", [])]
    }

@router.get("/match/{match_id}")
async def get_match(
    match_id: str,
    request: Request,
    redis = Depends(Redis.get_redis)
):
    lobby_manager = request.app.state.lobby_manager
    response = await create_match_response(lobby_manager, match_id)
    if not response:
        raise HTTPException(status_code=404, detail="Match not found")
    await redis.set(f"lobby_ping:{match_id}", int(time.time()), ex=20)
    return response

@router.put("/match/{match_id}/{reason}")
async def close_match(
    match_id: str,
    reason: str,
    request: Request,
    redis = Depends(Redis.get_redis)
):
    bhvr_session = request.cookies.get("bhvrSession")
    if not bhvr_session:
        raise HTTPException(status_code=404, detail="No session cookie")

    lobby_manager = request.app.state.lobby_manager
    lobby = await lobby_manager.get_lobby_by_id(match_id)
    if not lobby:
        raise HTTPException(status_code=404, detail="Lobby not found")

    is_owner = await lobby_manager.is_owner(match_id, bhvr_session)

    if is_owner:
        lobby["reason"] = reason
        try:
            await redis.set(f"lobby:{match_id}", json.dumps(lobby))
        except Exception as e:
            return {"error": f"json error: {str(e)}"}

        await lobby_manager.delete_match(match_id)
        resp = await MatchQueue.create_match_response(lobby_manager, match_id, killed=True)
        return resp
    else:
        removed = await lobby_manager.remove_player_from_lobby(match_id, bhvr_session)
        if not removed:
            raise HTTPException(status_code=404, detail="Player not found in lobby")
        return {"status": "left", "matchId": match_id}

@router.post("/queue/cancel", status_code=204)
async def cancel_queue(
    request: Request,
    redis = Depends(Redis.get_redis)
):
    bhvr_session = request.cookies.get("bhvrSession")
    if not bhvr_session:
        raise HTTPException(status_code=404, detail="No session cookie")
    
    lobby_manager = request.app.state.lobby_manager
    for side in ("A", "B"):
        match_queue = MatchQueue(redis, side, lobby_manager)
        await match_queue.remove_player(bhvr_session)

    return Response(status_code=204)

@router.post("/players/recentlyplayed/add")
async def player_add():
    return {}

@router.post("/end-of-match-event")
async def end_of_match_event():
    return {}

@router.put("/softWallet/put/analytics")
async def put_analytics():
    return {}

@router.post("/extensions/playerLevels/earnPlayerXp")
async def earnPlayerXp():
    return {}