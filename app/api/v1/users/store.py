import logging
import time
from typing import Annotated

from crud.sessions import SessionManager
from crud.users import UserManager
from db.sessions import get_sessions_session
from db.users import get_user_session
from dependency.redis import Redis
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from schemas.config import settings
from sqlalchemy.ext.asyncio import AsyncSession
from utils.utils import Utils

logger = logging.getLogger(__name__)

router = APIRouter(prefix=settings.api_prefix, tags=["Store"])

@router.get("/extensions/store/steamGetPendingTransactions")
async def steam_get_pending_transactions():
    return {
        "transactionOrderIdList": [],
    }

@router.post("/extensions/store/steamGetPendingTransactions")
async def get_pending_transactions(request: Request,
                        db_users: Annotated[AsyncSession, Depends(get_user_session)],
                        db_sessions: Annotated[AsyncSession, Depends(get_sessions_session)],
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

    user_id = user.user_id

    now = int(time.time())
    consent_list = [
        {
            "consentId": "eula",
            "isGiven": True,
            "updatedDate": now,
            "attentionNeeded": False,
            "latestVersion": {"entryDate": 1688342400, "label": "v4"},
        },
        {
            "consentId": "eula_psn_eu",
            "isGiven": True,
            "updatedDate": now,
            "attentionNeeded": False,
            "latestVersion": {"entryDate": 1688342400, "label": "v5"},
        },
        {
            "consentId": "eula_psn_na",
            "isGiven": True,
            "updatedDate": now,
            "attentionNeeded": False,
            "latestVersion": {"entryDate": 1688342400, "label": "v5"},
        },
        {
            "consentId": "marketing",
            "isGiven": True,
            "updatedDate": now,
            "attentionNeeded": False,
            "latestVersion": {"entryDate": 1676246400, "label": "v2"},
        },
        {
            "consentId": "privacy",
            "isGiven": True,
            "updatedDate": now,
            "attentionNeeded": False,
            "latestVersion": {"entryDate": 1688342400, "label": "v3"},
        },
    ]
    return {
        "userId": user_id,
        "consentList": consent_list,
    }

@router.get("/consent")
async def get_user_consent(
    request: Request,
    db_users: Annotated[AsyncSession, Depends(get_user_session)],
    db_sessions: Annotated[AsyncSession, Depends(get_sessions_session)],
    onlyAttentionNeeded: bool = False,
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

    user_id = user.user_id

    consent_list = [
        {
            "consentId": "eula",
            "isGiven": True,
            "updatedDate": 1744010648,
            "attentionNeeded": False,
            "latestVersion": {"entryDate": 1688342400, "label": "v4"},
        },
        {
            "consentId": "eula_psn_eu",
            "isGiven": True,
            "updatedDate": 1744010648,
            "attentionNeeded": False,
            "latestVersion": {"entryDate": 1688342400, "label": "v5"},
        },
        {
            "consentId": "eula_psn_na",
            "isGiven": True,
            "updatedDate": 1744010648,
            "attentionNeeded": False,
            "latestVersion": {"entryDate": 1688342400, "label": "v5"},
        },
        {
            "consentId": "marketing",
            "isGiven": True,
            "updatedDate": 1744010648,
            "attentionNeeded": False,
            "latestVersion": {"entryDate": 1676246400, "label": "v2"},
        },
        {
            "consentId": "privacy",
            "isGiven": True,
            "updatedDate": 1744010648,
            "attentionNeeded": False,
            "latestVersion": {"entryDate": 1688342400, "label": "v3"},
        },
    ]

    return {
        "userId": user_id,
        "consentList": consent_list,
    }

@router.put("/consent")
async def update_user_consent(
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

    await request.json()
    # data = {'list': [{'consentId': ..., 'isGiven': ...}, ...]}

    # Тут можешь сохранить согласия юзера в БД, если надо
    # Например:
    # for consent in data['list']:
    #     save_user_consent(user_id, consent['consentId'], consent['isGiven'])

    return {}

@router.post("/purchases/{character_name}")
async def buy_character(character_name: str,
                        request: Request,
                        db_users: Annotated[AsyncSession, Depends(get_user_session)],
                        db_sessions: Annotated[AsyncSession, Depends(get_sessions_session)],
                        redis = Depends(Redis.get_redis)):
    bhvr_session = request.cookies.get("bhvrSession")
    if not bhvr_session:
        raise HTTPException(status_code=401, detail="No session cookie")
    user_id = await SessionManager.get_user_id_by_session(db_sessions, bhvr_session)
    if not user_id:
        raise HTTPException(status_code=401, detail="Session not found")

    user = await UserManager.get_user(db_users, user_id=user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    wallet = await UserManager.get_wallet(db_users, user_id)

    data = await request.json()
    currency_type = data.get("currencyType")
    price = await Utils.get_item_price(character_name=character_name, currency_id=currency_type, redis=redis)

    if price is None:
        raise HTTPException(404, detail="Price not found")

    currency_balance = Utils.get_balance(wallet, currency_type)
    if currency_balance is None:
        raise HTTPException(400, detail=f"{currency_type} wallet entry missing")

    if currency_balance < price:
        raise HTTPException(400, detail="Not enough currency")

    if currency_balance >= price:
        await UserManager.update_wallet(db_users, user_id, currency_type, -price)
        await UserManager.add_inventory_item(db_users, user_id, character_name, 1)

        new_balance = currency_balance - price

        response = {
            "boughtItemIds": [character_name],
            "remainingBalance": new_balance,
            "currencyId": currency_type,
        }

        return JSONResponse(content=response, status_code=200)
    return None

@router.post("/extensions/store/purchaseOutfit")
async def buy_outfit(request: Request,
                        db_users: Annotated[AsyncSession, Depends(get_user_session)],
                        db_sessions: Annotated[AsyncSession, Depends(get_sessions_session)],
                        redis = Depends(Redis.get_redis)):
    bhvr_session = request.cookies.get("bhvrSession")
    if not bhvr_session:
        raise HTTPException(status_code=401, detail="No session cookie")
    user_id = await SessionManager.get_user_id_by_session(db_sessions, bhvr_session)
    if not user_id:
        raise HTTPException(status_code=401, detail="Session not found")

    raw  = await request.json()
    body = raw.get("data", raw)
    currency_type = body.get("currencyId")
    outfit_id = body.get("outfitId")
    prices = await Utils.get_item_price(outfit_id=outfit_id, currency_id=currency_type, redis=redis)
    if not prices or not isinstance(prices, dict):
        raise HTTPException(404, detail="Outfit not found or price not available")

    total_price = sum(prices.values())

    wallet = await UserManager.get_wallet(db_users, user_id)
    currency_balance = Utils.get_balance(wallet, currency_type)

    if currency_balance is None:
        raise HTTPException(400, detail=f"{currency_type} wallet entry missing")

    if currency_balance < total_price:
        raise HTTPException(400, detail="Not enough currency")

    await UserManager.update_wallet(db_users, user_id, currency_type, -total_price)
    for item_id in prices:
        await UserManager.add_inventory_item(db_users, user_id, item_id, 1)

    new_balance = currency_balance - total_price

    response = {
        "boughtItemIds": list(prices.keys()),
        "remainingBalance": new_balance,
        "currencyId": currency_type,
    }

    return JSONResponse(content=response, status_code=200)

@router.post("/extensions/store/purchaseCustomizationItem")
async def buy_item(request: Request,
                   db_users: Annotated[AsyncSession, Depends(get_user_session)],
                   db_sessions: Annotated[AsyncSession, Depends(get_sessions_session)],
                   redis = Depends(Redis.get_redis)):
    bhvr_session = request.cookies.get("bhvrSession")
    if not bhvr_session:
        raise HTTPException(status_code=401, detail="No session cookie")
    user_id = await SessionManager.get_user_id_by_session(db_sessions, bhvr_session)
    if not user_id:
        raise HTTPException(status_code=401, detail="Session not found")

    raw  = await request.json()
    body = raw.get("data", raw)
    currency_type = body.get("currencyId")
    item_id = body.get("itemId")

    price = await Utils.get_item_price(item_id=item_id, currency_id=currency_type, redis=redis)
    if price is None:
        raise HTTPException(400, detail="Item not found or no valid price")

    wallet = await UserManager.get_wallet(db_users, user_id)
    currency_balance = Utils.get_balance(wallet, currency_type)

    if currency_balance is None:
        raise HTTPException(400, detail=f"{currency_type} wallet entry missing")

    if currency_balance < price:
        raise HTTPException(400, detail="Not enough currency")

    await UserManager.update_wallet(db_users, user_id, currency_type, -price)
    await UserManager.add_inventory_item(db_users, user_id, item_id, 1)

    wallet = await UserManager.get_wallet(db_users, user_id)
    new_balance = Utils.get_balance(wallet, currency_type)
    now_ts = int(time.time())

    response = {
        "triggerResults": { "error": [], "success": [None] },
        "objectId": item_id,
        "quantity": 1,
        "lastUpdateAt": now_ts,
        "costs": [ { "id": currency_type, "amount": price, "type": "currency" } ],
        "receivedRewards": [ { "id": item_id, "type": "inventory", "amount": 1 } ],
        "wallet": [
            {
                "userId": user_id,
                "currency": currency_type,
                "balance": new_balance,
                "providerBalances": {},
                "disabled": False,
            },
        ],
        "outfitId": item_id,
        "outfitDefaultCost": [
            { "currencyId": currency_type, "price": price, "discountPercentage": 0 },
        ],
    }

    return JSONResponse(content=response, status_code=200)
