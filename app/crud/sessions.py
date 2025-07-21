from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, update, func
from models.sessions import Sessions
from datetime import datetime, timezone
import pytz

MOSCOW = pytz.timezone("Europe/Moscow")

class SessionManager:
    """
    Менеджер для работы сессиями пользователей.
    """
    @staticmethod
    async def create_session(db: AsyncSession, bhvr_session: str, user_id: str, steam_id: int, expires: int) -> Sessions:
        """
        Создаёт новую сессию пользователя.

        Args:
            db (AsyncSession): Сессия БД.
            bhvr_session (str): Строка идентификатора сессии.
            user_id (str): user_id Пользователя
            steam_id (int): Steam ID пользователя.
            expires (int): Время истечения сессии (UNIX timestamp).

        Returns:
            Sessions: Созданная сессия.
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
    async def delete_session(db: AsyncSession, bhvr_session: str) -> int:
        """
        Удаляет сессию по её bhvr_session.

        Args:
            db (AsyncSession): Сессия БД.
            bhvr_session (str): Идентификатор сессии.

        Returns:
            int: Количество удалённых строк.
        """
        stmt = delete(Sessions).where(Sessions.bhvr_session == bhvr_session)
        result = await db.execute(stmt)
        await db.commit()
        return result.rowcount

    @staticmethod
    async def extend_session(db: AsyncSession, bhvr_session: str, extend_seconds: int) -> bool:
        """
        Продлевает жизнь сессии на N секунд от текущего времени.

        Args:
            db (AsyncSession): Сессия БД.
            bhvr_session (str): Идентификатор сессии.
            extend_seconds (int): Сколько секунд добавить.

        Returns:
            bool: True если успешно, иначе False.
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
        """
        Получает steam_id по bhvr_session.

        Args:
            db (AsyncSession): Сессия БД.
            bhvr_session (str): Идентификатор сессии.

        Returns:
            int | None: Steam ID или None если не найдено.
        """
        stmt = select(Sessions).where(Sessions.bhvr_session == bhvr_session)
        result = await db.execute(stmt)
        session = result.scalar_one_or_none()
        return session.steam_id if session else None
    
    @staticmethod
    async def get_user_id_by_session(db: AsyncSession, bhvr_session: str) -> str | None:
        """
        Получает user_id по bhvr_session.

        Args:
            db (AsyncSession): Сессия БД.
            bhvr_session (str): Идентификатор сессии.

        Returns:
            str | None: User ID или None если не найдено.
        """
        stmt = select(Sessions).where(Sessions.bhvr_session == bhvr_session)
        result = await db.execute(stmt)
        session = result.scalar_one_or_none()
        return session.user_id if session else None

    @staticmethod
    async def refresh_session_if_needed(db: AsyncSession, bhvr_session: str, threshold: int = 15 * 60, extend_seconds: int = 40 * 60) -> bool:
        """
        Продлевает сессию, если до истечения осталось меньше threshold секунд.

        Args:
            db (AsyncSession): Сессия БД.
            bhvr_session (str): Идентификатор сессии.
            threshold (int): Порог в секундах, по достижении которого продлеваем.
            extend_seconds (int): На сколько продлевать.

        Returns:
            bool: True если продлили, False если не было необходимости или не найдено.
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
        """
        Удаляет все сессии, срок которых истёк.

        Args:
            db (AsyncSession): Сессия БД.

        Returns:
            int: Количество удалённых сессий.
        """
        now = int(datetime.now(MOSCOW).timestamp())
        stmt = delete(Sessions).where(Sessions.expires < now)
        result = await db.execute(stmt)
        await db.commit()
        return result.rowcount

    @staticmethod
    async def get_sessions_count(db: AsyncSession) -> int:
        """
        Получает текущее количество онлайн сессий.

        Args:
            db (AsyncSession): Сессия БД.

        Returns:
            int: Количество сессий.
        """
        now = int(datetime.now(MOSCOW).timestamp())
        stmt = select(func.count()).select_from(Sessions).where(Sessions.expires > now)
        result = await db.execute(stmt)
        count = result.scalar_one()
        return count
    
    async def get_all_online_user_ids(db: AsyncSession) -> set[str]:
        """
        Возвращает set user_id всех пользователей с активной сессией.
        """
        result = await db.execute(select(Sessions.user_id))
        return set(result.scalars().all())