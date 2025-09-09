from fastapi import APIRouter
from schemas.config import settings

router = APIRouter(prefix=settings.api_prefix, tags=["Reward"])

@router.get("/messages/list")
async def get_messages_list(limit: int = 100):
    return {"success": True}

@router.get("/messages/claim")
async def claim_reward() -> None:
    {"inventories":[],"currencies":[{"id":"Cells","newAmount":25000,"receivedAmount":12500}],"flag":"READ"}
