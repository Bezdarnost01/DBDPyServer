from datetime import datetime

import pytz
from models.sessions import Sessions
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

MOSCOW = pytz.timezone("Europe/Moscow")

class SessionManager:
    """Класс `SessionManager` описывает структуру приложения."""

    @staticmethod
    async def create_session(db: AsyncSession, bhvr_session: str, user_id: str, steam_id: int, expires: int) -> Sessions:
        """Функция `create_session` выполняет прикладную задачу приложения.
        
        Параметры:
            db (AsyncSession): Подключение к базе данных.
            bhvr_session (str): Объект сессии.
            user_id (str): Идентификатор пользователя.
            steam_id (int): Идентификатор steam.
            expires (int): Параметр `expires`.
        
        Возвращает:
            Sessions: Результат выполнения функции.
        """
        await db.execute(delete(Sessions).where(Sessions.steam_id == steam_id))
        await db.commit()

        session = Sessions(
            bhvr_session=bhvr_session,
            user_id=user_id,
            steam_id=steam_id,
            expires=expires,
            created_at=datetime.now(MOSCOW),
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)
        return session

    @staticmethod
    async def delete_session(db: AsyncSession, bhvr_session: str | None = None, user_id: str | None = None) -> int | None:
        """Функция `delete_session` выполняет прикладную задачу приложения.
        
        Параметры:
            db (AsyncSession): Подключение к базе данных.
            bhvr_session (str | None): Объект сессии. Значение по умолчанию: None.
            user_id (str | None): Идентификатор пользователя. Значение по умолчанию: None.
        
        Возвращает:
            int | None: Результат выполнения функции.
        """
        if bhvr_session:
            exists_stmt = select(Sessions).where(Sessions.bhvr_session == bhvr_session)
            res = await db.execute(exists_stmt)
            session = res.scalars().first()
            if not session:
                return None

            stmt = delete(Sessions).where(Sessions.bhvr_session == bhvr_session)
            result = await db.execute(stmt)
            await db.commit()
            return result.rowcount

        if user_id:
            exists_stmt = select(Sessions).where(Sessions.user_id == user_id)
            res = await db.execute(exists_stmt)
            session = res.scalars().first()
            if not session:
                return None

            stmt = delete(Sessions).where(Sessions.user_id == user_id)
            result = await db.execute(stmt)
            await db.commit()
            return result.rowcount

        return False

    @staticmethod
    async def extend_session(db: AsyncSession, bhvr_session: str, extend_seconds: int) -> bool:
        """Функция `extend_session` выполняет прикладную задачу приложения.
        
        Параметры:
            db (AsyncSession): Подключение к базе данных.
            bhvr_session (str): Объект сессии.
            extend_seconds (int): Параметр `extend_seconds`.
        
        Возвращает:
            bool: Результат выполнения функции.
        """
        now = int(datetime.now(MOSCOW).timestamp())
        new_expire = now + extend_seconds

        stmt = (
            update(Sessions)
            .where(Sessions.bhvr_session == bhvr_session)
            .values(expires=new_expire)
        )
        result = await db.execute(stmt)
        await db.commit()
        return result.rowcount > 0

    @staticmethod
    async def get_steam_id_by_session(db: AsyncSession, bhvr_session: str) -> int | None:
        """Функция `get_steam_id_by_session` выполняет прикладную задачу приложения.
        
        Параметры:
            db (AsyncSession): Подключение к базе данных.
            bhvr_session (str): Объект сессии.
        
        Возвращает:
            int | None: Результат выполнения функции.
        """
        stmt = select(Sessions).where(Sessions.bhvr_session == bhvr_session)
        result = await db.execute(stmt)
        session = result.scalar_one_or_none()
        return session.steam_id if session else None

    @staticmethod
    async def get_user_id_by_session(db: AsyncSession, bhvr_session: str) -> str | None:
        """Функция `get_user_id_by_session` выполняет прикладную задачу приложения.
        
        Параметры:
            db (AsyncSession): Подключение к базе данных.
            bhvr_session (str): Объект сессии.
        
        Возвращает:
            str | None: Результат выполнения функции.
        """
        stmt = select(Sessions).where(Sessions.bhvr_session == bhvr_session)
        result = await db.execute(stmt)
        session = result.scalar_one_or_none()
        return session.user_id if session else None

    @staticmethod
    async def get_user_session_by_user_id(db: AsyncSession, user_id: str) -> Sessions | None:
        """Функция `get_user_session_by_user_id` выполняет прикладную задачу приложения.
        
        Параметры:
            db (AsyncSession): Подключение к базе данных.
            user_id (str): Идентификатор пользователя.
        
        Возвращает:
            Sessions | None: Результат выполнения функции.
        """
        stmt = select(Sessions).where(Sessions.user_id == user_id)
        result = await db.execute(stmt)
        session = result.scalar_one_or_none()
        return session if session else None

    @staticmethod
    async def refresh_session_if_needed(db: AsyncSession, bhvr_session: str, threshold: int = 15 * 60, extend_seconds: int = 40 * 60) -> bool:
        """Функция `refresh_session_if_needed` выполняет прикладную задачу приложения.
        
        Параметры:
            db (AsyncSession): Подключение к базе данных.
            bhvr_session (str): Объект сессии.
            threshold (int): Параметр `threshold`. Значение по умолчанию: 15 * 60.
            extend_seconds (int): Параметр `extend_seconds`. Значение по умолчанию: 40 * 60.
        
        Возвращает:
            bool: Результат выполнения функции.
        """
        stmt = select(Sessions).where(Sessions.bhvr_session == bhvr_session)
        result = await db.execute(stmt)
        session = result.scalar_one_or_none()
        if session:
            now = int(datetime.now(MOSCOW).timestamp())
            if session.expires - now < threshold:
                session.expires = now + extend_seconds
                await db.commit()
                return True
        return False

    @staticmethod
    async def remove_expired_sessions(db: AsyncSession) -> int:
        """Функция `remove_expired_sessions` выполняет прикладную задачу приложения.
        
        Параметры:
            db (AsyncSession): Подключение к базе данных.
        
        Возвращает:
            int: Результат выполнения функции.
        """
        now = int(datetime.now(MOSCOW).timestamp())
        stmt = delete(Sessions).where(Sessions.expires < now)
        result = await db.execute(stmt)
        await db.commit()
        return result.rowcount

    @staticmethod
    async def get_sessions_count(db: AsyncSession) -> int:
        """Функция `get_sessions_count` выполняет прикладную задачу приложения.
        
        Параметры:
            db (AsyncSession): Подключение к базе данных.
        
        Возвращает:
            int: Результат выполнения функции.
        """
        now = int(datetime.now(MOSCOW).timestamp())
        stmt = select(func.count()).select_from(Sessions).where(Sessions.expires > now)
        result = await db.execute(stmt)
        return result.scalar_one()

    async def get_all_online_user_ids(self: AsyncSession) -> set[str]:
        """Функция `get_all_online_user_ids` выполняет прикладную задачу приложения.
        
        Параметры:
            self (AsyncSession): Текущий экземпляр класса.
        
        Возвращает:
            set[str]: Результат выполнения функции.
        """
        result = await self.execute(select(Sessions.user_id))
        return set(result.scalars().all())
