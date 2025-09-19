from datetime import datetime

import pytz
from models.inventory import UserInventory
from models.profile import UserProfile
from models.users import Users as DBUser
from models.wallet import UserWallet
from schemas.users import UserCreate
from sqlalchemy import bindparam, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

MOSCOW = pytz.timezone("Europe/Moscow")

class UserManager:
    """Класс `UserManager` описывает структуру приложения."""

    @staticmethod
    async def create_user(db: AsyncSession, user_in: UserCreate) -> DBUser | None:
        """Функция `create_user` выполняет прикладную задачу приложения.
        
        Параметры:
            db (AsyncSession): Подключение к базе данных.
            user_in (UserCreate): Параметр `user_in`.
        
        Возвращает:
            DBUser | None: Результат выполнения функции.
        """
        result = await db.execute(select(DBUser).where(DBUser.steam_id == user_in.steam_id))
        if result.scalar_one_or_none():
            return None

        new_user = DBUser(
            steam_id=user_in.steam_id,
        )

        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)

        user_profile = UserProfile(user_id=new_user.user_id)
        db.add(user_profile)
        await db.commit()

        from configs.config import STARTING_WALLET
        for entry in STARTING_WALLET:
            await UserManager.set_wallet_balance(db=db, user_id=new_user.user_id, currency=entry["currency"], balance=entry["balance"])

        return new_user

    @staticmethod
    async def get_user(db: AsyncSession, *, user_id: str | None = None, steam_id: int | None = None) -> DBUser | None:
        """Функция `get_user` выполняет прикладную задачу приложения.
        
        Параметры:
            db (AsyncSession): Подключение к базе данных.
            user_id (str | None): Идентификатор пользователя. Значение по умолчанию: None.
            steam_id (int | None): Идентификатор steam. Значение по умолчанию: None.
        
        Возвращает:
            DBUser | None: Результат выполнения функции.
        """
        if not user_id and not steam_id:
            msg = "Необходимо передать хотя бы user_id или steam_id"
            raise ValueError(msg)

        stmt = select(DBUser).where(
            or_(
                DBUser.user_id == user_id if user_id else False,
                DBUser.steam_id == steam_id if steam_id else False,
            ),
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_profile(db: AsyncSession, user_id: str| None = None, steam_id: int | None = None) -> UserProfile | None:
        """Функция `get_user_profile` выполняет прикладную задачу приложения.
        
        Параметры:
            db (AsyncSession): Подключение к базе данных.
            user_id (str| None): Идентификатор пользователя. Значение по умолчанию: None.
            steam_id (int | None): Идентификатор steam. Значение по умолчанию: None.
        
        Возвращает:
            UserProfile | None: Результат выполнения функции.
        """
        if user_id:
            stmt = select(UserProfile).where(UserProfile.user_id == user_id)
            result = await db.execute(stmt)
            return result.scalar_one_or_none()
        if steam_id:
            stmt = select(UserProfile).where(UserProfile.steam_id == steam_id)
            result = await db.execute(stmt)
            return result.scalar_one_or_none()

        if not user_id and not steam_id:
            msg = "Необходимо передать хотя бы user_id или steam_id"
            raise ValueError(msg)
        return None

    @staticmethod
    async def get_user_profile_by_name(db: AsyncSession, user_name: str) -> UserProfile | None:
        """Функция `get_user_profile_by_name` выполняет прикладную задачу приложения.
        
        Параметры:
            db (AsyncSession): Подключение к базе данных.
            user_name (str): Параметр `user_name`.
        
        Возвращает:
            UserProfile | None: Результат выполнения функции.
        """
        stmt = select(UserProfile).where(UserProfile.user_name == user_name)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def update_user_profile(db: AsyncSession, user_id: str, **fields) -> UserProfile | None:
        """Функция `update_user_profile` выполняет прикладную задачу приложения.
        
        Параметры:
            db (AsyncSession): Подключение к базе данных.
            user_id (str): Идентификатор пользователя.
            **fields (Any): Дополнительные именованные аргументы.
        
        Возвращает:
            UserProfile | None: Результат выполнения функции.
        """
        profile = await UserManager.get_user_profile(db, user_id=user_id)
        if not profile:
            return None
        for key, value in fields.items():
            setattr(profile, key, value)
        await db.commit()
        await db.refresh(profile)
        return profile

    @staticmethod
    async def update_save_data(db: AsyncSession, *, user_id: str | None = None, steam_id: int | None = None, save_data: bytes) -> DBUser | None:
        """Функция `update_save_data` выполняет прикладную задачу приложения.
        
        Параметры:
            db (AsyncSession): Подключение к базе данных.
            user_id (str | None): Идентификатор пользователя. Значение по умолчанию: None.
            steam_id (int | None): Идентификатор steam. Значение по умолчанию: None.
            save_data (bytes): Структура данных.
        
        Возвращает:
            DBUser | None: Результат выполнения функции.
        """
        if not user_id and not steam_id:
            msg = "Необходимо передать хотя бы user_id или steam_id"
            raise ValueError(msg)

        stmt = select(DBUser)
        if user_id:
            stmt = stmt.where(DBUser.user_id == user_id)
        elif steam_id:
            stmt = stmt.where(DBUser.steam_id == steam_id)

        result = await db.execute(stmt)
        user = result.scalars().first()

        if not user:
            return None

        user.save_data = save_data
        await db.commit()
        await db.refresh(user)
        return user

    @staticmethod
    async def ban(db: AsyncSession, *, user_id: str | None = None, steam_id: int | None = None) -> bool | None:
        """Функция `ban` выполняет прикладную задачу приложения.
        
        Параметры:
            db (AsyncSession): Подключение к базе данных.
            user_id (str | None): Идентификатор пользователя. Значение по умолчанию: None.
            steam_id (int | None): Идентификатор steam. Значение по умолчанию: None.
        
        Возвращает:
            bool | None: Результат выполнения функции.
        """
        if not user_id and not steam_id:
            msg = "Передайте хотя бы user_id или steam_id"
            raise ValueError(msg)

        stmt = select(DBUser)
        if user_id:
            stmt = stmt.where(DBUser.user_id == user_id)
        elif steam_id:
            stmt = stmt.where(DBUser.steam_id == steam_id)

        result = await db.execute(stmt)
        user = result.scalars().first()

        if not user:
            return None

        user.is_banned = True
        await db.commit()
        return True

    @staticmethod
    async def unban(db: AsyncSession, *, user_id: str | None = None, steam_id: int | None = None) -> bool | None:
        """Функция `unban` выполняет прикладную задачу приложения.
        
        Параметры:
            db (AsyncSession): Подключение к базе данных.
            user_id (str | None): Идентификатор пользователя. Значение по умолчанию: None.
            steam_id (int | None): Идентификатор steam. Значение по умолчанию: None.
        
        Возвращает:
            bool | None: Результат выполнения функции.
        """
        if not user_id and not steam_id:
            msg = "Передайте хотя бы user_id или steam_id"
            raise ValueError(msg)

        stmt = select(DBUser)
        if user_id:
            stmt = stmt.where(DBUser.user_id == user_id)
        elif steam_id:
            stmt = stmt.where(DBUser.steam_id == steam_id)

        result = await db.execute(stmt)
        user = result.scalars().first()

        if not user:
            return None

        if not getattr(user, "is_banned", False):
            return False

        user.is_banned = False
        await db.commit()
        return True

    @staticmethod
    async def is_banned(db: AsyncSession, *, user_id: str | None = None, steam_id: int | None = None) -> bool | None:
        """Функция `is_banned` выполняет прикладную задачу приложения.
        
        Параметры:
            db (AsyncSession): Подключение к базе данных.
            user_id (str | None): Идентификатор пользователя. Значение по умолчанию: None.
            steam_id (int | None): Идентификатор steam. Значение по умолчанию: None.
        
        Возвращает:
            bool | None: Результат выполнения функции.
        """
        if not user_id and not steam_id:
            msg = "Передайте хотя бы user_id или steam_id"
            raise ValueError(msg)

        stmt = select(DBUser).where(
            or_(
                DBUser.user_id == user_id if user_id else False,
                DBUser.steam_id == steam_id if steam_id else False,
            ),
        )
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if user is None:
            return None
        return getattr(user, "is_banned", False)

    @staticmethod
    async def update_last_login(db: AsyncSession, *, user_id: str | None = None, steam_id: int | None = None) -> DBUser | None:
        """Функция `update_last_login` выполняет прикладную задачу приложения.
        
        Параметры:
            db (AsyncSession): Подключение к базе данных.
            user_id (str | None): Идентификатор пользователя. Значение по умолчанию: None.
            steam_id (int | None): Идентификатор steam. Значение по умолчанию: None.
        
        Возвращает:
            DBUser | None: Результат выполнения функции.
        """
        if not user_id and not steam_id:
            msg = "Необходимо передать хотя бы user_id или steam_id"
            raise ValueError(msg)

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

    @staticmethod
    async def update_user_flag(db: AsyncSession, user_id: str | int, **fields) -> DBUser | None:
        """Функция `update_user_flag` выполняет прикладную задачу приложения.
        
        Параметры:
            db (AsyncSession): Подключение к базе данных.
            user_id (str | int): Идентификатор пользователя.
            **fields (Any): Дополнительные именованные аргументы.
        
        Возвращает:
            DBUser | None: Результат выполнения функции.
        """
        user = await UserManager.get_user(db, user_id=user_id)
        if not user:
            return None

        for key, value in fields.items():
            setattr(user, key, value)

        await db.commit()
        await db.refresh(user)
        return user

    @staticmethod
    async def get_inventory(db: AsyncSession, user_id: str) -> list[UserInventory] | None:
        """Функция `get_inventory` выполняет прикладную задачу приложения.
        
        Параметры:
            db (AsyncSession): Подключение к базе данных.
            user_id (str): Идентификатор пользователя.
        
        Возвращает:
            list[UserInventory] | None: Результат выполнения функции.
        """
        stmt = select(UserInventory).where(UserInventory.user_id == user_id)
        result = await db.execute(stmt)
        inventory = result.scalars().all()

        if not inventory:
            return None

        return inventory

    @staticmethod
    async def add_inventory_item(db: AsyncSession, user_id: str, object_id: str, quantity: int = 1):
        """Функция `add_inventory_item` выполняет прикладную задачу приложения.
        
        Параметры:
            db (AsyncSession): Подключение к базе данных.
            user_id (str): Идентификатор пользователя.
            object_id (str): Идентификатор object.
            quantity (int): Параметр `quantity`. Значение по умолчанию: 1.
        
        Возвращает:
            Any: Результат выполнения функции.
        """
        stmt = select(UserInventory).where(
            UserInventory.user_id == user_id,
            UserInventory.object_id == object_id,
        )
        result = await db.execute(stmt)
        item = result.scalar_one_or_none()
        if item:
            item.quantity += quantity
            item.last_update_at = int(datetime.now().timestamp())
        else:
            item = UserInventory(
                user_id=user_id,
                object_id=object_id,
                quantity=quantity,
                last_update_at=int(datetime.now().timestamp()),
            )
            db.add(item)
        await db.commit()
        await db.refresh(item)
        return item

    @staticmethod

    async def remove_inventory_item(db: AsyncSession, user_id: str, object_id: str) -> bool:
        """Функция `remove_inventory_item` выполняет прикладную задачу приложения.
        
        Параметры:
            db (AsyncSession): Подключение к базе данных.
            user_id (str): Идентификатор пользователя.
            object_id (str): Идентификатор object.
        
        Возвращает:
            bool: Результат выполнения функции.
        """
        stmt = select(UserInventory).where(
            UserInventory.user_id == user_id,
            UserInventory.object_id == object_id,
        )
        result = await db.execute(stmt)
        item = result.scalar_one_or_none()
        if item:
            await db.delete(item)
            await db.commit()
            return True
        return False

    @staticmethod
    async def get_wallet(db: AsyncSession, user_id: str) -> list[UserWallet] | None:
        """Функция `get_wallet` выполняет прикладную задачу приложения.
        
        Параметры:
            db (AsyncSession): Подключение к базе данных.
            user_id (str): Идентификатор пользователя.
        
        Возвращает:
            list[UserWallet] | None: Результат выполнения функции.
        """
        stmt = select(UserWallet).where(UserWallet.user_id == user_id)
        result = await db.execute(stmt)
        wallet = result.scalars().all()

        if not wallet:
            return None

        return wallet

    @staticmethod
    async def update_wallet(db: AsyncSession, user_id: str, currency: str, delta: int) -> "UserWallet":
        """Функция `update_wallet` выполняет прикладную задачу приложения.
        
        Параметры:
            db (AsyncSession): Подключение к базе данных.
            user_id (str): Идентификатор пользователя.
            currency (str): Параметр `currency`.
            delta (int): Параметр `delta`.
        
        Возвращает:
            "UserWallet": Результат выполнения функции.
        """
        stmt = select(UserWallet).where(
            UserWallet.user_id == user_id,
            UserWallet.currency == currency,
        )
        result = await db.execute(stmt)
        entry = result.scalar_one_or_none()
        if entry:
            if entry.balance + delta < 0:
                msg = "Not enough currency!"
                raise ValueError(msg)
            entry.balance += delta
        else:
            entry = UserWallet(user_id=user_id, currency=currency, balance=delta)
            db.add(entry)
        await db.commit()
        await db.refresh(entry)
        return entry

    @staticmethod
    async def set_wallet_balance(db: AsyncSession, user_id: str, currency: str, balance: int):
        """Функция `set_wallet_balance` выполняет прикладную задачу приложения.
        
        Параметры:
            db (AsyncSession): Подключение к базе данных.
            user_id (str): Идентификатор пользователя.
            currency (str): Параметр `currency`.
            balance (int): Параметр `balance`.
        
        Возвращает:
            Any: Результат выполнения функции.
        """

        stmt = select(UserWallet).where(
            UserWallet.user_id == user_id,
            UserWallet.currency == currency,
        )
        result = await db.execute(stmt)
        entry = result.scalar_one_or_none()
        if entry:
            entry.balance = balance
        else:
            entry = UserWallet(user_id=user_id, currency=currency, balance=balance)
            db.add(entry)
        await db.commit()
        await db.refresh(entry)
        return entry

    @staticmethod
    async def get_user_ids_by_steam_ids(db, steam_ids):
        """Функция `get_user_ids_by_steam_ids` выполняет прикладную задачу приложения.
        
        Параметры:
            db (Any): Подключение к базе данных.
            steam_ids (Any): Параметр `steam_ids`.
        
        Возвращает:
            Any: Результат выполнения функции.
        """

        if not steam_ids:
            return {}
        stmt = select(DBUser.steam_id, DBUser.user_id).where(
            DBUser.steam_id.in_(bindparam("steam_ids", expanding=True)),
        )
        result = await db.execute(stmt, {"steam_ids": steam_ids})
        return {str(row.steam_id): row.user_id for row in result.fetchall()}

    @staticmethod
    async def update_player_progress(
        db: AsyncSession,
        user_id: int,
        xp: int,
        level: int,
        prestige_level: int,
    ) -> None:
        """Функция `update_player_progress` выполняет прикладную задачу приложения.
        
        Параметры:
            db (AsyncSession): Подключение к базе данных.
            user_id (int): Идентификатор пользователя.
            xp (int): Параметр `xp`.
            level (int): Параметр `level`.
            prestige_level (int): Параметр `prestige_level`.
        
        Возвращает:
            None: Функция не возвращает значение.
        """
        result = await db.execute(select(DBUser).where(DBUser.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            return

        user.xp = xp
        user.level = level
        user.prestige_level = prestige_level
        await db.commit()
