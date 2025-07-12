from fastapi import APIRouter, Depends, HTTPException, Response, Request
from sqlalchemy.ext.asyncio import AsyncSession
from schemas.config import settings
from db.users import get_user_session
from db.sessions import get_sessions_session
import time
from crud.sessions import SessionManager
from crud.users import UserManager

router = APIRouter(prefix=settings.api_prefix, tags=["Reward"])

@router.get("/messages/list")

async def get_messages_list(limit: int = 100):
    now = int(time.time())
    messages = [
        {
            "expireAt": now + 86400 * 2,  # expires через 2 дня
            "received": now * 1000 + 1,
            "flag": "READ",
            "gameSpecificData": {},
            "read": True,
            "allowedPlatforms": [
                "egs", "grdk", "ps4", "ps5", "stadia", "steam", "switch", "xbox", "xsx"
            ],
            "message": {
                "title": "Login Reward",
                "body": "{\"sections\":[{\"type\":\"text\",\"text\":\"Enjoy your daily login reward\"},{\"type\":\"itemshowcase\",\"rewards\":[{\"type\":\"currency\",\"id\":\"BonusBloodpoints\",\"amount\":50000},{\"type\":\"currency\",\"id\":\"Shards\",\"amount\":300}]}]}",
                "claimable": {
                    "type": "reward",
                    "data": [
                        {"type": "currency", "amount": 50000, "id": "BonusBloodpoints"},
                        {"type": "currency", "amount": 300, "id": "Shards"}
                    ],
                    "state": "CLAIMED"
                }
            },
            "tag": ["inbox"],
            "userMinVersion": "2.6.0",
            "translationId": "302b5877-aecc-4c5c-a723-959149c92610",
            "recipientId": "system"
        },
        {
            "expireAt": now + 86400 * 5,  # expires через 5 дней
            "received": now * 1000,
            "flag": "UNREAD",
            "gameSpecificData": {},
            "read": False,
            "allowedPlatforms": [
                "egs", "grdk", "ps4", "ps5", "stadia", "steam", "switch", "xbox", "xsx"
            ],
            "message": {
                "title": "Login Reward",
                "body": "{\"sections\":[{\"type\":\"text\",\"text\":\"Enjoy your login reward\"},{\"type\":\"itemshowcase\",\"rewards\":[{\"type\":\"currency\",\"id\":\"SpringEventCurrency\",\"amount\":100}]}]}",
                "claimable": {
                    "type": "reward",
                    "data": [
                        {"type": "currency", "amount": 50000, "id": "BonusBloodpoints"},
                        {"type": "currency", "amount": 300, "id": "Shards"}
                    ],
                    "state": "UNCLAIMED"
                }
            },
            "tag": ["inbox"],
            "userMinVersion": "2.6.0",
            "translationId": "8fcd0cc6-b7d1-4d59-905d-dc08be33d0e3",
            "recipientId": "system"
        }
    ]
    return {"messages": messages[:limit]}