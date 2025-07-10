from db.users import user_engine, UsersBase
from db.sessions import sessions_engine, SessionsBase

async def init_all_databases():
    async with user_engine.begin() as conn:
        await conn.run_sync(UsersBase.metadata.create_all)
    async with sessions_engine.begin() as conn:
        await conn.run_sync(SessionsBase.metadata.create_all)
