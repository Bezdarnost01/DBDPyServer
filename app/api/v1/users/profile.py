from fastapi import APIRouter, Depends, HTTPException, Response, Request
from sqlalchemy.ext.asyncio import AsyncSession
from schemas.config import settings
from db.users import get_user_session
from db.sessions import get_sessions_session
from crud.sessions import SessionManager
from crud.users import UserManager
from utils.utils import Utils

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
    
    user = await UserManager.get_user(db_users, user_id=user_id)
    if not user:
        raise HTTPException(404, detail="User not found")

    inventory = await UserManager.get_inventory(db_users, user_id=user.id) or []
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
            "currency": currency,
            "disabled": False,
            "providerBalances": {},
            "userId": str(user.user_id)
        }
        for currency in CURRENCIES
    ]
    return {"list": result}

@router.get("/wallet/currencies")
async def get_wallet_currencies(
    request: Request,
    db_users: AsyncSession = Depends(get_user_session),
    db_sessions = Depends(get_sessions_session)
):
    bhvr_session = request.cookies.get("bhvrSession")
    if not bhvr_session:
        return Response(status_code=404)
    user_id = await SessionManager.get_user_id_by_session(db_sessions, bhvr_session)
    if not user_id:
        return Response(status_code=404)
    wallets = await UserManager.get_wallet(db_users, user_id)
    wallets_dict = [
        {
            "currencyId": w.currency,
            "balance": w.balance
        }
        for w in wallets
    ]
    return {"list": wallets_dict}


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
    return {"status": "Ok"}

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
    user = await UserManager.get_user(db_users, user_id=user_id)
    if not user:
        raise HTTPException(
            status_code=404,
            detail={"code": 404, "message": "User not found", "data": {}}
        )
    
    return {
        "nextRankResetDate": settings.next_rank_reset_date,
        "pips": {
            "survivorPips": user.survivor_pips or 0,
            "killerPips": user.killer_pips or 0
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
    user = await UserManager.get_user(db_users, user_id=user_id)
    if not user:
        raise HTTPException(404, detail={"code": 404, "message": "User not found", "data": {}})
    
    body = await request.json()
    if body.get("forceReset"):
        user.killer_pips = 0
        user.survivor_pips = 0
    else:
        if "killerPips" in body and isinstance(body["killerPips"], int) and body["killerPips"] >= 0:
            user.killer_pips = body["killerPips"]
        if "survivorPips" in body and isinstance(body["survivorPips"], int) and body["survivorPips"] >= 0:
            user.survivor_pips = body["survivorPips"]
    await db_users.commit()
    await db_users.refresh(user)
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

    return {"isBanned": bool(getattr(user, "is_banned", False))}

@router.post("/extensions/playerLevels/getPlayerLevel")
async def get_player_level(
    request: Request,
    db_users: AsyncSession = Depends(get_user_session),
    db_sessions = Depends(get_sessions_session)
):
    bhvr_session = request.cookies.get("bhvrSession")
    if not bhvr_session:
        return {
            "code": 404,
            "message": "Session not found",
            "data": {}
        }
    user_id = await SessionManager.get_user_id_by_session(db_sessions, bhvr_session)
    if not user_id:
        return {
            "code": 404,
            "message": "Session not found",
            "data": {}
        }
    user = await UserManager.get_user(db_users, user_id=user_id)
    if not user:
        return {
            "code": 404,
            "message": "User not found",
            "data": {}
        }

    profile_xp = getattr(user, "xp", 0) or 0
    level_object = Utils.xp_to_player_level(profile_xp)
    return level_object

@router.post("/players/ban/decayAndGetDisconnectionPenaltyPoints")
async def post_penalty_points():
    return {"penaltyPoints":0}