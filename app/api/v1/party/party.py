from fastapi import APIRouter, Depends, HTTPException, Response, Request, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from schemas.config import settings
from schemas.party import PartyInviteRequest
from db.users import get_user_session
from db.sessions import get_sessions_session
from db.matchmaking import get_matchmaking_session
import random
import time
import logging
import json
import asyncio
import uuid
from utils.decorators import log_call
from crud.sessions import SessionManager
from crud.users import UserManager
from utils.utils import Utils
from typing import Any, Dict, Optional
import copy
from crud.websocket import ws_manager

logger = logging.getLogger(__name__) 
router = APIRouter(prefix=settings.api_prefix, tags=["Party"])

PARTIES: Dict[str, Dict[str, Any]] = {}        # party_id -> party
PARTY_ID_BY_HOST: Dict[str, str] = {}          # hostPlayerId -> party_id
PLAYER_STATES: Dict[str, Dict[str, Any]] = {}  # playerId -> state["body"]
MATCHES: Dict[str, Dict[str, Any]] = {} 

# --- deps you already имеешь ---
# from deps import get_matchmaking_session, get_sessions_session
# from sessions import SessionManager

# ---------- helpers ----------
def _norm_id(pid: Optional[str]) -> str:
    return (pid or "").strip()

def _deep_update(dst: Dict[str, Any], src: Dict[str, Any]) -> Dict[str, Any]:
    for k, v in src.items():
        if isinstance(v, dict) and isinstance(dst.get(k), dict):
            _deep_update(dst[k], v)
        else:
            dst[k] = v
    return dst

async def _get_current_user_id(request: Request, db_sessions: AsyncSession) -> str:
    bhvr_session = request.cookies.get("bhvrSession")
    if not bhvr_session:
        raise HTTPException(status_code=401, detail="No session cookie")
    user_id = await SessionManager.get_user_id_by_session(db_sessions, bhvr_session)
    if not user_id:
        raise HTTPException(status_code=401, detail="Session not found")
    return user_id

def _recount_player_count(p: Dict[str, Any]) -> None:
    p["playerCount"] = len(p.get("members", []))

def _random_u32() -> int:
    return uuid.uuid4().int & ((1 << 32) - 1)

def _find_party_by_id(pid: str) -> Optional[Dict[str, Any]]:
    pid = _norm_id(pid)
    party = PARTIES.get(pid)
    if party:
        return party
    for p in PARTIES.values():
        if _norm_id(p.get("partyId")) == pid:
            return p
    return None

def _find_player_party(user_id: str):
    """Вернёт (party_id, party) для игрока или (None, None)."""
    pid = PARTY_ID_BY_HOST.get(user_id)
    if pid and pid in PARTIES:
        party = PARTIES[pid]
        if any(m.get("playerId") == user_id for m in party.get("members", [])):
            return pid, party
    for p_id, p in PARTIES.items():
        if any(m.get("playerId") == user_id for m in p.get("members", [])):
            return p_id, p
    return None, None

async def _broadcast_party_event(party: dict, payload: dict):
    """Разослать payload всем участникам партии (и хосту)."""
    targets = {m.get("playerId") for m in party.get("members", []) if m.get("playerId")}
    host_id = party.get("hostPlayerId")
    if host_id:
        targets.add(host_id)
    await asyncio.gather(
        *(ws_manager.send_to_user(uid, payload) for uid in targets),
        return_exceptions=True
    )

def _update_state_for_match(
    player_id: str,
    match_id: str,
    role: str,                       # "Host" | "Client"
    state: str = "InProgress",       # "InProgress" на create
    make_ready: bool = True
) -> dict:
    """
    Обновляет PLAYER_STATES[player_id] под матч и возвращает body.
    Роль/статус задаются явно (Host/Client, InProgress/Completed/...).
    """
    st = PLAYER_STATES.get(player_id) or {}
    st = st.copy() if isinstance(st, dict) else {}

    # минимальные и косметические дефолты (как в примере)
    st.setdefault("_isStateInitialized", True)
    st.setdefault("_playerPlatform", "steam")
    st.setdefault("_playerProvider", "steam")
    st.setdefault("_uniquePlayerId", "")
    st.setdefault("_playerName", str(player_id))
    st.setdefault("_playerCustomization", {
        "_equippedCustomization": {
            "head": "C_Head01",
            "torsoOrBody": "C_Torso01",
            "legsOrWeapon": "C_Legs01"
        },
        "_equippedCharms": []
    })
    st.setdefault("_queueDelayIteration", 1)
    st.setdefault("_characterClass", "_LOCKED_")
    st.setdefault("_disconnectionPenaltyEndOfBan", 0)

    # апдейты под матч
    st["_matchId"] = match_id
    st["_postMatchmakingRole"] = "Host" if role == "Host" else "Client"
    st["_postMatchmakingState"] = state
    if make_ready:
        st["_ready"] = True

    PLAYER_STATES[player_id] = st
    return st

async def _broadcast_member_state_change(party: dict, player_id: str, state_body: dict) -> None:
    """
    Рассылает всем участникам партии (и хосту) событие 'partyMemberStateChange'
    о смене состояния указанного игрока.
    """
    ws_msg = {
        "topic": "userNotification",
        "data": {
            "partyId": party["partyId"],
            "playerId": player_id,
            "state": {"body": state_body or {}},
            "timestamp": int(time.time() * 1000),
        },
        "event": "partyMemberStateChange",
    }
    await _broadcast_party_event(party, ws_msg)

async def _broadcast_party_state_snapshot(party: dict, exclude_host: bool = False):
    """
    Шлём 'partyStateChange' всем участникам (при желании без хоста),
    собирая payload ТОЛЬКО из объекта party + кэша PLAYER_STATES.
    """
    # список адресатов
    targets = [m.get("playerId") for m in party.get("members", []) if m.get("playerId")]
    if exclude_host:
        host_id = party.get("hostPlayerId")
        targets = [t for t in targets if t != host_id]

    for uid in targets:
        st = PLAYER_STATES.get(uid) or {}
        player_name = st.get("_playerName") or str(uid)
        role_int = _safe_int(st.get("_gameRole", 1), 1)

        # строим "чистый" partyStateChange по текущему состоянию party
        evt = _build_party_state_change_event(
            party=party,
            joining_user_id=uid,       # для чат/ролей подставляем адресата
            player_name=player_name,
            player_role_int=role_int,
        )
        await ws_manager.send_to_user(uid, evt)

# ---------- PARTY endpoints ----------

@router.get("/party")
async def get_party(
    includeState: bool = Query(False),
    includeMemberStates: bool = Query(False),
    request: Request = None,
    db_sessions: AsyncSession = Depends(get_sessions_session),
):
    """
    includeState=true -> {"playerIsInParty": bool, "currentPartyId": str|None}
    includeMemberStates=true -> в ответе партий добавятся "memberStates": {playerId: {"body": ...}}
    """
    if includeState:
        user_id = await _get_current_user_id(request, db_sessions)
        pid = PARTY_ID_BY_HOST.get(user_id)
        if pid and pid in PARTIES:
            return {"playerIsInParty": True, "currentPartyId": pid}
        for p_id, p in PARTIES.items():
            if any(m.get("playerId") == user_id for m in p.get("members", [])):
                return {"playerIsInParty": True, "currentPartyId": p_id}
        return {"playerIsInParty": False, "currentPartyId": None}

    parties = list(PARTIES.values())
    if includeMemberStates:
        enriched = []
        for p in parties:
            p_copy = copy.deepcopy(p)
            member_states = {
                m["playerId"]: {"body": PLAYER_STATES.get(m["playerId"])}
                for m in p_copy.get("members", [])
                if m.get("playerId")
            }
            p_copy["memberStates"] = member_states
            enriched.append(p_copy)
        return enriched

    return parties

@router.get("/party/{party_id}")
async def get_party_by_id(
    party_id: str,
    includeMemberStates: bool = Query(False),
    request: Request = None,
    db_sessions: AsyncSession = Depends(get_sessions_session),
):
    party = _find_party_by_id(party_id)
    if not party:
        raise HTTPException(status_code=404, detail="Party not found")

    # Пытаемся определить текущего пользователя — чтобы отправить ему WS
    user_id = None
    try:
        if request is not None:
            user_id = await _get_current_user_id(request, db_sessions)
    except HTTPException:
        user_id = None

    if user_id:
        # Имя/роль берём из кэшированного STATE (если нет — дефолты)
        st = PLAYER_STATES.get(user_id) or {}
        player_name = st.get("_playerName") or "---"
        role_int = _safe_int(st.get("_gameRole", 1), 1)

        # Готовим event "partyStateChange" на основе текущей party
        evt = _build_party_state_change_event(
            party=party,
            joining_user_id=user_id,
            player_name=player_name,
            player_role_int=role_int,
        )

        # Патчим под требования примера:
        # 1) dedicated = true
        evt["data"]["state"]["gameSpecificState"]["_isUsingDedicatedServer"] = True
        # 2) актуальный список игроков в _partyMatchmakingSettings._playerIds
        evt["data"]["state"]["gameSpecificState"]["_partyMatchmakingSettings"]["_playerIds"] = [
            m.get("playerId") for m in party.get("members", []) if m.get("playerId")
        ]
        # 3) при желании можно форснуть _gameType=1 (как в примере)
        if "_gameType" not in evt["data"]["state"]["gameSpecificState"]:
            evt["data"]["state"]["gameSpecificState"]["_gameType"] = 1

        # Шлём только текущему игроку
        await ws_manager.send_to_user(user_id, evt)

    # HTTP-ответ — как раньше
    if not includeMemberStates:
        return party

    logger.debug(user_id)
    p_copy = copy.deepcopy(party)
    member_states = {
        m["playerId"]: {"body": PLAYER_STATES.get(m["playerId"])}
        for m in p_copy.get("members", [])
        if m.get("playerId")
    }
    p_copy["memberStates"] = member_states
    return p_copy

@router.post("/party")
async def create_party(
    data: dict,
    request: Request,
    db_match: AsyncSession = Depends(get_matchmaking_session),
    db_sessions: AsyncSession = Depends(get_sessions_session),
):
    user_id = await _get_current_user_id(request, db_sessions)

    existing = PARTY_ID_BY_HOST.get(user_id)
    if existing and existing in PARTIES:
        return PARTIES[existing]

    party_id = str(uuid.uuid4())
    gs = data.get("gameSpecificState", {})
    if isinstance(gs, dict):
        ver = gs.get("_version")
        if isinstance(ver, str) and ver.endswith("-"):
            gs["_version"] = ver

    party = {
        "partyId": party_id,
        "hostPlayerId": user_id,
        "privacyState": data.get("privacyState", "public"),
        "gameSpecificState": gs if isinstance(gs, dict) else {},
        "playerLimit": int(data.get("playerLimit", 6)),
        "expiryTime": int(time.time()) + 3600,
        "autoJoinKey": _random_u32(),
        "members": [{"playerId": user_id}],
    }
    _recount_player_count(party)

    PARTIES[party_id] = party
    PARTY_ID_BY_HOST[user_id] = party_id
    return party


@router.put("/party/{party_id}")
async def update_party(
    party_id: str,
    data: dict,
    request: Request,
    db_sessions: AsyncSession = Depends(get_sessions_session),
):
    user_id = await _get_current_user_id(request, db_sessions)

    party = _find_party_by_id(party_id)
    if not party:
        raise HTTPException(status_code=404, detail="Party not found")

    if user_id != party.get("hostPlayerId"):
        raise HTTPException(status_code=403, detail="Only host can update the party")

    updated = copy.deepcopy(party)

    if "privacyState" in data:
        updated["privacyState"] = data["privacyState"]

    incoming_gs = data.get("gameSpecificState")
    if isinstance(incoming_gs, dict):
        ver = incoming_gs.get("_version")
        if isinstance(ver, str) and ver.endswith("-"):
            incoming_gs["_version"] = ver
        if "gameSpecificState" not in updated or not isinstance(updated["gameSpecificState"], dict):
            updated["gameSpecificState"] = {}
        _deep_update(updated["gameSpecificState"], incoming_gs)

        psi = updated["gameSpecificState"].get("platformSessionId")
        if psi is not None and (not isinstance(psi, str) or not psi.strip()):
            raise HTTPException(status_code=422, detail="Invalid platformSessionId")

    if "playerLimit" in data:
        try:
            updated["playerLimit"] = int(data["playerLimit"])
        except Exception:
            raise HTTPException(status_code=422, detail="Invalid playerLimit")

    if "expiryTime" in data:
        try:
            updated["expiryTime"] = int(data["expiryTime"])
        except Exception:
            raise HTTPException(status_code=422, detail="Invalid expiryTime")

    _recount_player_count(updated)

    final_key = _norm_id(updated["partyId"])
    PARTIES[final_key] = updated
    PARTY_ID_BY_HOST[updated["hostPlayerId"]] = final_key
    return updated

@router.delete("/party/leave")
async def leave_party(
    request: Request,
    disband: bool = Query(False),
    db_sessions: AsyncSession = Depends(get_sessions_session),
):
    user_id = await _get_current_user_id(request, db_sessions)

    party_id, party = _find_player_party(user_id)
    if not party:
        return {}

    is_host = party.get("hostPlayerId") == user_id

    if disband:
        if not is_host:
            raise HTTPException(status_code=403, detail="Only host can disband the party")
        PARTIES.pop(party_id, None)
        if PARTY_ID_BY_HOST.get(user_id) == party_id:
            PARTY_ID_BY_HOST.pop(user_id, None)
        return {}

    members = party.get("members", [])
    new_members = [m for m in members if m.get("playerId") != user_id]
    party["members"] = new_members
    _recount_player_count(party)

    if is_host:
        if not new_members:
            PARTIES.pop(party_id, None)
            if PARTY_ID_BY_HOST.get(user_id) == party_id:
                PARTY_ID_BY_HOST.pop(user_id, None)
            return {}
        else:
            new_host = new_members[0]["playerId"]
            party["hostPlayerId"] = new_host
            if PARTY_ID_BY_HOST.get(user_id) == party_id:
                PARTY_ID_BY_HOST.pop(user_id, None)
            PARTY_ID_BY_HOST[new_host] = party_id

    PARTIES[party_id] = party
    return {}

# ---------- PLAYER STATE endpoints ----------

@router.put("/party/player/{player_id}/state")
async def put_player_state(
    player_id: str,
    payload: Dict[str, Any],  # ожидаем {"body": {...}}
    request: Request,
    db_sessions: AsyncSession = Depends(get_sessions_session),
):
    """
    Игрок обновляет только свой state. После апдейта шлём WS
    всем участникам партии событие 'partyMemberStateChange'
    с новым state.body.
    """
    user_id = await _get_current_user_id(request, db_sessions)
    if user_id != player_id:
        raise HTTPException(status_code=403, detail="You can update only your own state")

    if not isinstance(payload, dict) or "body" not in payload or not isinstance(payload["body"], dict):
        raise HTTPException(status_code=422, detail='Expected JSON: {"body": {...}}')

    # сохранить состояние
    PLAYER_STATES[player_id] = payload["body"]

    # найти партию игрока
    party_id, party = _find_player_party(player_id)
    if party:
        # сформировать WS-сообщение для всех участников
        ws_msg = {
            "topic": "userNotification",
            "data": {
                "partyId": party["partyId"],
                "playerId": player_id,
                "state": {"body": PLAYER_STATES[player_id]},
                "timestamp": int(time.time() * 1000),
            },
            "event": "partyMemberStateChange",
        }
        await _broadcast_party_event(party, ws_msg)
    else:
        # игрок не состоит в партии — просто возвращаем обновлённый state
        logger.debug(f"put_player_state: player {player_id} is not in a party; skip WS broadcast")

    return {"body": PLAYER_STATES[player_id]}

@router.delete("/party/{party_id}")
async def delete_party_by_id(
    party_id: str,
    request: Request,
    db_sessions: AsyncSession = Depends(get_sessions_session),
):
    user_id = await _get_current_user_id(request, db_sessions)

    party = _find_party_by_id(party_id)
    if not party:
        raise HTTPException(status_code=404, detail="Party not found")

    host_id = party.get("hostPlayerId")
    if user_id != host_id:
        raise HTTPException(status_code=403, detail="Only host can delete the party")

    final_key = _norm_id(party.get("partyId"))
    PARTIES.pop(final_key, None)
    if PARTY_ID_BY_HOST.get(host_id) == final_key:
        PARTY_ID_BY_HOST.pop(host_id, None)

    return {}

def _snowflake_ms() -> int:
    """Генерим число наподобие 'сноуфлейка': основано на времени + немного рандома."""
    epoch_ms = 1577836800000  # 2020-01-01
    now_ms = int(time.time() * 1000)
    return ((now_ms - epoch_ms) << 22) | random.getrandbits(12)

def _make_platform_session_id(steam_id: str) -> str:
    return f"1||{steam_id}:7777|{_snowflake_ms()}"
def _role_int_to_name(v: int | None) -> str:
    # 1 — survivor (Camper), 2 — killer (Slasher)
    if v == 2:
        return "VE_Slasher"
    if v == 1:
        return "VE_Camper"
    return "VE_Unknown"

def _safe_int(x, default: int) -> int:
    try:
        return int(x)
    except Exception:
        return default

def _append_join_order_and_indices(party: dict, joining_user_id: str):
    gs = party.setdefault("gameSpecificState", {})
    join_order = gs.setdefault("_playerJoinOrder", [])
    # добавим только если нет
    if joining_user_id not in join_order:
        join_order.append(joining_user_id)

    members = party.get("members", [])
    ids_in_order = [m.get("playerId") for m in members if m.get("playerId")]
    # если join_order содержит кого-то, кого уже нет в members — можно очистить
    join_order[:] = [pid for pid in join_order if pid in ids_in_order]

    # индексы чата по текущему join_order (или по members, если join_order пуст)
    order = join_order if join_order else ids_in_order
    gs["_playerChatIndices"] = {pid: idx for idx, pid in enumerate(order)}

def _build_party_state_change_event(
    party: dict,
    joining_user_id: str,
    player_name: str,
    player_role_int: int | None,
) -> dict:
    now_sec = int(time.time())
    now_ms = int(time.time() * 1000)

    gs_src = party.get("gameSpecificState", {}) or {}
    # _customGamePresetData маппим на поля из примера (если есть исходные)
    cpd_src = gs_src.get("_customGamePresetData", {}) or {}
    map_avails = cpd_src.get("_mapAvailabilities") or cpd_src.get("mapAvails") or []
    # Базовые флаги (берём из источника, иначе дефолты True)
    perk_avail = cpd_src.get("_arePerkAvailable")
    if perk_avail is None:
        perk_avail = cpd_src.get("perkAvail", True)
    offering_avail = cpd_src.get("_areOfferingAvailable")
    if offering_avail is None:
        offering_avail = cpd_src.get("offeringAvail", True)
    item_avail = cpd_src.get("_areItemAvailable")
    if item_avail is None:
        item_avail = cpd_src.get("itemAvail", True)
    item_addon_avail = cpd_src.get("_areItemAddonAvailable")
    if item_addon_avail is None:
        item_addon_avail = cpd_src.get("itemAddonAvail", True)
    dlc_allowed = cpd_src.get("_areDlcContentAllowed")
    if dlc_allowed is None:
        dlc_allowed = cpd_src.get("dlcContentAllowed", True)
    private_match = cpd_src.get("_isPrivateMatch")
    if private_match is None:
        private_match = cpd_src.get("privateMatch", True)

    # session / matchmaking
    pss_src = gs_src.get("_partySessionSettings", {}) or {}
    mms_src = gs_src.get("_partyMatchmakingSettings", {}) or {}

    # Список игроков
    members = party.get("members", [])
    player_ids = [m.get("playerId") for m in members if m.get("playerId")]

    # playerRole строкой
    player_role_name = _role_int_to_name(player_role_int)

    # chat history – одно системное событие о присоединении
    chat_history = {
        "_chatMessageHistory": [
            {
                "type": "SystemPlayerJoinedParty",
                "playerMirrorsId": joining_user_id,
                "message": ""
            }
        ],
        "_chatPlayerRoles": [
            {
                "playerMirrorsId": joining_user_id,
                "playerName": player_name,
                "anonymousPlayerName": player_name,
                "playerRole": player_role_int or 0
            }
        ]
    }

    event_payload = {
        "topic": "userNotification",
        "data": {
            "partyId": party["partyId"],
            "state": {
                "gameSpecificState": {
                    "_customGamePresetData": {
                        "mapAvails": map_avails,
                        "perkAvail": bool(perk_avail),
                        "offeringAvail": bool(offering_avail),
                        "itemAvail": bool(item_avail),
                        "itemAddonAvail": bool(item_addon_avail),
                        "dlcContentAllowed": bool(dlc_allowed),
                        "idleCrowsAllowed": True,
                        "privateMatch": bool(private_match),
                        "bots": {"_bots": []},
                    },
                    "_partySessionSettings": {
                        "_sessionId": pss_src.get("_sessionId", ""),
                        "_gameSessionInfos": pss_src.get("_gameSessionInfos", {}),
                        "_owningUserId": pss_src.get("_owningUserId", ""),
                        "_owningUserName": pss_src.get("_owningUserName", ""),
                        "_isDedicated": bool(pss_src.get("_isDedicated", False)),
                        "_matchmakingTimestamp": _safe_int(pss_src.get("_matchmakingTimestamp", -1), -1),
                    },
                    "_partyMatchmakingSettings": {
                        "_playerIds": player_ids,
                        "_matchmakingState": mms_src.get("_matchmakingState", "None"),
                        "_startMatchmakingDateTimestamp": _safe_int(mms_src.get("_startMatchmakingDateTimestamp", -1), -1),
                        "_matchIncentive": _safe_int(mms_src.get("_matchIncentive", 0), 0),
                        "_modeBonus": _safe_int(mms_src.get("_modeBonus", 0), 0),
                        "_currentETASeconds": _safe_int(mms_src.get("_currentETASeconds", -1), -1),
                        "_isInFinalCountdown": bool(mms_src.get("_isInFinalCountdown", False)),
                        "_postMatchmakingTransitionId": _safe_int(mms_src.get("_postMatchmakingTransitionId", 0), 0),
                        "_playWhileYouWaitLobbyState": mms_src.get("_playWhileYouWaitLobbyState", "Inactive"),
                        "_autoReadyEnabled": mms_src.get("_autoReadyEnabled", "None"),
                        "_isPriorityQueue": bool(mms_src.get("_isPriorityQueue", False)),
                        "_isPlayWhileYouWaitQueuePossible": bool(mms_src.get("_isPlayWhileYouWaitQueuePossible", False)),
                    },
                    # эти два поля мы заранее поддерживаем в party.gameSpecificState
                    "_playerJoinOrder": gs_src.get("_playerJoinOrder", player_ids),
                    "_playerChatIndices": gs_src.get("_playerChatIndices", {pid: i for i, pid in enumerate(player_ids)}),

                    "_gameType": _safe_int(gs_src.get("_gameType", 1), 1),
                    "_playerRole": player_role_name,
                    "_isCrowdPlay": bool(gs_src.get("_isCrowdPlay", False)),
                    "_isUsingDedicatedServer": bool(pss_src.get("_isDedicated", False)),
                    "_chatHistory": chat_history,
                    "_version": gs_src.get("_version", "live"),
                    "_lastUpdatedTime": _safe_int(gs_src.get("_lastUpdatedTime", now_sec), now_sec),
                    "_lastSentTime": _safe_int(gs_src.get("_lastSentTime", now_sec), now_sec),
                },
                "playerLimit": party.get("playerLimit", 6),
                "privacyState": party.get("privacyState", "public"),
            },
            "timestamp": now_ms
        },
        "event": "partyStateChange"
    }
    return event_payload

@router.post("/party/{party_id}/join")
async def join_party(
    party_id: str,
    request: Request,
    autoJoin: bool = Query(False, alias="autoJoin"),
    key: Optional[int] = Query(None, alias="key"),
    db_sessions: AsyncSession = Depends(get_sessions_session),
    db_users: AsyncSession = Depends(get_user_session),
):
    user_id = await _get_current_user_id(request, db_sessions)

    party = _find_party_by_id(party_id)
    if not party:
        raise HTTPException(status_code=404, detail="Party not found")

    # истёк ли срок
    expiry_ts = party.get("expiryTime")
    if isinstance(expiry_ts, int) and expiry_ts < int(time.time()):
        raise HTTPException(status_code=404, detail="Party expired")

    # добавление участника (без дублей)
    members = party.get("members", [])
    already_member = any(m.get("playerId") == user_id for m in members)
    if not already_member:
        limit = int(party.get("playerLimit", 0) or 0)
        if limit and len(members) >= limit:
            raise HTTPException(status_code=403, detail="Party is full")
        members.append({"playerId": user_id})
        party["members"] = members
        _recount_player_count(party)

    # обновим join order / chat indices в party.gameSpecificState
    _append_join_order_and_indices(party, user_id)

    # сохранить партию
    PARTIES[party["partyId"]] = party

    # хост ли текущий юзер
    is_host = (party.get("hostPlayerId") == user_id)

    # профиль игрока (имя/steam_id)
    player_profile = await UserManager.get_user_profile(db_users, user_id)
    player_name = getattr(player_profile, "user_name", str(user_id))
    steam_id = str(getattr(player_profile, "steam_id", "") or "")

    # 1) уведомление хосту: partyJoin
    player_join = {
        "topic": "userNotification",
        "data": {
            "playerId": user_id,
            "playerName": player_name,
            "partyId": party["partyId"],
            "timestamp": int(time.time())
        },
        "event": "partyJoin"
    }

    # 2) состояние участника (host <- partyMemberStateChange)
    stored_body = PLAYER_STATES.get(user_id)
    platform_session = stored_body.get("_platformSessionId") if isinstance(stored_body, dict) else None
    if not platform_session:
        platform_session = _make_platform_session_id(steam_id)

    state_body = (stored_body.copy() if isinstance(stored_body, dict) else {})
    # минимальные обязательные поля, если их нет
    state_defaults = {
        "_playerCustomization": {
            "_equippedCustomization": {
                "head": "AV_Head01_P01",
                "torsoOrBody": "AV_Torso008",
                "legsOrWeapon": "AV_Legs008_01"
            },
            "_equippedCharms": []
        },
        "_playerName": player_name,
        "_uniquePlayerId": steam_id,
        "_playerRank": 1,
        "_characterLevel": 1,
        "_prestigeLevel": 0,
        "_gameRole": 1,  # 1 – выживший, 2 – убийца
        "_characterId": 6,
        "_powerId": "_EMPTY_",
        "_location": 1,
        "_queueDelayIteration": 0,
        "_ready": False,
        "_crossplayAllowed": True,
        "_playerPlatform": "steam",
        "_playerProvider": "steam",
        "_matchId": "",
        "_postMatchmakingRole": "None",   # перезапишем ниже
        "_postMatchmakingState": "None",  # перезапишем ниже
        "_roleRequested": 0,
        "_anonymousSuffix": 0,
        "_isStateInitialized": True,
        "_characterClass": "_LOCKED_",
        "_disconnectionPenaltyEndOfBan": 0
    }
    for k, v in state_defaults.items():
        state_body.setdefault(k, v)

    # перезапишем роль/состояние явно
    state_body["_postMatchmakingRole"] = "Host" if is_host else "Client"
    state_body["_postMatchmakingState"] = "Completed"

    state_body["_platformSessionId"] = platform_session
    PLAYER_STATES[user_id] = state_body  # кэш

    player_join_state = {
        "topic": "userNotification",
        "data": {
            "partyId": party["partyId"],
            "playerId": user_id,
            "state": {"body": state_body},
            "timestamp": int(time.time() * 1000)
        },
        "event": "partyMemberStateChange"
    }

    # 3) сообщение тому, кто заходит: partyStateChange (заполненный максимумом)
    player_role_int = state_body.get("_gameRole", 1)
    party_state_change = _build_party_state_change_event(
        party=party,
        joining_user_id=user_id,
        player_name=player_name,
        player_role_int=_safe_int(player_role_int, 1),
    )

    # отправляем:
    await ws_manager.send_to_user(party.get("hostPlayerId"), player_join)
    await ws_manager.send_to_user(party.get("hostPlayerId"), player_join_state)
    await ws_manager.send_to_user(user_id, party_state_change)

    # ----------- HTTP-ОТВЕТ -----------
    gsm = dict(party.get("gameSpecificState") or {})
    gsm.setdefault("_customGamePresetData", {
        "mapAvails": [],
        "perkAvail": True,
        "offeringAvail": True,
        "itemAvail": True,
        "itemAddonAvail": True,
        "dlcContentAllowed": True,
        "idleCrowsAllowed": True,
        "privateMatch": True,
        "bots": {"_bots": []},
    })
    gsm.setdefault("_partySessionSettings", {
        "_sessionId": "",
        "_gameSessionInfos": {},
        "_owningUserId": "",
        "_owningUserName": "",
        "_isDedicated": False,
        "_matchmakingTimestamp": -1,
    })
    all_player_ids = [m.get("playerId") for m in party.get("members", []) if m.get("playerId")]
    gsm.setdefault("_partyMatchmakingSettings", {
        "_playerIds": all_player_ids,
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
        "_isPlayWhileYouWaitQueuePossible": False,
    })
    gsm.setdefault("_playerJoinOrder", party.get("gameSpecificState", {}).get("_playerJoinOrder", []))
    gsm.setdefault("_playerChatIndices", party.get("gameSpecificState", {}).get("_playerChatIndices", {}))

    role_map = {1: "VE_Camper", 2: "VE_Slasher"}
    top_level_player_role = role_map.get(int(player_role_int) if str(player_role_int).isdigit() else 1, "VE_Camper")

    gsm.setdefault("_gameType", 0)
    gsm.setdefault("_playerRole", top_level_player_role)
    gsm.setdefault("_isCrowdPlay", False)
    gsm.setdefault("_isUsingDedicatedServer", False)
    gsm.setdefault("_chatHistory", {
        "_chatMessageHistory": [
            {"type": "SystemPlayerJoinedParty", "playerMirrorsId": str(user_id), "message": ""}
        ],
        "_chatPlayerRoles": []
    })
    gsm.setdefault("_version", "live")
    now_ts = int(time.time())
    gsm["_lastUpdatedTime"] = now_ts
    gsm["_lastSentTime"] = now_ts

    members_with_state = []
    for m in party.get("members", []):
        pid = m.get("playerId")
        entry = {"playerId": pid}
        st = PLAYER_STATES.get(pid)
        if isinstance(st, dict):
            entry["state"] = {"body": st}
        members_with_state.append(entry)

    response_payload = {
        "partyId":      party["partyId"],
        "playerLimit":  party.get("playerLimit"),
        "privacyState": party.get("privacyState", "public"),
        "gameSpecificState": gsm,
        "autoJoinKey":  party.get("autoJoinKey"),
        "hostPlayerId": party.get("hostPlayerId"),
        "expiryTime":   party.get("expiryTime"),
        "members":      members_with_state,
        "playerCount":  party.get("playerCount", len(members_with_state)),
    }

    return response_payload

DEFAULT_MAP_AVAILS = [255, 255, 239, 255, 255, 255, 255, 3, 0, 0, 0]

def _norm_map_avails(src) -> list[int]:
    """Вернёт массив из 11 значений как в целевой схеме."""
    if isinstance(src, list) and len(src) == 11 and all(isinstance(x, int) for x in src):
        return src
    # попытка извлечь из сырого payload (некоторые клиенты присылают строки чисел)
    try:
        if isinstance(src, list):
            src_int = [int(x) for x in src]
            if len(src_int) == 11:
                return src_int
    except Exception:
        pass
    return DEFAULT_MAP_AVAILS

# @router.post("/match/create", operation_id="match_create_v1", name="match_create_v1")
# async def create_match(
#     data: dict,
#     request: Request,
#     db_sessions: AsyncSession = Depends(get_sessions_session),
# ):
#     host_id = await _get_current_user_id(request, db_sessions)
#     match_id = host_id
#     now_ms = int(time.time() * 1000)

#     # 1) собираем sideB: приоритет sideB -> playersB -> пати хоста
#     sideB = list(data.get("sideB") or [])
#     if not sideB:
#         playersB = list(data.get("playersB") or [])
#         if playersB:
#             sideB = playersB
#     if not sideB:
#         _, party = _find_player_party(host_id)
#         if party:
#             sideB = [
#                 m.get("playerId")
#                 for m in party.get("members", [])
#                 if m.get("playerId") and m.get("playerId") != host_id
#             ]

#     # 2) считаем количества и категорию
#     countA = 1
#     countB = len(sideB)
#     category_out = f"live-277399-:::all::{countA}:{countB}:G:2:P"

#     # 3) формируем HTTP-ответ (как у тебя, но с динамикой и host_id)
#     response = {
#         "matchId": match_id,                     # <-- host_id
#         "schema": 3,
#         "category": category_out,
#         "geolocation": {},
#         "creationDateTime": now_ms,
#         "status": "OPENED",
#         "creator": host_id,                      # <-- host_id
#         "customData": {},
#         "version": 1,
#         "effectiveCounts": {"A": countA, "B": countB},
#         "churn": 0,
#         "props": {
#             "EncryptionKey": "GdvU19quZQRRu8yKHA8NxZ/umxDMkhwgGC695JpoZv8=",
#             "MatchConfiguration": "{\r\n\t\"_mapAvailabilities\": [ 255, 255, 255, 255, 255 ],\r\n\t\"_arePerkAvailable\": true,\r\n\t\"_areOfferingAvailable\": true,\r\n\t\"_areItemAvailable\": true,\r\n\t\"_areItemAddonAvailable\": true,\r\n\t\"_areDlcContentAllowed\": true,\r\n\t\"_isPrivateMatch\": true\r\n}",
#             "GameType": "1",
#             "isPrivate": True,
#             "countA": countA,
#             "countB": countB,                    # <-- динамика
#             "platform": "UniversalXPlay",
#             "isDedicated": False                 # как у тебя в create
#         },
#         "reason": "",
#         "region": "all",
#         "sideA": [host_id],                      # <-- host_id
#         "sideB": sideB,                          # <-- динамика
#         "isRequesterCreator": False
#     }

#     # 4) сохраняем матч
#     MATCHES[match_id] = response

#     # 5) WS: уведомляем соответствующие пати (хоста + всех из sideB)
#     targets = set(sideB)
#     targets.add(host_id)

#     touched_party_ids = set()
#     for pid in targets:
#         p_id, p_obj = _find_player_party(pid)
#         if p_obj:
#             touched_party_ids.add(p_id)

#     for p_id in touched_party_ids:
#         party = PARTIES[p_id]
#         party_host = party.get("hostPlayerId")

#         for m in party.get("members", []):
#             pid = m.get("playerId")
#             if not pid:
#                 continue
#             role = "Host" if pid == party_host else "Client"
#             new_body = _update_state_for_match(
#                 player_id=pid,
#                 match_id=match_id,               # matchId = host_id
#                 role=role,
#                 state="InProgress",
#                 make_ready=True
#             )
#             await _broadcast_member_state_change(party, pid, new_body)

#     return response

# @router.get("/match/{match_id}", operation_id="match_get_v1", name="match_get_v1")
# async def get_match(match_id: str):
#     match = MATCHES.get(match_id)
#     if not match:
#         raise HTTPException(status_code=404, detail="Match not found")
#     return match

# @router.post("/match/{match_id}/register", operation_id="match_register_v1", name="match_register_v1")
# async def register_match(
#     match_id: str,
#     data: dict,
#     request: Request,
#     db_sessions: AsyncSession = Depends(get_sessions_session),
# ):
#     """
#     Хост регистрирует матч.
#     Вход: {"customData":{"SessionSettings":"<BASE64>"} , (опционально) "sideB": ["playerId1", ...]}
#     sideB:
#       - если передан в запросе — используем как есть;
#       - иначе берём из пати хоста (все члены, кроме хоста).
#     sideA фиксирован: [match_id]
#     """

#     # 1) SessionSettings (как в твоём примере)
#     DEFAULT_SESSION_SETTINGS = (
#         "AAAAJGZkYzJiYTk4LTQ0NjEtNDJjMC04ODdkLTIxNmUzNzM0YjkwMgAAAAAAAAAAAAAAAAAAAAYAAAAAAQAAAAEBAQABAAAEO5cAAAARAAAAB01BUE5BTUUGAAAAC09ubGluZUxvYmJ5AgAAABBDVVNUT01TRUFSQ0hJTlQyAescCN8CAAAACEdBTUVNT0RFBgAAAAROb25lAgAAABBDVVNUT01TRUFSQ0hJTlQ1AQAAAAECAAAADE1BVENIVElNRU9VVAdC8AAAAgAAABNTRVNTSU9OVEVNUExBVEVOQU1FBgAAAAtHYW1lU2Vzc2lvbgIAAAAOU0VBUkNIS0VZV09SRFMGAAAABkN1c3RvbQIAAAAQQ1VTVE9NU0VBUkNISU5UMwEAAAABAgAAABBTZXNzaW9uU3RhcnRUaW1lBgAAABgyMDI1LTA4LTIwVDIwOjQ0OjM0LjUzMloCAAAAEENVU1RPTVNFQVJDSElOVDEBAAAAEQMAAAAQTWlycm9yc1Nlc3Npb25JZAYAAAAkZmRjMmJhOTgtNDQ2MS00MmMwLTg4N2QtMjE2ZTM3MzRiOTAyAgAAAA1FbmNyeXB0aW9uS2V5BgAAACxHZHZVMTlxdVpRUlJ1OHlLSEE4TnhaL3VteERNa2h3Z0dDNjk1SnBvWnY4PQIAAAASTWF0Y2hDb25maWd1cmF0aW9uBgAAAPF7DQoJIl9tYXBBdmFpbGFiaWxpdGllcyI6IFsgMjU1LCAyNTUsIDI1NSwgMjU1LCAyNTUgXSwNCgkiX2FyZVBlcmtBdmFpbGFibGUiOiB0cnVlLA0KCSJfYXJlT2ZmZXJpbmdBdmFpbGFibGUiOiB0cnVlLA0KCSJfYXJlSXRlbUF2YWlsYWJsZSI6IHRydWUsDQoJIl9hcmVJdGVtQWRkb25BdmFpbGFibGUiOiB0cnVlLA0KCSJfYXJlRGxjQ29udGVudEFsbG93ZWQiOiB0cnVlLA0KCSJfaXNQcml2YXRlTWF0Y2giOiB0cnVlDQp9AgAAAAZDb3VudEEBAAAAAQIAAAAGQ291bnRCAQAAAAACAAAACHBsYXRmb3JtBgAAAA5Vbml2ZXJzYWxYUGxheQIAAAARUGxhdGZvcm1TZXNzaW9uSWQGAAAALDF8fDc2NTYxMTk5ODI2MDA5NDA5Ojc3Nzd8MTA5Nzc1MjQxMzk4MDEyNjQ5Ag=="
#     )
#     req_custom = data.get("customData") or {}
#     session_settings = req_custom.get("SessionSettings") or DEFAULT_SESSION_SETTINGS

#     # 2) Определяем host и sideB
#     sideB = list(data.get("sideB") or [])

#     try:
#         host_id = await _get_current_user_id(request, db_sessions)
#     except HTTPException:
#         host_id = None

#     if not sideB and host_id:
#         # найдём пати хоста и соберём sideB из участников пати (кроме хоста)
#         _, party = _find_player_party(host_id)
#         if party:
#             sideB = [
#                 m.get("playerId")
#                 for m in party.get("members", [])
#                 if m.get("playerId") and m.get("playerId") != host_id
#             ]

#     # 3) Считаем количества и формируем динамические поля
#     countA = 1  # как ты писал — A фиксирован (хост/идентификатор матча)
#     countB = len(sideB)
#     category_out = f"live-277399-:::all::{countA}:{countB}:G:2:P"
#     now_ms = int(time.time() * 1000)

#     # 4) Собираем ответ по нужной схеме
#     response = {
#         "matchId": match_id,
#         "schema": 3,
#         "category": category_out,
#         "geolocation": {},
#         "creationDateTime": now_ms,
#         "status": "CREATED",
#         "creator": "",
#         "customData": {"SessionSettings": session_settings},
#         "version": 1,
#         "effectiveCounts": {"A": countA, "B": countB},
#         "churn": 0,
#         "props": {
#             "EncryptionKey": "ljyd1L2rRx9SWqJPM0WB2WtEAg5WPzdyCiihNx/6r98=",
#             "MatchConfig": "{\"mapAvails\":[255,255,239,255,255,255,255,3,0,0,0],\"perkAvail\":true,\"offeringAvail\":true,\"itemAvail\":true,\"itemAddonAvail\":true,\"dlcContentAllowed\":true,\"idleCrowsAllowed\":true,\"privateMatch\":true,\"bots\":{\"_bots\":[]}}",
#             "CrossplayOptOut": "false",
#             "GameType": "None:1",
#             "isPrivate": True,
#             "countA": countA,
#             "countB": countB,
#             "platform": "UniversalXPlay",
#             "isDedicated": True,
#         },
#         "reason": "",
#         "region": "all",
#         "sideA": [match_id],   # A остаётся фиксированным
#         "sideB": sideB,        # B динамический
#         "isRequesterInMatch": True,
#         "isRequesterCreator": False,
#     }

#     # 5) Сохраняем
#     MATCHES[match_id] = response
#     return response

# PLATFORM_ID = None
# PARTY_OWNER_STATE = None
# INCLUDE_STATE = None

# @router.get("/party")
# async def get_party(includeState: bool = Query(False)):
#     if includeState == True:
#         return {}

# @router.post("/party")
# async def create_party(
#     data: dict,
#     request: Request,
#     db_match: AsyncSession = Depends(get_matchmaking_session),
#     db_sessions: AsyncSession = Depends(get_sessions_session)
# ):
#     bhvr_session = request.cookies.get("bhvrSession")
#     if not bhvr_session:
#         raise HTTPException(status_code=401, detail="No session cookie")
#     user_id = await SessionManager.get_user_id_by_session(db_sessions, bhvr_session)
#     if not user_id:
#         raise HTTPException(status_code=401, detail="Session not found")

#     # now_ts = int(time.time())
#     # expiry_time = now_ts + 60 * 60 * 2
#     # auto_join_key = random.randint(1, 2**31 - 1)
#     # player_limit = data.get("playerLimit", 4)
#     # privacy_state = data.get("privacyState", "public")
#     # game_specific_state = data.get("gameSpecificState", {})

#     # preset = game_specific_state.get("_customGamePresetData", {})
#     # out_preset = {
#     #     "mapAvails": preset.get("_mapAvailabilities", []),
#     #     "perkAvail": preset.get("_arePerkAvailable", True),
#     #     "offeringAvail": preset.get("_areOfferingAvailable", True),
#     #     "itemAvail": preset.get("_areItemAvailable", True),
#     #     "itemAddonAvail": preset.get("_areItemAddonAvailable", True),
#     #     "dlcContentAllowed": preset.get("_areDlcContentAllowed", True),
#     #     "privateMatch": preset.get("_isPrivateMatch", True),
#     #     "bots": {"_bots": []}
#     # }

#     # # Копируем остальные части gameSpecificState (просто скопировать и обновить только нужные ключи)
#     # out_gss = dict(game_specific_state)
#     # out_gss["_customGamePresetData"] = out_preset
#     # out_gss.setdefault("_partySessionSettings", {})
#     # out_gss.setdefault("_partyMatchmakingSettings", {})
#     # out_gss["_partyMatchmakingSettings"].setdefault("_startMatchmakingDateTimestamp", -1)
#     # out_gss["_partyMatchmakingSettings"].setdefault("_matchIncentive", 0)
#     # out_gss["_partyMatchmakingSettings"].setdefault("_isInFinalCountdown", False)
#     # out_gss["_partyMatchmakingSettings"].setdefault("_postMatchmakingTransitionId", 0)
#     # out_gss.setdefault("_playerJoinOrder", [])
#     # out_gss.setdefault("_playerChatIndices", {})
#     # out_gss.setdefault("_gameType", 0)
#     # out_gss.setdefault("_isCrowdPlay", False)
#     # out_gss.setdefault("_isUsingDedicatedServer", True)
#     # out_gss.setdefault("_chatHistory", {"_chatMessageHistory": [], "_playerNames": []})
#     # out_gss.setdefault("_version", "icecream-hf1-2373437-live")
#     # out_gss.setdefault("_lastUpdatedTime", 0)
#     # out_gss.setdefault("_lastSentTime", 0)

#     # # Собираем members (только хост)
#     # members = [{"playerId": user_id}]

#     # # Сохраняем в базу
#     # party = await PartyManager.create_party(
#     #     db=db_match,
#     #     party_id=user_id,
#     #     host_player_id=user_id,
#     #     privacy_state=privacy_state,
#     #     player_limit=player_limit,
#     #     auto_join_key=auto_join_key,
#     #     expiry_time=expiry_time,
#     #     player_count=1,
#     #     game_specific_state=out_gss,
#     #     members=members
#     # )

#     # json_response = {
#     #     "partyId": party.party_id,
#     #     "hostPlayerId": party.host_player_id,
#     #     "gameSpecificState": party.game_specific_state,
#     #     "playerLimit": party.player_limit,
#     #     "privacyState": party.privacy_state,
#     #     "expiryTime": party.expiry_time,
#     #     "autoJoinKey": party.auto_join_key,
#     #     "playerCount": party.player_count,
#     #     "members": party.members
#     # }

#     json_response = {
#         "partyId": "0912a919-a897-4e37-8057-b0d7cf2adb66",
#         "hostPlayerId": "f58654d6-15f4-4d25-b52a-9238ae696ebd",
#         "privacyState": "public",
#         "gameSpecificState": {
#             "_customGamePresetData": {
#             "_mapAvailabilities": [],
#             "_arePerkAvailable": True,
#             "_areOfferingAvailable": True,
#             "_areItemAvailable": True,
#             "_areItemAddonAvailable": True,
#             "_areDlcContentAllowed": True,
#             "_isPrivateMatch": True
#             },
#             "_partySessionSettings": {
#             "_sessionId": "",
#             "_gameSessionInfos": {},
#             "_owningUserId": "",
#             "_owningUserName": "",
#             "_isDedicated": False,
#             "_matchmakingTimestamp": -1
#             },
#             "_partyMatchmakingSettings": {
#             "_playerIds": [],
#             "_matchmakingState": "None"
#             },
#             "_playerChatIndices": {},
#             "_gameType": 1,
#             "_version": "live-277399-",
#             "_lastUpdatedTime": -1667662445,
#             "_lastSentTime": 32759
#         },
#         "playerLimit": 6,
#         "expiryTime": 1754076448,
#         "autoJoinKey": 838695663,
#         "playerCount": 1,
#         "members": [
#             {
#             "playerId": "f58654d6-15f4-4d25-b52a-9238ae696ebd"
#             }
#         ]
#         }

#     return JSONResponse(content=json_response, status_code=201)

# @router.delete("/party/{party_id}")
# async def delete_party(
#     party_id: str,
#     db_match: AsyncSession = Depends(get_matchmaking_session),
# ):
#     result = await PartyManager.delete_party(db=db_match, party_id=party_id)
#     return Response(status_code=204)
    
# @router.delete("/party/leave")
# async def leave_party(request: Request, disband: bool = Query(False), 
#                       db_sessions: AsyncSession = Depends(get_sessions_session), 
#                       db_match: AsyncSession = Depends(get_matchmaking_session)
# ):
#     if disband == True:
#         bhvr_session = request.cookies.get("bhvrSession")
#         if not bhvr_session:
#             raise HTTPException(status_code=401, detail="No session cookie")
#         user_id = await SessionManager.get_user_id_by_session(db_sessions, bhvr_session)
#         if not user_id:
#             raise HTTPException(status_code=401, detail="Session not found")
        
#         party = await PartyManager.get_player_party(db=db_match, player_id=user_id)

#         if not party:
#             raise HTTPException(status_code=404, detail="Party not found")

#         await PartyManager.remove_member(db=db_match, party_id=party.party_id, player_id=user_id)
        
#     return {}
    
# @router.put("/party/{party_id}")
# async def update_party(
#     request: Request, 
#     party_id: str, 
#     db_sessions: AsyncSession = Depends(get_sessions_session), 
#     db_users: AsyncSession = Depends(get_user_session),
#     db_match: AsyncSession = Depends(get_matchmaking_session)
# ):
#     data = await request.json()
#     bhvr_session = request.cookies.get("bhvrSession")
#     if not bhvr_session:
#         raise HTTPException(status_code=401, detail="No session cookie")
    
#     # party = await PartyManager.get_party(db_match, party_id)
#     # if not party:
#     #     raise HTTPException(404, "Party not found")
    
#     # user_profile = await UserManager.get_user_profile(db_users, user_id=party.host_player_id)

#     # data = await request.json()
#     # privacy_state = party.privacy_state
#     # game_specific_state = party.game_specific_state
#     # player_limit = party.player_limit

#     # preset = game_specific_state.get("_customGamePresetData", {})
#     # out_preset = {
#     #     "mapAvails": preset.get("_mapAvailabilities", []),
#     #     "perkAvail": preset.get("_arePerkAvailable", True),
#     #     "offeringAvail": preset.get("_areOfferingAvailable", True),
#     #     "itemAvail": preset.get("_areItemAvailable", True),
#     #     "itemAddonAvail": preset.get("_areItemAddonAvailable", True),
#     #     "dlcContentAllowed": preset.get("_areDlcContentAllowed", True),
#     #     "privateMatch": preset.get("_isPrivateMatch", True),
#     #     "bots": {"_bots": []}
#     # }
#     # out_gss = dict(game_specific_state)
#     # out_gss["_customGamePresetData"] = out_preset
#     # out_gss.setdefault("_partySessionSettings", {})
#     # out_gss.setdefault("_partyMatchmakingSettings", {})
#     # out_gss["_partyMatchmakingSettings"].setdefault("_startMatchmakingDateTimestamp", -1)
#     # out_gss["_partyMatchmakingSettings"].setdefault("_matchIncentive", 0)
#     # out_gss["_partyMatchmakingSettings"].setdefault("_isInFinalCountdown", False)
#     # out_gss["_partyMatchmakingSettings"].setdefault("_postMatchmakingTransitionId", 0)
#     # out_gss.setdefault("_playerJoinOrder", [])
#     # out_gss.setdefault("_playerChatIndices", {})
#     # out_gss.setdefault("_gameType", 0)
#     # out_gss.setdefault("_isCrowdPlay", False)
#     # out_gss.setdefault("_isUsingDedicatedServer", True)
#     # out_gss.setdefault("_chatHistory", {"_chatMessageHistory": [], "_playerNames": []})
#     # out_gss.setdefault("_version", "icecream-hf1-2373437-live")
#     # out_gss.setdefault("_lastUpdatedTime", 0)
#     # out_gss.setdefault("_lastSentTime", 0)

#     # updated_party = await PartyManager.update_party(
#     #     db=db_match,
#     #     party_id=party_id,
#     #     privacy_state=privacy_state,
#     #     player_limit=player_limit,
#     #     game_specific_state=out_gss,
#     # )

#     # await PartyManager.add_player_to_join_order(
#     #     db=db_match,
#     #     party_id=party_id,
#     #     player_id=party.host_player_id,
#     # )

#     # await PartyManager.set_platform_session_id(
#     #     db=db_match,
#     #     party_id=party_id,
#     #     player_id=party.host_player_id,
#     #     platform_session_id=f"1||{user_profile.steam_id}:7777|109775241482773159",
#     # )

#     # return {
#     #     "partyId": updated_party.party_id,
#     #     "hostPlayerId": updated_party.host_player_id,
#     #     "gameSpecificState": updated_party.game_specific_state,
#     #     "playerLimit": updated_party.player_limit,
#     #     "privacyState": updated_party.privacy_state,
#     #     "expiryTime": updated_party.expiry_time,
#     #     "autoJoinKey": updated_party.auto_join_key,
#     #     "playerCount": updated_party.player_count,
#     #     "members": updated_party.members
#     # }

#     global PLATFORM_ID
#     PLATFORM_ID = data.get("gameSpecificState").get("platformSessionId")

#     json_response = {
#     "partyId": "0912a919-a897-4e37-8057-b0d7cf2adb66",
#     "hostPlayerId": "f58654d6-15f4-4d25-b52a-9238ae696ebd",
#     "gameSpecificState": {
#         "_customGamePresetData": {
#         "_mapAvailabilities": [],
#         "_arePerkAvailable": True,
#         "_areOfferingAvailable": True,
#         "_areItemAvailable": True,
#         "_areItemAddonAvailable": True,
#         "_areDlcContentAllowed": True,
#         "_isPrivateMatch": True
#         },
#         "_partySessionSettings": {
#         "_sessionId": "",
#         "_gameSessionInfos": {},
#         "_owningUserId": "",
#         "_owningUserName": "",
#         "_isDedicated": False,
#         "_matchmakingTimestamp": -1
#         },
#         "_partyMatchmakingSettings": {
#         "_playerIds": [],
#         "_matchmakingState": "None"
#         },
#         "_playerChatIndices": {},
#         "_gameType": 1,
#         "_version": "live-277399-",
#         "_lastUpdatedTime": -1667662445,
#         "_lastSentTime": 32759,
#         "platformSessionId": PLATFORM_ID
#     },
#     "expiryTime": 1754076268,
#     "privacyState": "public",
#     "autoJoinKey": 838695663,
#     "playerLimit": 6,
#     "members": [
#         {
#         "playerId": "f58654d6-15f4-4d25-b52a-9238ae696ebd"
#         }
#     ],
#     "playerCount": 1
#     }

#     return JSONResponse(content=json_response, status_code=200)

# @router.put("/party/player/{party_id}/state")
# async def party_update_user_state(party_id: str,
#                                   request: Request,
#                                   db_match: AsyncSession = Depends(get_matchmaking_session),
#                                   db_sessions = Depends(get_sessions_session),
#                                   db_users = Depends(get_user_session)):
    
#     global PARTY_OWNER_STATE
#     bhvr_session = request.cookies.get("bhvrSession")
#     if not bhvr_session:
#         raise HTTPException(status_code=401, detail="No session cookie")
    
#     user_id = await SessionManager.get_user_id_by_session(db=db_sessions, bhvr_session=bhvr_session)

#     if not user_id:
#         raise HTTPException(status_code=401, detail="Session not found")
    
#     user_profile = await UserManager.get_user_profile(db=db_users, user_id=user_id)

#     data = await request.json()

#     # body = data.get("body")

#     # await PartyManager.update_member_state(db=db_match, party_id=party_id, player_id=user_profile.user_id, state=body)
#     # return Response(status_code=204)

#     steam_id = data.get("body").get("_uniquePlayerId")

#     if steam_id == "76561199106922308":
#         PARTY_OWNER_STATE = data

#     return(Response(status_code=204))

# #я его мать ебал, доделать
# @router.post("/party/{party_id}/invite")
# async def party_player_invite(party_id: str, 
#                               request: Request,
#                               data: PartyInviteRequest,
#                               db_sessions = Depends(get_sessions_session),
#                               db_users = Depends(get_user_session)):
#     expire_at = int(time.time() + 300)

#     bhvr_session = request.cookies.get("bhvrSession")
#     if not bhvr_session:
#         raise HTTPException(status_code=401, detail="No session cookie")
    
#     user_id = await SessionManager.get_user_id_by_session(db=db_sessions, bhvr_session=bhvr_session)

#     if not user_id:
#         raise HTTPException(status_code=401, detail="Session not found")
    
#     user_profile = await UserManager.get_user_profile(db=db_users, user_id=user_id)

#     websoket_data = {
#     "topic": "userNotification",
#     "data": {
#         "inviterId": "0a6ffe7f-04d3-48e0-9222-4cf7370bac86",
#         "inviterPlayerName": "Bezdarnost",
#         "playerId": "4c9e085b-ec60-4734-a937-1a510f01c958",
#         "playerName": "Yappa <3 trubochki",
#         "fromRequestToJoin": False,
#         "timestamp": int(time.time())
#     },
#     "event": "partyOtherPlayerInvite"
#     }

#     await ws_manager.send_to_user("0a6ffe7f-04d3-48e0-9222-4cf7370bac86", message=websoket_data)

#     return {"partyId": party_id,"expireAt": expire_at}

#     # invited_it = data.players[0]

#     # response_data = {
#     #     "topic": "userNotification",
#     #     "data": {
#     #         "inviterId": user_profile.user_id,
#     #         "inviterPlayerName": user_profile.user_name,
#     #         "partyId": party_id,
#     #         "fromRequestToJoin": False,
#     #         "expireAt": expire_at,
#     #         "timestamp": time.time()
#     #     },
#     #     "event": "partyInvite"
#     # }

#     # await ws_manager.send_to_user(invited_it, message=response_data)

#     # return {"partyId": party_id,"expireAt": expire_at}

# @router.get("/party/player/{party_id}")
# async def party_get_include_state(party_id: str):
#     return Response(status_code=200)

# @router.get("/party/{party_id}")
# async def get_party(
#     party_id: str,
#     request: Request,
#     includeState: bool = Query(False, alias="includeState"),
#     db: AsyncSession = Depends(get_matchmaking_session),
# ):
#     # party = await PartyManager.get_party(db, party_id)
#     # if not party:
#     #     raise HTTPException(404, "Party not found")

#     # payload = {
#     #     "partyId":      party.party_id,
#     #     "playerLimit":  party.player_limit,
#     #     "privacyState": party.privacy_state,
#     #     "gameSpecificState": party.game_specific_state,
#     #     "autoJoinKey":  party.auto_join_key,
#     #     "hostPlayerId": party.host_player_id,
#     #     "expiryTime":   party.expiry_time,
#     #     "members":      party.members,
#     #     "playerCount":  party.player_count,
#     # }

#     # json_bytes = json.dumps(
#     #     payload,
#     #     ensure_ascii=False,
#     #     separators=(",", ":")
#     # ).encode("utf-8")

#     # return Response(content=json_bytes, media_type="application/json")

#     # head = PARTY_OWNER_STATE.get("body", {}).get("_customizationMesh", [None])[0]
#     # torsoOrBody = PARTY_OWNER_STATE.get("body", {}).get("_customizationMesh", [None])[1]
#     # legsOrWeapon = PARTY_OWNER_STATE.get("body", {}).get("_customizationMesh", [None])[2]
#     # data = PARTY_OWNER_STATE.get("body")
#     global INCLUDE_STATE

#     json_response = {
#     "partyId": "f58654d6-15f4-4d25-b52a-9238ae696ebd",
#     "playerLimit": 6,
#     "privacyState": "friends",
#     "gameSpecificState": {
#         "_customGamePresetData": {
#         "mapAvails": [],
#         "perkAvail": True,
#         "offeringAvail": True,
#         "itemAvail": True,
#         "itemAddonAvail": True,
#         "dlcContentAllowed": True,
#         "idleCrowsAllowed": True,
#         "privateMatch": True,
#         "bots": {
#             "_bots": []
#         }
#         },
#         "_partySessionSettings": {
#         "_sessionId": "",
#         "_gameSessionInfos": {},
#         "_owningUserId": "",
#         "_owningUserName": "",
#         "_isDedicated": False,
#         "_matchmakingTimestamp": -1
#         },
#         "_partyMatchmakingSettings": {
#         "_playerIds": [],
#         "_matchmakingState": "None",
#         "_startMatchmakingDateTimestamp": -1,
#         "_matchIncentive": 0,
#         "_modeBonus": 0,
#         "_currentETASeconds": -1,
#         "_isInFinalCountdown": False,
#         "_postMatchmakingTransitionId": 0,
#         "_playWhileYouWaitLobbyState": "Inactive",
#         "_autoReadyEnabled": "None",
#         "_isPriorityQueue": False,
#         "_isPlayWhileYouWaitQueuePossible": False
#         },
#         "_playerJoinOrder": [
#         "f58654d6-15f4-4d25-b52a-9238ae696ebd",
#         "4c9e085b-ec60-4734-a937-1a510f01c958"
#         ],
#         "_playerChatIndices": {
#         "f58654d6-15f4-4d25-b52a-9238ae696ebd": 0,
#         "4c9e085b-ec60-4734-a937-1a510f01c958": 1
#         },
#         "_gameType": 0,
#         "_playerRole": "VE_Camper",
#         "_isCrowdPlay": False,
#         "_isUsingDedicatedServer": True,
#         "_chatHistory": {
#         "_chatMessageHistory": [
#             {
#             "type": "SystemPlayerJoinedParty",
#             "playerMirrorsId": "4c9e085b-ec60-4734-a937-1a510f01c958",
#             "message": ""
#             }
#         ],
#         "_chatPlayerRoles": [
#             {
#             "playerMirrorsId": "f58654d6-15f4-4d25-b52a-9238ae696ebd",
#             "playerName": "DBDPUBSERV",
#             "anonymousPlayerName": "Дэвид Кинг",
#             "playerRole": 0
#             }
#         ]
#         },
#         "_version": "live-277399-",
#         "_lastUpdatedTime": 1751997607,
#         "_lastSentTime": 1751997607
#     },
#     "autoJoinKey": 838695663,
#     "hostPlayerId": "f58654d6-15f4-4d25-b52a-9238ae696ebd",
#     "expiryTime": 1752001202,
#     "members": [
#         {
#         "playerId": "f58654d6-15f4-4d25-b52a-9238ae696ebd",
#         "state": {
#             "body": {
#             "_playerCustomization": {
#                 "_equippedCustomization": {
#                 "head": "DK_Head002",
#                 "torsoOrBody": "DK_Torso02_KOEvent01",
#                 "legsOrWeapon": "DK_Legs002_02"
#                 },
#                 "_equippedCharms": []
#             },
#             "_playerName": "DBDPUBSERV",
#             "_platformSessionId": "1||76561199234371478:7777|109775241482773159",
#             "_uniquePlayerId": "76561199234371478",
#             "_playerRank": 20,
#             "_characterLevel": 25,
#             "_prestigeLevel": 1,
#             "_gameRole": 2,
#             "_characterId": 2,
#             "_powerId": "Item_Camper_MedKit03",
#             "_location": 1,
#             "_queueDelayIteration": 0,
#             "_ready": False,
#             "_crossplayAllowed": True,
#             "_playerPlatform": "steam",
#             "_playerProvider": "steam",
#             "_matchId": "",
#             "_postMatchmakingRole": "None",
#             "_postMatchmakingState": "None",
#             "_roleRequested": 0,
#             "_anonymousSuffix": 1,
#             "_isStateInitialized": True,
#             "_characterClass": "_LOCKED_",
#             "_disconnectionPenaltyEndOfBan": 0
#             }
#         }
#         },
#         {
#         "playerId": "4c9e085b-ec60-4734-a937-1a510f01c958"
#         }
#     ],
#     "playerCount": 2
#     }

#     INCLUDE_STATE = json_response

#     return JSONResponse(content=json_response, status_code=200)

# @router.post("/party/{party_id}/join")
# async def join_party(
#     party_id: str,
#     request: Request,
#     autoJoin: bool = Query(False, alias="autoJoin"),
#     key: int | None = Query(None, alias="key"),
#     db: AsyncSession = Depends(get_matchmaking_session),
#     db_users: AsyncSession = Depends(get_user_session),
#     db_sessions: AsyncSession = Depends(get_sessions_session)
# ):
#     # party = await PartyManager.get_party(db, party_id)
#     # if not party:
#     #     raise HTTPException(404, "Party not found")

#     # if autoJoin and key is not None and party.auto_join_key != key:
#     #     raise HTTPException(403, "Invalid autoJoinKey")

#     # if party.expiry_time and party.expiry_time < int(time.time()):
#     #     raise HTTPException(404, "Party expired")

#     # bhvr_session = request.cookies.get("bhvrSession")
#     # if not bhvr_session:
#     #     raise HTTPException(status_code=401, detail="No session cookie")

#     # user_id = await SessionManager.get_user_id_by_session(db_sessions, bhvr_session)
#     # if not user_id:
#     #     raise HTTPException(status_code=401, detail="Session not found")

#     # await PartyManager.add_player_to_join_order(
#     #     db=db,
#     #     party_id=party_id,
#     #     player_id=user_id,
#     # )

#     # user_profile = await UserManager.get_user_profile(db=db_users, user_id=user_id)

#     # await PartyManager.set_platform_session_id(
#     #     db=db,
#     #     party_id=party_id,
#     #     player_id=user_id,
#     #     platform_session_id=f"1||{user_profile.steam_id}:7777|109775241482773159",
#     # )

#     # party_json = {
#     #     "partyId":      party.party_id,
#     #     "playerLimit":  party.player_limit,
#     #     "privacyState": party.privacy_state,
#     #     "gameSpecificState": party.game_specific_state,
#     #     "autoJoinKey":  party.auto_join_key,
#     #     "hostPlayerId": party.host_player_id,
#     #     "expiryTime":   party.expiry_time,
#     #     "members":      party.members,
#     #     "playerId":     user_id,
#     #     "playerCount":  party.player_count + 1,
#     # }

#     # return {"partyDetails": party_json}
#     global INCLUDE_STATE
#     return INCLUDE_STATE

# @router.post("/test/party/{user_id}")
# async def test_party_invite(user_id: str, 
#                               request: Request,
#                               data: PartyInviteRequest,
#                               db_sessions = Depends(get_sessions_session),
#                               db_users = Depends(get_user_session)):
#     expire_at = int(time.time() + 300)
#     response_data = {
#         "topic": "userNotification",
#         "data": {
#             "inviterId": user_id,
#             "inviterPlayerName": "Bezdarnost",
#             "partyId": user_id,
#             "fromRequestToJoin": False,
#             "expireAt": expire_at,
#             "timestamp": time.time()
#         },
#         "event": "partyInvite"
#     }

#     await ws_manager.send_to_user(user_id, message=response_data)

# @router.post("/party/test")
# async def test_party_invite(request: Request,
#                               db_sessions = Depends(get_sessions_session),
#                               db_users = Depends(get_user_session)):
#     expire_at = int(time.time() + 300)
#     response_data = {
#     "topic": "userNotification",
#     "data": {
#         "playerId": "4c9e085b-ec60-4734-a937-1a510f01c958",
#         "playerName": "Yappa <3 trubochki",
#         "partyId": "0912a919-a897-4e37-8057-b0d7cf2adb66",
#         "timestamp": expire_at
#     },
#     "event": "partyJoin"
#     }

#     join_json = {
#     "topic": "userNotification",
#     "data": {
#         "partyId": "0912a919-a897-4e37-8057-b0d7cf2adb66",
#         "playerId": "4c9e085b-ec60-4734-a937-1a510f01c958",
#         "state": {
#         "body": {
#             "_playerCustomization": {
#             "_equippedCustomization": {
#                 "head": "AV_Head01_P01",
#                 "torsoOrBody": "AV_Torso008",
#                 "legsOrWeapon": "AV_Legs008_01"
#             },
#             "_equippedCharms": []
#             },
#             "_playerName": "Yappa <3 trubochki",
#             "_platformSessionId": "1||76561199318369188:7777|109775244114306341",
#             "_uniquePlayerId": "76561198961790135",
#             "_playerRank": 3,
#             "_characterLevel": 50,
#             "_prestigeLevel": 100,
#             "_gameRole": 2,
#             "_characterId": 6,
#             "_powerId": "_EMPTY_",
#             "_location": 1,
#             "_queueDelayIteration": 0,
#             "_ready": False,
#             "_crossplayAllowed": True,
#             "_playerPlatform": "steam",
#             "_playerProvider": "steam",
#             "_matchId": "",
#             "_postMatchmakingRole": "None",
#             "_postMatchmakingState": "None",
#             "_roleRequested": 0,
#             "_anonymousSuffix": 2,
#             "_isStateInitialized": True,
#             "_characterClass": "_LOCKED_",
#             "_disconnectionPenaltyEndOfBan": 0
#         }
#         },
#         "timestamp": 1754305942663
#     },
#     "event": "partyMemberStateChange"
#     }

#     await ws_manager.send_to_user("f58654d6-15f4-4d25-b52a-9238ae696ebd", message=response_data)
#     await ws_manager.send_to_user("f58654d6-15f4-4d25-b52a-9238ae696ebd", message=join_json)