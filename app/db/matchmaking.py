from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import MetaData, event

MATCH_DATABASE_URL = "sqlite+aiosqlite:///../data/MatchBase.db"

matchs_metadata = MetaData()

class MatchsBase(DeclarativeBase):
    metadata = matchs_metadata

match_engine = create_async_engine(MATCH_DATABASE_URL)
match_sessionmaker = async_sessionmaker(match_engine, expire_on_commit=False)

@event.listens_for(match_engine.sync_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")   # включаем WAL
    cursor.execute("PRAGMA synchronous=NORMAL;") # рекомендуемая связка
    cursor.close()

async def get_matchmaking_session() -> AsyncSession:
    async with match_sessionmaker() as session:
        yield session