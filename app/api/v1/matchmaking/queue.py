import json
import logging
import time
from typing import Annotated

from crud.sessions import SessionManager
from crud.users import UserManager
from db.sessions import get_sessions_session
from db.users import get_user_session
from dependency.redis import Redis
from fastapi import APIRouter, Body, Depends, HTTPException, Request, Response
from schemas.config import settings
from schemas.queue import QueueRequest
from services.lobby import LobbyManager
from services.queue import MatchQueue
from sqlalchemy.ext.asyncio import AsyncSession
from utils.utils import Utils

logger = logging.getLogger(__name__)

router = APIRouter(prefix=settings.api_prefix, tags=["Match"])

@router.post("/queue")
async def queue_player(
    request: Request,
    body: Annotated[QueueRequest, Body()],
    redis = Depends(Redis.get_redis),
    db_sessions: AsyncSession = Depends(get_sessions_session),
    db_users: AsyncSession = Depends(get_user_session),
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
            "userId": user_id,
        },
        "side": body.side.upper(),
    }
    lobby_manager = request.app.state.lobby_manager
    match_queue = MatchQueue(redis, body.side.upper(), lobby_manager)

    if not body.checkOnly:
        await match_queue.add_player(
            bhvr_session=bhvr_session,
            user_id=user_id,
            side=body.side.upper(),
        )
        return {
            "queueData": {
                "ETA": -10000,
                "position": 0,
                "sizeA": 1 if body.side.upper() == "A" else 0,
                "sizeB": 1 if body.side.upper() == "B" else 0,
                "stable": False,
            },
            "status": "QUEUED",
        }
    return await match_queue.get_queue_status(session_obj)

@router.post("/match/{match_id}/register")
async def match_register(
    match_id: str,
    request: Request,
    redis = Depends(Redis.get_redis),
    db_sessions: AsyncSession = Depends(get_sessions_session),
    db_users: AsyncSession = Depends(get_user_session),
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

    return {
        "matchId": lobby["id"],
        "category": "live-138518-live:None:Windows:all::1:4:0:G:2",
        "creationDateTime": int(time.time()),
        "status": "OPENED",
        "creator": lobby["host"]["userId"],
        "customData": {
            "SessionSettings": lobby.get("sessionSettings", ""),
        },
        "version": 2,
        "props": {
            "countA": 1,
            "countB": 4,
            "gameMode": "None",
            "platform": "UniversalXPlay",
            "CrossplayOptOut": "false",
            "isDedicated": False,
        },
        "sideA": [
            lobby["host"]["userId"],
        ],
        "sideB": [p["userId"] for p in lobby["nonHosts"]],
    }


async def create_match_response(lobby_manager: LobbyManager, match_id: str, killed: bool = False):
    lobby = await lobby_manager.get_lobby_by_id(match_id)
    if not lobby:
        lobby = await lobby_manager.get_killed_lobby_by_id(match_id)
        killed = True
    if not lobby:
        return {}
    return {
        "matchId": match_id,
        "category": "live-138518-live:None:Windows:all::1:4:0:G:2",
        "creationDateTime": int(time.time()),
        "status": "CLOSED" if killed else "OPENED",
        "creator": lobby["host"]["userId"],
        "customData": {
            "SessionSettings": lobby.get("sessionSettings", ""),
        },
        "version": 2,
        "props": {
            "countA": 1,
            "countB": 4,
            "gameMode": "None",
            "platform": "UniversalXPlay",
            "CrossplayOptOut": "false",
            "isDedicated": False,
        },
        "sideA": [lobby["host"]["userId"]],
        "sideB": [p["userId"] for p in lobby.get("nonHosts", [])],
    }

@router.get("/match/{match_id}")
async def get_match(
    match_id: str,
    request: Request,
    redis = Depends(Redis.get_redis),
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
    redis = Depends(Redis.get_redis),
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
            return {"error": f"json error: {e!s}"}

        await lobby_manager.delete_match(match_id)
        return await MatchQueue.create_match_response(lobby_manager, match_id, killed=True)
    removed = await lobby_manager.remove_player_from_lobby(match_id, bhvr_session)
    if not removed:
        raise HTTPException(status_code=404, detail="Player not found in lobby")
    return {"status": "left", "matchId": match_id}

@router.post("/queue/cancel", status_code=204)
async def cancel_queue(
    request: Request,
    redis = Depends(Redis.get_redis),
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
async def earnPlayerXp(
    request: Request,
    db_users: Annotated[AsyncSession, Depends(get_user_session)],
    db_sessions: Annotated[AsyncSession, Depends(get_sessions_session)],
):
    bhvr_session = request.cookies.get("bhvrSession")
    if not bhvr_session:
        raise HTTPException(status_code=401, detail="No session cookie")

    user_id = await SessionManager.get_user_id_by_session(db_sessions, bhvr_session)
    if not user_id:
        raise HTTPException(status_code=401, detail="Session not found")

    payload = await request.json()
    match_time = int(payload.get("data", {}).get("matchTime", 0))
    is_first_match = bool(payload.get("data", {}).get("isFirstMatch", False))
    consecutive_match = float(payload.get("data", {}).get("consecutiveMatch", 1))
    emblem_qualities = payload.get("data", {}).get("emblemQualities", []) or []
    client_level_version = int(payload.get("data", {}).get("levelVersion", 34))
    player_type = str(payload.get("data", {}).get("playerType", "killer"))

    user_profile = await UserManager.get_user_profile(db=db_users, user_id=user_id)

    current_xp = int(getattr(user_profile, "current_xp", 0))
    current_level = int(getattr(user_profile, "level", 1))
    current_prestige = int(getattr(user_profile, "prestige_level", 0))
    total_xp_before = int(getattr(user_profile, "total_xp", 0))
    level_version_server = int(getattr(user_profile, "level_version", client_level_version))

    gain = Utils.calc_match_xp(
        match_time=match_time,
        is_first_match=is_first_match,
        player_type=player_type,
        consecutive_match=consecutive_match,
        emblem_qualities=emblem_qualities,
    )

    consecutive_bonus = int(
        max(
            0,
            gain["totalXpGained"] - (gain["baseMatchXp"] + gain["emblemsBonus"] + gain["firstMatchBonus"]),
        ),
    )

    after = Utils.process_xp_gain(
        current_xp=current_xp,
        current_level=current_level,
        current_prestige=current_prestige,
        gained_xp=int(gain["totalXpGained"]),
    )
    total_xp_after = total_xp_before + int(gain["totalXpGained"])

    rewards = Utils.calc_rewards(
        old_level=current_level,
        new_level=after["level"],
        old_prestige=current_prestige,
        new_prestige=after["prestigeLevel"],
    )

    await UserManager.update_user_profile(
        db=db_users,
        user_id=user_id,
        current_xp=after["currentXp"],
        current_xp_upper_bound=after["currentXpUpperBound"],
        level=after["level"],
        prestige_level=after["prestigeLevel"],
        total_xp=total_xp_after,
        level_version=level_version_server,
    )

    xp_breakdown = {
        "baseMatchXp": int(gain["baseMatchXp"]),
        "consecutiveMatchMultiplier": gain["consecutiveMatchMultiplier"],
        "emblemsBonus": int(gain["emblemsBonus"]),
        "firstMatchBonus": int(gain["firstMatchBonus"]),
    }
    if consecutive_bonus > 0:
        xp_breakdown["consecutiveMatchBonus"] = consecutive_bonus

    resp = {
        "extensionProgress": "Success",
        "levelInfo": {
            "currentXp": int(after["currentXp"]),
            "currentXpUpperBound": int(after["currentXpUpperBound"]),
            "level": int(after["level"]),
            "levelVersion": int(level_version_server),
            "prestigeLevel": int(after["prestigeLevel"]),
            "totalXp": int(total_xp_after),
        },
        "xpGainBreakdown": xp_breakdown,
    }

    # если есть награды — добавляем
    if rewards:
        resp["grantedCurrencies"] = rewards
        for r in rewards:
            await UserManager.update_wallet(db=db_users, user_id=user_id, currency=r["currency"], delta=r["balance"])

    return resp
