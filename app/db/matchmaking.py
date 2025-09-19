from sqlalchemy import MetaData, event
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

MATCH_DATABASE_URL = "sqlite+aiosqlite:///../data/MatchBase.db"

matchs_metadata = MetaData()

class MatchsBase(DeclarativeBase):
    """Класс `MatchsBase` наследуется от DeclarativeBase и описывает структуру приложения."""

    metadata = matchs_metadata

match_engine = create_async_engine(MATCH_DATABASE_URL)
match_sessionmaker = async_sessionmaker(match_engine, expire_on_commit=False)

@event.listens_for(match_engine.sync_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record) -> None:
    """Функция `set_sqlite_pragma` выполняет прикладную задачу приложения.
    
    Параметры:
        dbapi_connection (Any): Подключение к базе данных.
        connection_record (Any): Параметр `connection_record`.
    
    Возвращает:
        None: Функция не возвращает значение.
    """

    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")   # включаем WAL
    cursor.execute("PRAGMA synchronous=NORMAL;") # рекомендуемая связка
    cursor.close()

async def get_matchmaking_session() -> AsyncSession:
    """Функция `get_matchmaking_session` выполняет прикладную задачу приложения.
    
    Параметры:
        Отсутствуют.
    
    Возвращает:
        AsyncSession: Результат выполнения функции.
    """

    async with match_sessionmaker() as session:
        yield session
