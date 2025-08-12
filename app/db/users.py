from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import MetaData, event

USERS_DATABASE_URL = "sqlite+aiosqlite:///../data/USERS.db"

users_metadata = MetaData()

class UsersBase(DeclarativeBase):
    metadata = users_metadata

user_engine = create_async_engine(USERS_DATABASE_URL)
users_sessionmaker = async_sessionmaker(user_engine, expire_on_commit=False)

@event.listens_for(user_engine.sync_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.execute("PRAGMA synchronous=NORMAL;")
    cursor.close()

async def get_user_session() -> AsyncSession:
    async with users_sessionmaker() as session:
        yield session