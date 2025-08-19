from fastapi import APIRouter, Depends, HTTPException, Response, Request
from sqlalchemy.ext.asyncio import AsyncSession
from schemas.config import settings
from db.users import get_user_session
from db.sessions import get_sessions_session
from crud.sessions import SessionManager
from crud.users import UserManager
from utils.utils import Utils
from utils.users import UserWorker
from utils.decorators import log_call
from dependency.redis import Redis
import logging
logger = logging.getLogger(__name__) 

router = APIRouter(prefix=settings.api_prefix, tags=["Users"])

@router.get("/inventories")
async def get_inventory(request: Request,
                        db_users: AsyncSession = Depends(get_user_session),
                        db_sessions: AsyncSession = Depends(get_sessions_session)
):
    bhvr_session = request.cookies.get("bhvrSession")
    if not bhvr_session:
        raise HTTPException(status_code=401, detail="No session cookie")
    
    user_id = await SessionManager.get_user_id_by_session(db_sessions, bhvr_session)
    if not user_id:
        raise HTTPException(status_code=401, detail="Session not found")
    
    inventory = await UserManager.get_inventory(db_users, user_id=user_id) or []
    inventory_list = []
    for item in inventory:
        inventory_list.append({
            "objectId": item.object_id,
            "quantity": item.quantity,
            "lastUpdatedAt": item.last_update_at
        })
    return {
        "code": 200,
        "message": "OK",
        "data": {
            "inventory": inventory_list
        }
    }

@router.get("/players/me/states/FullProfile/binary")
async def get_user_save(
    request: Request,
    db_users: AsyncSession = Depends(get_user_session),
    db_sessions: AsyncSession = Depends(get_sessions_session)
):
    bhvr_session = request.cookies.get("bhvrSession")
    if not bhvr_session:
        raise HTTPException(status_code=401, detail="No session cookie")

    user_id = await SessionManager.get_user_id_by_session(db_sessions, bhvr_session)
    if not user_id:
        raise HTTPException(status_code=401, detail="Session not found")

    user = await UserManager.get_user(db_users, user_id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return Response(
        content=user.save_data,
        media_type="application/octet-stream",
        headers={
            "Kraken-State-Version": "1",
            "Kraken-State-Schema-Version": "0",
        },
    )

@router.get("/wallet/currencies/BonusBloodpoints")
async def get_bonus_bloodpoints(request: Request,
                        db_users: AsyncSession = Depends(get_user_session),
                        db_sessions: AsyncSession = Depends(get_sessions_session)
):
    bhvr_session = request.cookies.get("bhvrSession")
    if not bhvr_session:
        raise HTTPException(status_code=401, detail="No session cookie")
    
    user_id = await SessionManager.get_user_id_by_session(db_sessions, bhvr_session)
    if not user_id:
        raise HTTPException(status_code=401, detail="Session not found")
    
    user = await UserManager.get_user(db_users, user_id=user_id)
    if not user:
        raise HTTPException(404, detail="User not found")

    if user.is_first_login:
        balance = settings.bonus_bloodpoints
        await UserManager.update_user_flag(db=db_users, user_id=user_id, is_first_login=False)
    else:
        balance = 0
    return {
        "userId": user.user_id,
        "balance": balance,
        "currency": "BonusBloodpoints"
    }

@router.post("/extensions/wallet/getLocalizedCurrenciesAfterLogin")
async def get_localized_currencies_after_login(
    request: Request,
    db_users: AsyncSession = Depends(get_user_session),
    db_sessions: AsyncSession = Depends(get_sessions_session)
):
    bhvr_session = request.cookies.get("bhvrSession")
    if not bhvr_session:
        raise HTTPException(status_code=401, detail="No session cookie")
    
    user_id = await SessionManager.get_user_id_by_session(db_sessions, bhvr_session)
    if not user_id:
        raise HTTPException(status_code=401, detail="Session not found")
    
    user = await UserManager.get_user(db_users, user_id=user_id)
    if not user:
        raise HTTPException(404, detail="User not found")
    
    wallet = await UserManager.get_wallet(db=db_users, user_id=user.id) or []
    balances = {w.currency: w.balance for w in wallet}
    
    from configs.config import CURRENCIES

    result = [
        {
            "balance": balances.get(currency, 0),
            "currency": currency
        }
        for currency in CURRENCIES
    ]
    return {"list": result}

@router.get("/wallet/currencies")
async def get_wallet_currencies(
    request: Request,
    db_users: AsyncSession = Depends(get_user_session),
    db_sessions=Depends(get_sessions_session)
):
    from configs.config import CURRENCIES

    bhvr_session = request.cookies.get("bhvrSession")
    if not bhvr_session:
        return Response(status_code=404)
    user_id = await SessionManager.get_user_id_by_session(db_sessions, bhvr_session)
    if not user_id:
        return Response(status_code=404)

    wallets = await UserManager.get_wallet(db_users, user_id) or []
    balances = {w.currency: w.balance for w in wallets}

    user = await UserManager.get_user(db_users, user_id=user_id)
    if not user:
        return Response(status_code=404)

    wallets_dict = []
    for currency in CURRENCIES:
        value = balances.get(currency, 0)
        wallets_dict.append({
            "balance": value,
            "currency": currency
        })
    return {"list": wallets_dict}

@router.post("/wallet/withdraw")
async def wallet_withdraw():
        return {"ok": True}

@router.post("/playername/steam/{steam_name}")
async def get_player_name(
    steam_name: str,
    request: Request,
    db_users: AsyncSession = Depends(get_user_session),
    db_sessions: AsyncSession = Depends(get_sessions_session)
):
    bhvr_session = request.cookies.get("bhvrSession")
    if not bhvr_session:
        raise HTTPException(status_code=401, detail="No session cookie")
    
    user_id = await SessionManager.get_user_id_by_session(db_sessions, bhvr_session)
    if not user_id:
        raise HTTPException(status_code=401, detail="Session not found")
    
    user = await UserManager.get_user(db_users, user_id=user_id)
    if not user:
        raise HTTPException(404, detail="User not found")

    tag = str(user_id).split("-")[0][:4]
    player_name = f"{steam_name}#{tag}"

    await UserManager.update_user_profile(db=db_users, user_id=user_id, steam_id=user.steam_id, user_name=steam_name, user_code=tag)

    return {
        "providerPlayerNames": {"steam": steam_name},
        "userId": user_id,
        "playerName": player_name,
        "unchanged": True
    }

@router.post("/players/me/states/binary")
async def push_save_state(
    request: Request,
    version: str,
    db_users: AsyncSession = Depends(get_user_session),
    db_sessions = Depends(get_sessions_session)
):
    bhvr_session = request.cookies.get("bhvrSession")
    if not bhvr_session:
        raise HTTPException(status_code=401, detail="No session cookie")
    
    user_id = await SessionManager.get_user_id_by_session(db_sessions, bhvr_session)
    if not user_id:
        raise HTTPException(status_code=401, detail="Session not found")
    
    user = await UserManager.get_user(db_users, user_id=user_id)
    if not user:
        raise HTTPException(404, detail="User not found")
    
    body = await request.body()

    await UserManager.update_save_data(db=db_users, user_id=user_id, save_data=body)

    return {
        "version": int(version) + 1,
        "stateName": "FullProfile",
        "schemaVersion": 0,
        "playerId": user_id
    }

@router.post("/extensions/ownedProducts/reportOwnedProducts")
async def report_owned_products(request: Request):
    return {
        "entitlements": [],
        "consumables": [],
        "backfilledClientDlc": False
    }

@router.get("/ranks/pips")
async def get_ranks_pips(
    request: Request,
    db_users: AsyncSession = Depends(get_user_session),
    db_sessions = Depends(get_sessions_session)
):
    bhvr_session = request.cookies.get("bhvrSession")
    if not bhvr_session:
        raise HTTPException(
            status_code=404,
            detail={"code": 404, "message": "Session not found", "data": {}}
        )
    user_id = await SessionManager.get_user_id_by_session(db_sessions, bhvr_session)
    if not user_id:
        raise HTTPException(
            status_code=404,
            detail={"code": 404, "message": "Session not found", "data": {}}
        )
    user_profile = await UserManager.get_user_profile(db_users, user_id=user_id)
    if not user_profile:
        raise HTTPException(
            status_code=404,
            detail={"code": 404, "message": "User not found", "data": {}}
        )
    
    return {
        "nextRankResetDate": settings.next_rank_reset_date,
        "pips": {
            "survivorPips": user_profile.survivor_pips or 0,
            "killerPips": user_profile.killer_pips or 0
        },
        "seasonRefresh": False
    }

@router.put("/ranks/pips")
async def put_ranks_pips(
    request: Request,
    db_users: AsyncSession = Depends(get_user_session),
    db_sessions = Depends(get_sessions_session)
):
    bhvr_session = request.cookies.get("bhvrSession")
    if not bhvr_session:
        raise HTTPException(404, detail={"code": 404, "message": "Session not found", "data": {}})
    user_id = await SessionManager.get_user_id_by_session(db_sessions, bhvr_session)
    if not user_id:
        raise HTTPException(404, detail={"code": 404, "message": "Session not found", "data": {}})
    user_profile = await UserManager.get_user_profile(db_users, user_id=user_id)
    if not user_profile:
        raise HTTPException(404, detail={"code": 404, "message": "User not found", "data": {}})
    
    body = await request.json()
    if body.get("forceReset"):
        user_profile.killer_pips = 0
        user_profile.survivor_pips = 0
    else:
        if "killerPips" in body and isinstance(body["killerPips"], int) and body["killerPips"] >= 0:
            user_profile.killer_pips = body["killerPips"]
        if "survivorPips" in body and isinstance(body["survivorPips"], int) and body["survivorPips"] >= 0:
            user_profile.survivor_pips = body["survivorPips"]
    await db_users.commit()
    await db_users.refresh(user_profile)
    return {"code": 200, "message": "OK"}

@router.get("/players/ban/status")
async def check_ban(request: Request,
    db_users: AsyncSession = Depends(get_user_session),
    db_sessions: AsyncSession = Depends(get_sessions_session),
):
    bhvr_session = request.cookies.get("bhvrSession")
    if not bhvr_session:
        raise HTTPException(status_code=401, detail="No session cookie")
    
    steam_id = await SessionManager.get_steam_id_by_session(db_sessions, bhvr_session)
    if not steam_id:
        raise HTTPException(status_code=401, detail="Session not found")

    user = await UserManager.get_user(db_users, steam_id=steam_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "isBanned": bool(getattr(user, "is_banned", False)),
        "HuliPalish? 0_o": "https://ibb.co/jvr26bXD"
    }

@router.post("/extensions/playerLevels/getPlayerLevel")
async def get_player_level(
    request: Request,
    db_users: AsyncSession = Depends(get_user_session),
    db_sessions = Depends(get_sessions_session)
):
    bhvr_session = request.cookies.get("bhvrSession")
    if not bhvr_session:
        raise HTTPException(status_code=401, detail="No session cookie")
    user_id = await SessionManager.get_user_id_by_session(db_sessions, bhvr_session)
    if not user_id:
        raise HTTPException(status_code=401, detail="Session not found")
    
    user = await UserManager.get_user(db_users, user_id=user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")

    profile_xp = getattr(user, "xp", 0) or 0

    level_object = Utils.xp_to_player_level(profile_xp)
    return level_object

@router.post("/players/ban/decayAndGetDisconnectionPenaltyPoints")
async def post_penalty_points():
    return {"penaltyPoints":0}

@router.post("/players/friends/sync")
async def friends_sync(
    req: Request,
    db_users: AsyncSession = Depends(get_user_session),
    db_sessions: AsyncSession = Depends(get_sessions_session),
    redis = Depends(Redis.get_redis)
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

    await Redis.set_friend_ids(redis, cid, ids, ttl=15)

    cached_friends = await Redis.get_friends_list(redis, cid, ids)
    if cached_friends:
        return {"friends": cached_friends}

    steam_to_cloud = await Redis.get_cloud_ids(redis, ids, db_users)
    steamid_to_name = await Redis.get_steam_names(redis, ids)

    friends = []
    for sid in ids:
        friend_cloud_id = steam_to_cloud.get(str(sid))
        pname = steamid_to_name.get(sid, "Unknown")
        if friend_cloud_id:
            friends.append({
                "userId": cid,
                "friendId": friend_cloud_id,
                "status": "confirmed",
                "platformIds": {"steam": sid},
                "friendPlayerName": {
                    "userId": friend_cloud_id,
                    "providerPlayerNames": {"steam": pname},
                    "playerName": f"{pname}#{friend_cloud_id[:4]}"
                },
                "favorite": False,
                "mute": False,
                "isKrakenOnlyFriend": False
            })

    await Redis.set_friends_list(redis, cid, ids, friends, ttl=15)
    return {"friends": friends}

@router.get("/players/{user_id}/friends")
async def get_friends(
    user_id: str,
    platform: str = "steam",
    db_users: AsyncSession = Depends(get_user_session),
    redis = Depends(Redis.get_redis)
):

    ids = await Redis.get_friend_ids(redis, user_id)

    cached_friends = await Redis.get_friends_list(redis, user_id, ids)
    if cached_friends:
        return cached_friends

    steam_to_cloud = await Redis.get_cloud_ids(redis, ids, db_users)
    steamid_to_name = await Redis.get_steam_names(redis, ids)

    friends = []
    for sid in ids:
        friend_cloud_id = steam_to_cloud.get(str(sid))
        pname = steamid_to_name.get(sid, "Unknown")
        if friend_cloud_id:
            friends.append({
                "userId": user_id,
                "friendId": friend_cloud_id,
                "status": "confirmed",
                "platformIds": {"steam": sid},
                "friendPlayerName": {
                    "userId": friend_cloud_id,
                    "providerPlayerNames": {"steam": pname},
                    "playerName": f"{pname}#{friend_cloud_id[:4]}"
                },
                "favorite": False,
                "mute": False,
                "isKrakenOnlyFriend": False
            })

    await Redis.set_friends_list(redis, user_id, ids, friends, ttl=15)
    return friends

@router.get("/friends/richPresence/{user_id}")
async def get_friends_rich_presence(
    user_id: str,
    db_users: AsyncSession = Depends(get_user_session),
    db_sessions: AsyncSession = Depends(get_sessions_session),
    redis = Depends(Redis.get_redis)
):

    ids = await Redis.get_friend_ids(redis, user_id)
    if not ids:
        return []

    steam_to_cloud = await Redis.get_cloud_ids(redis, ids, db_users)
    steamid_to_name = await Redis.get_steam_names(redis, ids)
    online_user_ids = await SessionManager.get_all_online_user_ids(db_sessions)

    rich_presence = []
    for sid in ids:
        friend_cloud_id = steam_to_cloud.get(str(sid))
        pname = steamid_to_name.get(sid, "Unknown")
        if not friend_cloud_id:
            continue

        is_online = friend_cloud_id in online_user_ids

        profile = await UserManager.get_user_profile(db_users, friend_cloud_id)
        if is_online:
            game_state = profile.user_state if profile and profile.user_state else "InLobby"
            rich_presence.append({
                "playerId": friend_cloud_id,
                "online": True,
                "gameState": game_state,
                "gameVersion": "3.6.0_289644live",
                "gameSpecificData": {
                    "richPresenceStatus": game_state,
                    "richPresencePlatform": "steam"
                },
                "playerNames": {
                    "userId": friend_cloud_id,
                    "providerPlayerNames": {"steam": pname},
                    "playerName": f"{pname}#{friend_cloud_id[:4]}"
                },
            })
        else:
            game_state = profile.user_state if profile and profile.user_state else "InLobby"
            rich_presence.append({
                "playerId": friend_cloud_id,
                "online": False,
                "gameState": game_state,
                "gameVersion": "3.6.0_289644live",
                "playerNames": {
                    "userId": friend_cloud_id,
                    "providerPlayerNames": {"steam": pname},
                    "playerName": f"{pname}#{friend_cloud_id[:4]}"
                }
            })

    return rich_presence
