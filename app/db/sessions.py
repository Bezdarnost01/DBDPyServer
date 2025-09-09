from sqlalchemy import MetaData, event
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

SESSIONS_DATABASE_URL = "sqlite+aiosqlite:///../data/SESSIONS.db"

sessions_metadata = MetaData()

class SessionsBase(DeclarativeBase):
    metadata = sessions_metadata

sessions_engine = create_async_engine(SESSIONS_DATABASE_URL)
sessions_sessionmaker = async_sessionmaker(sessions_engine, expire_on_commit=False)

@event.listens_for(sessions_engine.sync_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")   # включаем WAL
    cursor.execute("PRAGMA synchronous=NORMAL;") # рекомендуемая связка
    cursor.close()

async def get_sessions_session() -> AsyncSession:
    async with sessions_sessionmaker() as session:
        yield session
