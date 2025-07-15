import asyncio
from db.users import user_engine
from sqlalchemy.ext.asyncio import AsyncSession
from crud.users import UserManager
from utils.users import UserWorker
from configs.config import CURRENCIES

async def main():
    user_id = "23096e31-f029-40dd-8054-ce80694c4117"
    async with AsyncSession(user_engine) as session:
        # Получаем текущие значения из кошелька (базы)
        wallets = await UserManager.get_wallet(session, user_id=user_id) or []
        balances = {w.currency: w.balance for w in wallets}
        print(f"[БАЗА] Текущее состояние кошелька (balances): {balances}")

        # Получаем Bloodpoints из сейва ДО синхронизации
        stats_before = await UserWorker.get_stats_from_save(session, user_id=user_id)
        print(f"[СЕЙВ] Bloodpoints (experience) до синхронизации: {stats_before.experience}")

        # Берём Bloodpoints из базы
        bloodpoints_db = balances.get("Bloodpoints", 0)
        print(f"[БАЗА] Bloodpoints: {bloodpoints_db}")

        # Обновляем сейв (experience) до значения из базы
        await UserWorker.set_experience_in_save(session, user_id=user_id, new_experience=10000000)
        print(f"[ОБНОВЛЕНИЕ] Обновили experience в сейве до {bloodpoints_db}")

        # Проверяем Bloodpoints в сейве ПОСЛЕ синхронизации
        stats_after = await UserWorker.get_stats_from_save(session, user_id=user_id)
        print(f"[СЕЙВ] Bloodpoints (experience) после синхронизации: {stats_after.experience}")

        # Итоговое формирование ответа (эмулируем return FastAPI)
        wallets_dict = [
            {
                "balance": balances.get(currency, 0),
                "currency": currency
            }
            for currency in CURRENCIES
        ]
        print(f"[ОТВЕТ] wallets_dict: {wallets_dict}")

if __name__ == "__main__":
    asyncio.run(main())
