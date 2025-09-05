from .users import Users as Users
from .inventory import UserInventory as UserInventory
from .wallet import UserWallet as UserWallet

from db.users import user_engine, UsersBase
from db.sessions import sessions_engine, SessionsBase
from db.matchmaking import match_engine, MatchsBase

async def init_all_databases():
    async with user_engine.begin() as conn:
        await conn.run_sync(UsersBase.metadata.create_all)
    async with sessions_engine.begin() as conn:
        await conn.run_sync(SessionsBase.metadata.create_all)
    async with match_engine.begin() as conn:
        await conn.run_sync(MatchsBase.metadata.create_all)

__all__ = ["Users", "UserInventory", "UserWallet", "user_engine", "UsersBase"]