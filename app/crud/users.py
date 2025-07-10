from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from models.users import Users as DBUser
from schemas.users import UserCreate

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