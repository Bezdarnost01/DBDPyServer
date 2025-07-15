from fastapi import APIRouter, Depends, HTTPException, Response, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession
from schemas.config import settings
from db.users import get_user_session
from db.sessions import get_sessions_session
from db.matchmaking import get_matchmaking_session
import random
from crud.party import PartyManager
import time
import asyncio
from crud.sessions import SessionManager
from crud.users import UserManager
from utils.utils import Utils

router = APIRouter(prefix=settings.api_prefix, tags=["Party"])

@router.get("/party")
async def get_party(includeState: bool = Query(False)):
    if includeState == True:
        return {}
    
@router.post("/party")
async def create_party(
    data: dict,
    request: Request,
    db_match: AsyncSession = Depends(get_matchmaking_session),
    db_sessions: AsyncSession = Depends(get_sessions_session)
):
    bhvr_session = request.cookies.get("bhvrSession")
    if not bhvr_session:
        raise HTTPException(status_code=401, detail="No session cookie")
    user_id = await SessionManager.get_user_id_by_session(db_sessions, bhvr_session)
    if not user_id:
        raise HTTPException(status_code=401, detail="Session not found")

    now_ts = int(time.time())
    expiry_time = now_ts + 60 * 60 * 2
    auto_join_key = random.randint(100_000_000, 999_999_999)
    player_limit = data.get("playerLimit", 4)
    privacy_state = data.get("privacyState", "public")
    game_specific_state = data.get("gameSpecificState", {})

    preset = game_specific_state.get("_customGamePresetData", {})
    out_preset = {
        "mapAvails": preset.get("_mapAvailabilities", []),
        "perkAvail": preset.get("_arePerkAvailable", True),
        "offeringAvail": preset.get("_areOfferingAvailable", True),
        "itemAvail": preset.get("_areItemAvailable", True),
        "itemAddonAvail": preset.get("_areItemAddonAvailable", True),
        "dlcContentAllowed": preset.get("_areDlcContentAllowed", True),
        "privateMatch": preset.get("_isPrivateMatch", True),
        "bots": {"_bots": []}
    }

    # Копируем остальные части gameSpecificState (просто скопировать и обновить только нужные ключи)
    out_gss = dict(game_specific_state)
    out_gss["_customGamePresetData"] = out_preset
    out_gss.setdefault("_partySessionSettings", {})
    out_gss.setdefault("_partyMatchmakingSettings", {})
    out_gss["_partyMatchmakingSettings"].setdefault("_startMatchmakingDateTimestamp", -1)
    out_gss["_partyMatchmakingSettings"].setdefault("_matchIncentive", 0)
    out_gss["_partyMatchmakingSettings"].setdefault("_isInFinalCountdown", False)
    out_gss["_partyMatchmakingSettings"].setdefault("_postMatchmakingTransitionId", 0)
    out_gss.setdefault("_playerJoinOrder", [])
    out_gss.setdefault("_playerChatIndices", {})
    out_gss.setdefault("_gameType", 0)
    out_gss.setdefault("_isCrowdPlay", False)
    out_gss.setdefault("_isUsingDedicatedServer", True)
    out_gss.setdefault("_chatHistory", {"_chatMessageHistory": [], "_playerNames": []})
    out_gss.setdefault("_version", "icecream-hf1-2373437-live")
    out_gss.setdefault("_lastUpdatedTime", 0)
    out_gss.setdefault("_lastSentTime", 0)

    # Собираем members (только хост)
    members = [{"playerId": user_id}]

    # Сохраняем в базу
    party = await PartyManager.create_party(
        db=db_match,
        party_id=user_id,
        host_player_id=user_id,
        privacy_state=privacy_state,
        player_limit=player_limit,
        auto_join_key=auto_join_key,
        expiry_time=expiry_time,
        player_count=1,
        game_specific_state=out_gss,
        members=members
    )

    return {
        "partyId": party.party_id,
        "hostPlayerId": party.host_player_id,
        "gameSpecificState": party.game_specific_state,
        "playerLimit": party.player_limit,
        "privacyState": party.privacy_state,
        "expiryTime": party.expiry_time,
        "autoJoinKey": party.auto_join_key,
        "playerCount": party.player_count,
        "members": party.members
    }

@router.delete("/party/{party_id}")
async def delete_party(
    party_id: str,
    db_match: AsyncSession = Depends(get_matchmaking_session),
):
    result = await PartyManager.delete_party(db=db_match, party_id=party_id)
    if not result:
        raise HTTPException(status_code=404, detail="Party not found")
    return {"result": "deleted"}
    
@router.delete("/party/leave")
async def leave_party(request: Request, disband: bool = Query(False), 
                      db_sessions: AsyncSession = Depends(get_sessions_session), 
                      db_match: AsyncSession = Depends(get_matchmaking_session)
):
    if disband == True:
        bhvr_session = request.cookies.get("bhvrSession")
        if not bhvr_session:
            raise HTTPException(status_code=401, detail="No session cookie")
        user_id = await SessionManager.get_user_id_by_session(db_sessions, bhvr_session)
        if not user_id:
            raise HTTPException(status_code=401, detail="Session not found")
        
        party = await PartyManager.get_player_party(db=db_match, player_id=user_id)

        if not party:
            raise HTTPException(status_code=404, detail="Party not found")

        await PartyManager.remove_member(db=db_match, party_id=party.party_id, player_id=user_id)
        
        return {}
    
@router.put("/party/{party_id}")
async def update_party(
    request: Request, 
    party_id: str, 
    db_sessions: AsyncSession = Depends(get_sessions_session), 
    db_match: AsyncSession = Depends(get_matchmaking_session)
):
    bhvr_session = request.cookies.get("bhvrSession")
    if not bhvr_session:
        raise HTTPException(status_code=401, detail="No session cookie")
    
    data = await request.json()
    privacy_state = data.get("privacyState", "public")
    game_specific_state = data.get("gameSpecificState", {})
    player_limit = data.get("playerLimit", 4)

    party = await PartyManager.get_party(db_match, party_id)
    if not party:
        raise HTTPException(404, "Party not found")

    preset = game_specific_state.get("_customGamePresetData", {})
    out_preset = {
        "mapAvails": preset.get("_mapAvailabilities", []),
        "perkAvail": preset.get("_arePerkAvailable", True),
        "offeringAvail": preset.get("_areOfferingAvailable", True),
        "itemAvail": preset.get("_areItemAvailable", True),
        "itemAddonAvail": preset.get("_areItemAddonAvailable", True),
        "dlcContentAllowed": preset.get("_areDlcContentAllowed", True),
        "privateMatch": preset.get("_isPrivateMatch", True),
        "bots": {"_bots": []}
    }
    out_gss = dict(game_specific_state)
    out_gss["_customGamePresetData"] = out_preset
    out_gss.setdefault("_partySessionSettings", {})
    out_gss.setdefault("_partyMatchmakingSettings", {})
    out_gss["_partyMatchmakingSettings"].setdefault("_startMatchmakingDateTimestamp", -1)
    out_gss["_partyMatchmakingSettings"].setdefault("_matchIncentive", 0)
    out_gss["_partyMatchmakingSettings"].setdefault("_isInFinalCountdown", False)
    out_gss["_partyMatchmakingSettings"].setdefault("_postMatchmakingTransitionId", 0)
    out_gss.setdefault("_playerJoinOrder", [])
    out_gss.setdefault("_playerChatIndices", {})
    out_gss.setdefault("_gameType", 0)
    out_gss.setdefault("_isCrowdPlay", False)
    out_gss.setdefault("_isUsingDedicatedServer", True)
    out_gss.setdefault("_chatHistory", {"_chatMessageHistory": [], "_playerNames": []})
    out_gss.setdefault("_version", "icecream-hf1-2373437-live")
    out_gss.setdefault("_lastUpdatedTime", 0)
    out_gss.setdefault("_lastSentTime", 0)

    updated_party = await PartyManager.update_party(
        db=db_match,
        party_id=party_id,
        privacy_state=privacy_state,
        player_limit=player_limit,
        game_specific_state=out_gss,
    )

    return {
        "partyId": updated_party.party_id,
        "hostPlayerId": updated_party.host_player_id,
        "gameSpecificState": updated_party.game_specific_state,
        "playerLimit": updated_party.player_limit,
        "privacyState": updated_party.privacy_state,
        "expiryTime": updated_party.expiry_time,
        "autoJoinKey": updated_party.auto_join_key,
        "playerCount": updated_party.player_count,
        "members": updated_party.members
    }

@router.put("/party/player/{party_id}/state")
async def party_update_user_state(party_id: str):
    return Response(status_code=204)