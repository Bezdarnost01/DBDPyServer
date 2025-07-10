import pytz
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from models.users import Users as DBUser
from schemas.users import UserCreate

MOSCOW = pytz.timezone("Europe/Moscow")

class UserManager:
    @staticmethod
    async def create_user(db: AsyncSession, user_in: UserCreate) -> DBUser | None:
        """
        Добавляет пользователя в базу данных.

        Args:
            db (AsyncSession): Асинхронная сессия SQLAlchemy.
            user_in (UserCreate): Данные для создания пользователя.

        Returns:
            DBUser | None: Созданный пользователь или None, если steam_id уже существует.
        """
        result = await db.execute(select(DBUser).where(DBUser.steam_id == user_in.steam_id))
        if result.scalar_one_or_none():
            return None
        
        new_user = DBUser(
            steam_id = user_in.steam_id
        )

        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        return new_user

    @staticmethod
    async def get_user(db: AsyncSession, *, user_id: str = None, steam_id: int = None) -> DBUser | None:
        """
        Получение объекта пользователя из базы данных по user_id или steam_id.

        Args:
            db (AsyncSession): Сессия БД.
            user_id (str, optional): ID пользователя.
            steam_id (int, optional): Steam ID пользователя.

        Returns:
            DBUser | None: Найденный пользователь или None.
        """
        if not user_id and not steam_id:
            raise ValueError("Необходимо передать хотя бы user_id или steam_id")

        stmt = select(DBUser).where(
            or_(
                DBUser.user_id == user_id if user_id else False,
                DBUser.steam_id == steam_id if steam_id else False
            )
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
    
    @staticmethod
    async def is_banned(db: AsyncSession, *, user_id: str = None, steam_id: int = None) -> bool | None:
        """
        Проверка: является ли пользователь забаненным.

        Args:
            db (AsyncSession): Сессия БД.
            user_id (str, optional): user_id пользователя.
            steam_id (int, optional): steam_id пользователя.

        Returns:
            bool | None: True/False — если пользователь найден, None — если нет такого пользователя.
        """
        if not user_id and not steam_id:
            raise ValueError("Передайте хотя бы user_id или steam_id")

        stmt = select(DBUser).where(
            or_(
                DBUser.user_id == user_id if user_id else False,
                DBUser.steam_id == steam_id if steam_id else False
            )
        )
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if user is None:
            return None
        return getattr(user, "is_banned", False)
    
    @staticmethod
    async def update_last_login(db: AsyncSession, *, user_id: str = None, steam_id: int = None) -> DBUser | None:
        """
        Обновляет дату последнего входа пользователя.

        Args:
            db (AsyncSession): Сессия БД.
            user_id (str, optional): user_id пользователя.
            steam_id (int, optional): Steam ID пользователя.

        Returns:
            DBUser | None: Обновленный объект пользователя или None если не найден.
        """
        if not user_id and not steam_id:
            raise ValueError("Необходимо передать хотя бы user_id или steam_id")

        stmt = select(DBUser)
        if user_id:
            stmt = stmt.where(DBUser.user_id == user_id)
        elif steam_id:
            stmt = stmt.where(DBUser.steam_id == steam_id)

        result = await db.execute(stmt)
        user = result.scalars().first()

        if not user:
            return None

        user.last_login = datetime.now(MOSCOW)
        await db.commit()
        await db.refresh(user)
        return user