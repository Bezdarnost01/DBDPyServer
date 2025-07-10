from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import MetaData

SESSIONS_DATABASE_URL = "sqlite+aiosqlite:///../data/SESSIONS.db"

sessions_metadata = MetaData()

class SessionsBase(DeclarativeBase):
    metadata = sessions_metadata

sessions_engine = create_async_engine(SESSIONS_DATABASE_URL)
sessions_sessionmaker = async_sessionmaker(sessions_engine, expire_on_commit=False)
