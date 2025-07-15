from fastapi import APIRouter, Depends, HTTPException, Response, Request
from sqlalchemy.ext.asyncio import AsyncSession
from schemas.config import settings
import time
from db.users import get_user_session
from db.sessions import get_sessions_session
from crud.sessions import SessionManager
from crud.users import UserManager

router = APIRouter(prefix=settings.api_prefix, tags=["Store"])

@router.get("/extensions/store/steamGetPendingTransactions")
async def steam_get_pending_transactions():
    return {
        "transactionOrderIdList": []
    }

@router.post("/extensions/store/steamGetPendingTransactions")
async def get_pending_transactions(request: Request,
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
    
    user_id = user.user_id

    now = int(time.time())
    consent_list = [
        {
            "consentId": "eula",
            "isGiven": True,
            "updatedDate": now,
            "attentionNeeded": False,
            "latestVersion": {"entryDate": 1688342400, "label": "v4"}
        },
        {
            "consentId": "eula_psn_eu",
            "isGiven": True,
            "updatedDate": now,
            "attentionNeeded": False,
            "latestVersion": {"entryDate": 1688342400, "label": "v5"}
        },
        {
            "consentId": "eula_psn_na",
            "isGiven": True,
            "updatedDate": now,
            "attentionNeeded": False,
            "latestVersion": {"entryDate": 1688342400, "label": "v5"}
        },
        {
            "consentId": "marketing",
            "isGiven": True,
            "updatedDate": now,
            "attentionNeeded": False,
            "latestVersion": {"entryDate": 1676246400, "label": "v2"}
        },
        {
            "consentId": "privacy",
            "isGiven": True,
            "updatedDate": now,
            "attentionNeeded": False,
            "latestVersion": {"entryDate": 1688342400, "label": "v3"}
        }
    ]
    return {
        "userId": user_id,
        "consentList": consent_list
    }

@router.get("/consent")
async def get_user_consent(
    request: Request,
    db_users: AsyncSession = Depends(get_user_session),
    db_sessions: AsyncSession = Depends(get_sessions_session),
    onlyAttentionNeeded: bool = False
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
            "latestVersion": {"entryDate": 1688342400, "label": "v4"}
        },
        {
            "consentId": "eula_psn_eu",
            "isGiven": True,
            "updatedDate": 1744010648,
            "attentionNeeded": False,
            "latestVersion": {"entryDate": 1688342400, "label": "v5"}
        },
        {
            "consentId": "eula_psn_na",
            "isGiven": True,
            "updatedDate": 1744010648,
            "attentionNeeded": False,
            "latestVersion": {"entryDate": 1688342400, "label": "v5"}
        },
        {
            "consentId": "marketing",
            "isGiven": True,
            "updatedDate": 1744010648,
            "attentionNeeded": False,
            "latestVersion": {"entryDate": 1676246400, "label": "v2"}
        },
        {
            "consentId": "privacy",
            "isGiven": True,
            "updatedDate": 1744010648,
            "attentionNeeded": False,
            "latestVersion": {"entryDate": 1688342400, "label": "v3"}
        }
    ]
    
    return {
        "userId": user_id,
        "consentList": consent_list
    }

@router.put("/consent")
async def update_user_consent(
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

    data = await request.json()
    # data = {'list': [{'consentId': ..., 'isGiven': ...}, ...]}

    # Тут можешь сохранить согласия юзера в БД, если надо
    # Например:
    # for consent in data['list']:
    #     save_user_consent(user_id, consent['consentId'], consent['isGiven'])

    return {}