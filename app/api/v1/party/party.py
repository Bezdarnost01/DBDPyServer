from fastapi import APIRouter, Depends, HTTPException, Response, Request, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from schemas.config import settings
from schemas.party import PartyInviteRequest
from db.users import get_user_session
from db.sessions import get_sessions_session
from db.matchmaking import get_matchmaking_session
import random
from crud.party import PartyManager
import time
import logging
import json
import asyncio
from utils.decorators import log_call
from crud.sessions import SessionManager
from crud.users import UserManager
from utils.utils import Utils
from crud.websocket import ws_manager

logger = logging.getLogger(__name__) 
router = APIRouter(prefix=settings.api_prefix, tags=["Party"])

PLATFORM_ID = None
PARTY_OWNER_STATE = None
INCLUDE_STATE = None

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

    # now_ts = int(time.time())
    # expiry_time = now_ts + 60 * 60 * 2
    # auto_join_key = random.randint(1, 2**31 - 1)
    # player_limit = data.get("playerLimit", 4)
    # privacy_state = data.get("privacyState", "public")
    # game_specific_state = data.get("gameSpecificState", {})

    # preset = game_specific_state.get("_customGamePresetData", {})
    # out_preset = {
    #     "mapAvails": preset.get("_mapAvailabilities", []),
    #     "perkAvail": preset.get("_arePerkAvailable", True),
    #     "offeringAvail": preset.get("_areOfferingAvailable", True),
    #     "itemAvail": preset.get("_areItemAvailable", True),
    #     "itemAddonAvail": preset.get("_areItemAddonAvailable", True),
    #     "dlcContentAllowed": preset.get("_areDlcContentAllowed", True),
    #     "privateMatch": preset.get("_isPrivateMatch", True),
    #     "bots": {"_bots": []}
    # }

    # # Копируем остальные части gameSpecificState (просто скопировать и обновить только нужные ключи)
    # out_gss = dict(game_specific_state)
    # out_gss["_customGamePresetData"] = out_preset
    # out_gss.setdefault("_partySessionSettings", {})
    # out_gss.setdefault("_partyMatchmakingSettings", {})
    # out_gss["_partyMatchmakingSettings"].setdefault("_startMatchmakingDateTimestamp", -1)
    # out_gss["_partyMatchmakingSettings"].setdefault("_matchIncentive", 0)
    # out_gss["_partyMatchmakingSettings"].setdefault("_isInFinalCountdown", False)
    # out_gss["_partyMatchmakingSettings"].setdefault("_postMatchmakingTransitionId", 0)
    # out_gss.setdefault("_playerJoinOrder", [])
    # out_gss.setdefault("_playerChatIndices", {})
    # out_gss.setdefault("_gameType", 0)
    # out_gss.setdefault("_isCrowdPlay", False)
    # out_gss.setdefault("_isUsingDedicatedServer", True)
    # out_gss.setdefault("_chatHistory", {"_chatMessageHistory": [], "_playerNames": []})
    # out_gss.setdefault("_version", "icecream-hf1-2373437-live")
    # out_gss.setdefault("_lastUpdatedTime", 0)
    # out_gss.setdefault("_lastSentTime", 0)

    # # Собираем members (только хост)
    # members = [{"playerId": user_id}]

    # # Сохраняем в базу
    # party = await PartyManager.create_party(
    #     db=db_match,
    #     party_id=user_id,
    #     host_player_id=user_id,
    #     privacy_state=privacy_state,
    #     player_limit=player_limit,
    #     auto_join_key=auto_join_key,
    #     expiry_time=expiry_time,
    #     player_count=1,
    #     game_specific_state=out_gss,
    #     members=members
    # )

    # json_response = {
    #     "partyId": party.party_id,
    #     "hostPlayerId": party.host_player_id,
    #     "gameSpecificState": party.game_specific_state,
    #     "playerLimit": party.player_limit,
    #     "privacyState": party.privacy_state,
    #     "expiryTime": party.expiry_time,
    #     "autoJoinKey": party.auto_join_key,
    #     "playerCount": party.player_count,
    #     "members": party.members
    # }

    json_response = {
        "partyId": "0912a919-a897-4e37-8057-b0d7cf2adb66",
        "hostPlayerId": "f58654d6-15f4-4d25-b52a-9238ae696ebd",
        "privacyState": "public",
        "gameSpecificState": {
            "_customGamePresetData": {
            "_mapAvailabilities": [],
            "_arePerkAvailable": True,
            "_areOfferingAvailable": True,
            "_areItemAvailable": True,
            "_areItemAddonAvailable": True,
            "_areDlcContentAllowed": True,
            "_isPrivateMatch": True
            },
            "_partySessionSettings": {
            "_sessionId": "",
            "_gameSessionInfos": {},
            "_owningUserId": "",
            "_owningUserName": "",
            "_isDedicated": False,
            "_matchmakingTimestamp": -1
            },
            "_partyMatchmakingSettings": {
            "_playerIds": [],
            "_matchmakingState": "None"
            },
            "_playerChatIndices": {},
            "_gameType": 1,
            "_version": "live-277399-",
            "_lastUpdatedTime": -1667662445,
            "_lastSentTime": 32759
        },
        "playerLimit": 6,
        "expiryTime": 1754076448,
        "autoJoinKey": 838695663,
        "playerCount": 1,
        "members": [
            {
            "playerId": "f58654d6-15f4-4d25-b52a-9238ae696ebd"
            }
        ]
        }

    return JSONResponse(content=json_response, status_code=201)

@router.delete("/party/{party_id}")
async def delete_party(
    party_id: str,
    db_match: AsyncSession = Depends(get_matchmaking_session),
):
    result = await PartyManager.delete_party(db=db_match, party_id=party_id)
    return Response(status_code=204)
    
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
    db_users: AsyncSession = Depends(get_user_session),
    db_match: AsyncSession = Depends(get_matchmaking_session)
):
    data = await request.json()
    bhvr_session = request.cookies.get("bhvrSession")
    if not bhvr_session:
        raise HTTPException(status_code=401, detail="No session cookie")
    
    # party = await PartyManager.get_party(db_match, party_id)
    # if not party:
    #     raise HTTPException(404, "Party not found")
    
    # user_profile = await UserManager.get_user_profile(db_users, user_id=party.host_player_id)

    # data = await request.json()
    # privacy_state = party.privacy_state
    # game_specific_state = party.game_specific_state
    # player_limit = party.player_limit

    # preset = game_specific_state.get("_customGamePresetData", {})
    # out_preset = {
    #     "mapAvails": preset.get("_mapAvailabilities", []),
    #     "perkAvail": preset.get("_arePerkAvailable", True),
    #     "offeringAvail": preset.get("_areOfferingAvailable", True),
    #     "itemAvail": preset.get("_areItemAvailable", True),
    #     "itemAddonAvail": preset.get("_areItemAddonAvailable", True),
    #     "dlcContentAllowed": preset.get("_areDlcContentAllowed", True),
    #     "privateMatch": preset.get("_isPrivateMatch", True),
    #     "bots": {"_bots": []}
    # }
    # out_gss = dict(game_specific_state)
    # out_gss["_customGamePresetData"] = out_preset
    # out_gss.setdefault("_partySessionSettings", {})
    # out_gss.setdefault("_partyMatchmakingSettings", {})
    # out_gss["_partyMatchmakingSettings"].setdefault("_startMatchmakingDateTimestamp", -1)
    # out_gss["_partyMatchmakingSettings"].setdefault("_matchIncentive", 0)
    # out_gss["_partyMatchmakingSettings"].setdefault("_isInFinalCountdown", False)
    # out_gss["_partyMatchmakingSettings"].setdefault("_postMatchmakingTransitionId", 0)
    # out_gss.setdefault("_playerJoinOrder", [])
    # out_gss.setdefault("_playerChatIndices", {})
    # out_gss.setdefault("_gameType", 0)
    # out_gss.setdefault("_isCrowdPlay", False)
    # out_gss.setdefault("_isUsingDedicatedServer", True)
    # out_gss.setdefault("_chatHistory", {"_chatMessageHistory": [], "_playerNames": []})
    # out_gss.setdefault("_version", "icecream-hf1-2373437-live")
    # out_gss.setdefault("_lastUpdatedTime", 0)
    # out_gss.setdefault("_lastSentTime", 0)

    # updated_party = await PartyManager.update_party(
    #     db=db_match,
    #     party_id=party_id,
    #     privacy_state=privacy_state,
    #     player_limit=player_limit,
    #     game_specific_state=out_gss,
    # )

    # await PartyManager.add_player_to_join_order(
    #     db=db_match,
    #     party_id=party_id,
    #     player_id=party.host_player_id,
    # )

    # await PartyManager.set_platform_session_id(
    #     db=db_match,
    #     party_id=party_id,
    #     player_id=party.host_player_id,
    #     platform_session_id=f"1||{user_profile.steam_id}:7777|109775241482773159",
    # )

    # return {
    #     "partyId": updated_party.party_id,
    #     "hostPlayerId": updated_party.host_player_id,
    #     "gameSpecificState": updated_party.game_specific_state,
    #     "playerLimit": updated_party.player_limit,
    #     "privacyState": updated_party.privacy_state,
    #     "expiryTime": updated_party.expiry_time,
    #     "autoJoinKey": updated_party.auto_join_key,
    #     "playerCount": updated_party.player_count,
    #     "members": updated_party.members
    # }

    global PLATFORM_ID
    PLATFORM_ID = data.get("gameSpecificState").get("platformSessionId")

    json_response = {
    "partyId": "0912a919-a897-4e37-8057-b0d7cf2adb66",
    "hostPlayerId": "f58654d6-15f4-4d25-b52a-9238ae696ebd",
    "gameSpecificState": {
        "_customGamePresetData": {
        "_mapAvailabilities": [],
        "_arePerkAvailable": True,
        "_areOfferingAvailable": True,
        "_areItemAvailable": True,
        "_areItemAddonAvailable": True,
        "_areDlcContentAllowed": True,
        "_isPrivateMatch": True
        },
        "_partySessionSettings": {
        "_sessionId": "",
        "_gameSessionInfos": {},
        "_owningUserId": "",
        "_owningUserName": "",
        "_isDedicated": False,
        "_matchmakingTimestamp": -1
        },
        "_partyMatchmakingSettings": {
        "_playerIds": [],
        "_matchmakingState": "None"
        },
        "_playerChatIndices": {},
        "_gameType": 1,
        "_version": "live-277399-",
        "_lastUpdatedTime": -1667662445,
        "_lastSentTime": 32759,
        "platformSessionId": PLATFORM_ID
    },
    "expiryTime": 1754076268,
    "privacyState": "public",
    "autoJoinKey": 838695663,
    "playerLimit": 6,
    "members": [
        {
        "playerId": "f58654d6-15f4-4d25-b52a-9238ae696ebd"
        }
    ],
    "playerCount": 1
    }

    return JSONResponse(content=json_response, status_code=200)

@router.put("/party/player/{party_id}/state")
async def party_update_user_state(party_id: str,
                                  request: Request,
                                  db_match: AsyncSession = Depends(get_matchmaking_session),
                                  db_sessions = Depends(get_sessions_session),
                                  db_users = Depends(get_user_session)):
    
    global PARTY_OWNER_STATE
    bhvr_session = request.cookies.get("bhvrSession")
    if not bhvr_session:
        raise HTTPException(status_code=401, detail="No session cookie")
    
    user_id = await SessionManager.get_user_id_by_session(db=db_sessions, bhvr_session=bhvr_session)

    if not user_id:
        raise HTTPException(status_code=401, detail="Session not found")
    
    user_profile = await UserManager.get_user_profile(db=db_users, user_id=user_id)

    data = await request.json()

    # body = data.get("body")

    # await PartyManager.update_member_state(db=db_match, party_id=party_id, player_id=user_profile.user_id, state=body)
    # return Response(status_code=204)

    steam_id = data.get("body").get("_uniquePlayerId")

    if steam_id == "76561199106922308":
        PARTY_OWNER_STATE = data

    return(Response(status_code=204))

#я его мать ебал, доделать
@router.post("/party/{party_id}/invite")
async def party_player_invite(party_id: str, 
                              request: Request,
                              data: PartyInviteRequest,
                              db_sessions = Depends(get_sessions_session),
                              db_users = Depends(get_user_session)):
    expire_at = int(time.time() + 300)

    bhvr_session = request.cookies.get("bhvrSession")
    if not bhvr_session:
        raise HTTPException(status_code=401, detail="No session cookie")
    
    user_id = await SessionManager.get_user_id_by_session(db=db_sessions, bhvr_session=bhvr_session)

    if not user_id:
        raise HTTPException(status_code=401, detail="Session not found")
    
    user_profile = await UserManager.get_user_profile(db=db_users, user_id=user_id)

    websoket_data = {
    "topic": "userNotification",
    "data": {
        "inviterId": "0a6ffe7f-04d3-48e0-9222-4cf7370bac86",
        "inviterPlayerName": "Bezdarnost",
        "playerId": "4c9e085b-ec60-4734-a937-1a510f01c958",
        "playerName": "Yappa <3 trubochki",
        "fromRequestToJoin": False,
        "timestamp": int(time.time())
    },
    "event": "partyOtherPlayerInvite"
    }

    await ws_manager.send_to_user("0a6ffe7f-04d3-48e0-9222-4cf7370bac86", message=websoket_data)

    return {"partyId": party_id,"expireAt": expire_at}

    # invited_it = data.players[0]

    # response_data = {
    #     "topic": "userNotification",
    #     "data": {
    #         "inviterId": user_profile.user_id,
    #         "inviterPlayerName": user_profile.user_name,
    #         "partyId": party_id,
    #         "fromRequestToJoin": False,
    #         "expireAt": expire_at,
    #         "timestamp": time.time()
    #     },
    #     "event": "partyInvite"
    # }

    # await ws_manager.send_to_user(invited_it, message=response_data)

    # return {"partyId": party_id,"expireAt": expire_at}

@router.get("/party/player/{party_id}")
async def party_get_include_state(party_id: str):
    return Response(status_code=200)

@router.get("/party/{party_id}")
async def get_party(
    party_id: str,
    request: Request,
    includeState: bool = Query(False, alias="includeState"),
    db: AsyncSession = Depends(get_matchmaking_session),
):
    # party = await PartyManager.get_party(db, party_id)
    # if not party:
    #     raise HTTPException(404, "Party not found")

    # payload = {
    #     "partyId":      party.party_id,
    #     "playerLimit":  party.player_limit,
    #     "privacyState": party.privacy_state,
    #     "gameSpecificState": party.game_specific_state,
    #     "autoJoinKey":  party.auto_join_key,
    #     "hostPlayerId": party.host_player_id,
    #     "expiryTime":   party.expiry_time,
    #     "members":      party.members,
    #     "playerCount":  party.player_count,
    # }

    # json_bytes = json.dumps(
    #     payload,
    #     ensure_ascii=False,
    #     separators=(",", ":")
    # ).encode("utf-8")

    # return Response(content=json_bytes, media_type="application/json")

    # head = PARTY_OWNER_STATE.get("body", {}).get("_customizationMesh", [None])[0]
    # torsoOrBody = PARTY_OWNER_STATE.get("body", {}).get("_customizationMesh", [None])[1]
    # legsOrWeapon = PARTY_OWNER_STATE.get("body", {}).get("_customizationMesh", [None])[2]
    # data = PARTY_OWNER_STATE.get("body")
    global INCLUDE_STATE

    json_response = {
    "partyId": "f58654d6-15f4-4d25-b52a-9238ae696ebd",
    "playerLimit": 6,
    "privacyState": "friends",
    "gameSpecificState": {
        "_customGamePresetData": {
        "mapAvails": [],
        "perkAvail": True,
        "offeringAvail": True,
        "itemAvail": True,
        "itemAddonAvail": True,
        "dlcContentAllowed": True,
        "idleCrowsAllowed": True,
        "privateMatch": True,
        "bots": {
            "_bots": []
        }
        },
        "_partySessionSettings": {
        "_sessionId": "",
        "_gameSessionInfos": {},
        "_owningUserId": "",
        "_owningUserName": "",
        "_isDedicated": False,
        "_matchmakingTimestamp": -1
        },
        "_partyMatchmakingSettings": {
        "_playerIds": [],
        "_matchmakingState": "None",
        "_startMatchmakingDateTimestamp": -1,
        "_matchIncentive": 0,
        "_modeBonus": 0,
        "_currentETASeconds": -1,
        "_isInFinalCountdown": False,
        "_postMatchmakingTransitionId": 0,
        "_playWhileYouWaitLobbyState": "Inactive",
        "_autoReadyEnabled": "None",
        "_isPriorityQueue": False,
        "_isPlayWhileYouWaitQueuePossible": False
        },
        "_playerJoinOrder": [
        "f58654d6-15f4-4d25-b52a-9238ae696ebd",
        "4c9e085b-ec60-4734-a937-1a510f01c958"
        ],
        "_playerChatIndices": {
        "f58654d6-15f4-4d25-b52a-9238ae696ebd": 0,
        "4c9e085b-ec60-4734-a937-1a510f01c958": 1
        },
        "_gameType": 0,
        "_playerRole": "VE_Camper",
        "_isCrowdPlay": False,
        "_isUsingDedicatedServer": True,
        "_chatHistory": {
        "_chatMessageHistory": [
            {
            "type": "SystemPlayerJoinedParty",
            "playerMirrorsId": "4c9e085b-ec60-4734-a937-1a510f01c958",
            "message": ""
            }
        ],
        "_chatPlayerRoles": [
            {
            "playerMirrorsId": "f58654d6-15f4-4d25-b52a-9238ae696ebd",
            "playerName": "DBDPUBSERV",
            "anonymousPlayerName": "Дэвид Кинг",
            "playerRole": 0
            }
        ]
        },
        "_version": "live-277399-",
        "_lastUpdatedTime": 1751997607,
        "_lastSentTime": 1751997607
    },
    "autoJoinKey": 838695663,
    "hostPlayerId": "f58654d6-15f4-4d25-b52a-9238ae696ebd",
    "expiryTime": 1752001202,
    "members": [
        {
        "playerId": "f58654d6-15f4-4d25-b52a-9238ae696ebd",
        "state": {
            "body": {
            "_playerCustomization": {
                "_equippedCustomization": {
                "head": "DK_Head002",
                "torsoOrBody": "DK_Torso02_KOEvent01",
                "legsOrWeapon": "DK_Legs002_02"
                },
                "_equippedCharms": []
            },
            "_playerName": "DBDPUBSERV",
            "_platformSessionId": "1||76561199234371478:7777|109775241482773159",
            "_uniquePlayerId": "76561199234371478",
            "_playerRank": 20,
            "_characterLevel": 25,
            "_prestigeLevel": 1,
            "_gameRole": 2,
            "_characterId": 2,
            "_powerId": "Item_Camper_MedKit03",
            "_location": 1,
            "_queueDelayIteration": 0,
            "_ready": False,
            "_crossplayAllowed": True,
            "_playerPlatform": "steam",
            "_playerProvider": "steam",
            "_matchId": "",
            "_postMatchmakingRole": "None",
            "_postMatchmakingState": "None",
            "_roleRequested": 0,
            "_anonymousSuffix": 1,
            "_isStateInitialized": True,
            "_characterClass": "_LOCKED_",
            "_disconnectionPenaltyEndOfBan": 0
            }
        }
        },
        {
        "playerId": "4c9e085b-ec60-4734-a937-1a510f01c958"
        }
    ],
    "playerCount": 2
    }

    INCLUDE_STATE = json_response

    return JSONResponse(content=json_response, status_code=200)

@router.post("/party/{party_id}/join")
async def join_party(
    party_id: str,
    request: Request,
    autoJoin: bool = Query(False, alias="autoJoin"),
    key: int | None = Query(None, alias="key"),
    db: AsyncSession = Depends(get_matchmaking_session),
    db_users: AsyncSession = Depends(get_user_session),
    db_sessions: AsyncSession = Depends(get_sessions_session)
):
    # party = await PartyManager.get_party(db, party_id)
    # if not party:
    #     raise HTTPException(404, "Party not found")

    # if autoJoin and key is not None and party.auto_join_key != key:
    #     raise HTTPException(403, "Invalid autoJoinKey")

    # if party.expiry_time and party.expiry_time < int(time.time()):
    #     raise HTTPException(404, "Party expired")

    # bhvr_session = request.cookies.get("bhvrSession")
    # if not bhvr_session:
    #     raise HTTPException(status_code=401, detail="No session cookie")

    # user_id = await SessionManager.get_user_id_by_session(db_sessions, bhvr_session)
    # if not user_id:
    #     raise HTTPException(status_code=401, detail="Session not found")

    # await PartyManager.add_player_to_join_order(
    #     db=db,
    #     party_id=party_id,
    #     player_id=user_id,
    # )

    # user_profile = await UserManager.get_user_profile(db=db_users, user_id=user_id)

    # await PartyManager.set_platform_session_id(
    #     db=db,
    #     party_id=party_id,
    #     player_id=user_id,
    #     platform_session_id=f"1||{user_profile.steam_id}:7777|109775241482773159",
    # )

    # party_json = {
    #     "partyId":      party.party_id,
    #     "playerLimit":  party.player_limit,
    #     "privacyState": party.privacy_state,
    #     "gameSpecificState": party.game_specific_state,
    #     "autoJoinKey":  party.auto_join_key,
    #     "hostPlayerId": party.host_player_id,
    #     "expiryTime":   party.expiry_time,
    #     "members":      party.members,
    #     "playerId":     user_id,
    #     "playerCount":  party.player_count + 1,
    # }

    # return {"partyDetails": party_json}
    global INCLUDE_STATE
    return INCLUDE_STATE

@router.post("/test/party/{user_id}")
async def test_party_invite(user_id: str, 
                              request: Request,
                              data: PartyInviteRequest,
                              db_sessions = Depends(get_sessions_session),
                              db_users = Depends(get_user_session)):
    expire_at = int(time.time() + 300)
    response_data = {
        "topic": "userNotification",
        "data": {
            "inviterId": user_id,
            "inviterPlayerName": "Bezdarnost",
            "partyId": user_id,
            "fromRequestToJoin": False,
            "expireAt": expire_at,
            "timestamp": time.time()
        },
        "event": "partyInvite"
    }

    await ws_manager.send_to_user(user_id, message=response_data)