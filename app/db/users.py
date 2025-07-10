from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import MetaData

USERS_DATABASE_URL = "sqlite+aiosqlite:///./USERS.db"

users_metadata = MetaData()

class UsersBase(DeclarativeBase):
    metadata = users_metadata

user_engine = create_async_engine(USERS_DATABASE_URL)
users_sessionmaker = async_sessionmaker(user_engine, expire_on_commit=False)
