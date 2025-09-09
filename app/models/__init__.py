from db.matchmaking import MatchsBase, match_engine
from db.sessions import SessionsBase, sessions_engine
from db.users import UsersBase, user_engine

from .inventory import UserInventory as UserInventory
from .users import Users as Users
from .wallet import UserWallet as UserWallet


async def init_all_databases() -> None:
    async with user_engine.begin() as conn:
        await conn.run_sync(UsersBase.metadata.create_all)
    async with sessions_engine.begin() as conn:
        await conn.run_sync(SessionsBase.metadata.create_all)
    async with match_engine.begin() as conn:
        await conn.run_sync(MatchsBase.metadata.create_all)

__all__ = ["UserInventory", "UserWallet", "Users", "UsersBase", "user_engine"]
