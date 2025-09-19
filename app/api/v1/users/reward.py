from fastapi import APIRouter
from schemas.config import settings

router = APIRouter(prefix=settings.api_prefix, tags=["Reward"])


@router.get("/messages/list")
async def get_messages_list(limit: int = 100):
    """Функция `get_messages_list` выполняет прикладную задачу приложения.
    
    Параметры:
        limit (int): Параметр `limit`. Значение по умолчанию: 100.
    
    Возвращает:
        Any: Результат выполнения функции.
    """

    return {"success": True}


@router.get("/messages/claim")
async def claim_reward() -> dict:
    """Функция `claim_reward` выполняет прикладную задачу приложения.
    
    Параметры:
        Отсутствуют.
    
    Возвращает:
        dict: Результат выполнения функции.
    """

    return {
        "inventories": [],
        "currencies": [{"id": "Cells", "newAmount": 25000, "receivedAmount": 12500}],
        "flag": "READ",
    }
