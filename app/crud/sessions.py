from datetime import datetime

import pytz
from models.sessions import Sessions
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

MOSCOW = pytz.timezone("Europe/Moscow")

class SessionManager:
    """Менеджер для работы сессиями пользователей."""

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
    async def delete_session(db: AsyncSession, bhvr_session: str | None = None, user_id: str | None = None) -> int | None:
        """
        Удаляет сессию по её bhvr_session.

        Args:
            db (AsyncSession): Сессия БД.
            bhvr_session (str): Идентификатор сессии.

        Returns:
            int: Количество удалённых строк.

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
    async def get_user_session_by_user_id(db: AsyncSession, user_id: str) -> Sessions | None:
        """
        Получает обьект session по user_id.

        Args:
            db (AsyncSession): Сессия БД.
            bhvr_session (str): Идентификатор сессии.

        Returns:
            str | None: session или None если не найдено.

        """
        stmt = select(Sessions).where(Sessions.user_id == user_id)
        result = await db.execute(stmt)
        session = result.scalar_one_or_none()
        return session if session else None

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
        return result.scalar_one()

    async def get_all_online_user_ids(self: AsyncSession) -> set[str]:
        """Возвращает set user_id всех пользователей с активной сессией."""
        result = await self.execute(select(Sessions.user_id))
        return set(result.scalars().all())
