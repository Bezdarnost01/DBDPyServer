import asyncio

from configs.config import CURRENCIES
from crud.users import UserManager
from db.users import user_engine
from sqlalchemy.ext.asyncio import AsyncSession
from utils.users import UserWorker


async def main() -> None:
    user_id = "23096e31-f029-40dd-8054-ce80694c4117"
    async with AsyncSession(user_engine) as session:
        # Получаем текущие значения из кошелька (базы)
        wallets = await UserManager.get_wallet(session, user_id=user_id) or []
        balances = {w.currency: w.balance for w in wallets}

        # Получаем Bloodpoints из сейва ДО синхронизации
        await UserWorker.get_stats_from_save(session, user_id=user_id)

        # Берём Bloodpoints из базы
        balances.get("Bloodpoints", 0)

        # Обновляем сейв (experience) до значения из базы
        await UserWorker.set_experience_in_save(session, user_id=user_id, new_experience=10000000)

        # Проверяем Bloodpoints в сейве ПОСЛЕ синхронизации
        await UserWorker.get_stats_from_save(session, user_id=user_id)

        # Итоговое формирование ответа (эмулируем return FastAPI)
        [
            {
                "balance": balances.get(currency, 0),
                "currency": currency,
            }
            for currency in CURRENCIES
        ]

if __name__ == "__main__":
    asyncio.run(main())
