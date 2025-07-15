from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import MetaData

MATCH_DATABASE_URL = "sqlite+aiosqlite:///../data/matchLists.db"

matchs_metadata = MetaData()

class MatchsBase(DeclarativeBase):
    metadata = matchs_metadata

match_engine = create_async_engine(MATCH_DATABASE_URL)
match_sessionmaker = async_sessionmaker(match_engine, expire_on_commit=False)

async def get_matchmaking_session() -> AsyncSession:
    async with match_sessionmaker() as session:
        yield session