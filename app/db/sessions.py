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
    """Класс `SessionsBase` наследуется от DeclarativeBase и описывает структуру приложения."""

    metadata = sessions_metadata

sessions_engine = create_async_engine(SESSIONS_DATABASE_URL)
sessions_sessionmaker = async_sessionmaker(sessions_engine, expire_on_commit=False)

@event.listens_for(sessions_engine.sync_engine, "connect")
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

async def get_sessions_session() -> AsyncSession:
    """Функция `get_sessions_session` выполняет прикладную задачу приложения.
    
    Параметры:
        Отсутствуют.
    
    Возвращает:
        AsyncSession: Результат выполнения функции.
    """

    async with sessions_sessionmaker() as session:
        yield session
