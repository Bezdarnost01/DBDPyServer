import pytz
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, bindparam
from models.users import Users as DBUser
from models.inventory import UserInventory
from models.wallet import UserWallet
from models.profile import UserProfile
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
    async def get_user_profile(db: AsyncSession, user_id: str| None = None, steam_id: int | None = None) -> UserProfile | None:
        """
        Получает профиль пользователя по user_id.

        Args:
            db (AsyncSession): Асинхронная сессия SQLAlchemy.
            user_id (str | None): Уникальный идентификатор пользователя.
            steam_id (int | None): Стим айди пользователя.

        Returns:
            UserProfile | None: Объект профиля пользователя, если найден, иначе None.

        Пример использования:
        ---------------------
        profile = await UserManager.get_user_profile(db, user_id="abc123")
        if profile:
            print(profile.user_name, profile.xp)
        else:
            print("Профиль не найден")
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
            raise ValueError("Необходимо передать хотя бы user_id или steam_id")
        
    @staticmethod
    async def get_user_profile_by_name(db: AsyncSession, user_name: str) -> UserProfile | None:
        """
        Получает профиль пользователя по user_name.

        Args:
            db (AsyncSession): Асинхронная сессия SQLAlchemy.
            user_id (str): Имя пользователя.

        Returns:
            UserProfile | None: Объект профиля пользователя, если найден, иначе None.

        Пример использования:
        ---------------------
        profile = await UserManager.get_user_profile(db, user_id="abc123")
        if profile:
            print(profile.user_name, profile.xp)
        else:
            print("Профиль не найден")
        """
        stmt = select(UserProfile).where(UserProfile.user_name == user_name)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def update_user_profile(db: AsyncSession, user_id: str, **fields) -> UserProfile | None:
        """
        Обновляет поля профиля пользователя по user_id.

        Args:
            db (AsyncSession): Асинхронная сессия SQLAlchemy.
            user_id (str): Уникальный идентификатор пользователя.
            **fields: Произвольные поля для обновления (например, xp=1000, user_name="NewName").

        Returns:
            UserProfile | None: Обновлённый профиль пользователя, если найден, иначе None.

        Пример использования:
        ---------------------
        profile = await UserManager.update_user_profile(
            db,
            user_id="abc123",
            xp=2000,
            user_name="AwesomePlayer",
            rank=5
        )
        if profile:
            print("Профиль обновлён:", profile.user_name, profile.xp)
        else:
            print("Профиль не найден")
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
    async def update_save_data(db: AsyncSession, *, user_id: str = None, steam_id: int = None, save_data: bytes) -> DBUser | None:
        """
        Обновляет сохрание пользователя.

        Args:
            db (AsyncSession): Сессия БД.
            user_id (str, optional): user_id пользователя.
            steam_id (int, optional): Steam ID пользователя.
            save_data(bytes): Новый бинарный сейв юзера.

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

        user.save_data = save_data
        await db.commit()
        await db.refresh(user)
        return user

    @staticmethod
    async def ban(db: AsyncSession, *, user_id: str = None, steam_id: int = None) -> bool | None:
        """
        Блокировка пользователя.

        Args:
            db (AsyncSession): Сессия БД.
            user_id (str, optional): user_id пользователя.
            steam_id (int, optional): steam_id пользователя.

        Returns:
            bool | None: True/False — если пользователь найден, None — если нет такого пользователя.
        """
        if not user_id and not steam_id:
            raise ValueError("Передайте хотя бы user_id или steam_id")
        
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
    async def unban(db: AsyncSession, *, user_id: str = None, steam_id: int = None) -> bool | None:
        """
        Разблокировка пользователя.

        Args:
            db (AsyncSession): Сессия БД.
            user_id (str, optional): user_id пользователя.
            steam_id (int, optional): steam_id пользователя.

        Returns:
            bool | None: True — если пользователь найден и разбанен,
                        False — если уже не был забанен,
                        None — если пользователь не найден.
        """
        if not user_id and not steam_id:
            raise ValueError("Передайте хотя бы user_id или steam_id")
        
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
    
    @staticmethod
    async def update_user_flag(db: AsyncSession, user_id: str | int, **fields) -> DBUser | None:
        """
        Универсальное обновление любых флагов пользователя.

        Args:
            db (AsyncSession): сессия БД
            user_id (str|int): ID пользователя (user_id или id)
            fields: поля для обновления (например, is_banned=True, first_login_at=False), можно менять сразу несколько полей.
        Returns:
            DBUser | None: обновлённый пользователь или None, если не найден
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
        """
        Получает инвентарь  пользователя.

        Args:
            db (AsyncSession): Сессия БД.
            user_id (str): user_id пользователя.
        Returns:
            list[UserInventory] | None : Обьект инвентаря юзера или None если не найден.
        """
        stmt = select(UserInventory).where(UserInventory.user_id == user_id)
        result = await db.execute(stmt)
        inventory = result.scalars().all()

        if not inventory:
            return None
        
        return inventory

    @staticmethod
    async def add_inventory_item(db: AsyncSession, user_id: str, object_id: str, quantity: int = 1):
        """
        Добавляет предмет в инвентарь пользователя.

        Args:
            db (AsyncSession): Сессия БД.
            user_id (str): user_id пользователя.
            object_id (str): object_id предмета.
            quantity (int): количество предметов.
        Returns:
            list[UserInventory] | None : Обьект инвентаря юзера или None если не найден.
        """
        stmt = select(UserInventory).where(
            UserInventory.user_id == user_id,
            UserInventory.object_id == object_id
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
                last_update_at=int(datetime.now().timestamp())
            )
            db.add(item)
        await db.commit()
        await db.refresh(item)
        return item

    @staticmethod
    
    async def remove_inventory_item(db: AsyncSession, user_id: str, object_id: str) -> bool:
        """
        Удаляет предмет из инвентаря пользователя.

        Args:
            db (AsyncSession): Сессия БД.
            user_id (str): user_id пользователя.
            object_id (str): object_id предмета.
        Returns:
            bool : True если успешно, False если ошибка.
        """
        stmt = select(UserInventory).where(
            UserInventory.user_id == user_id,
            UserInventory.object_id == object_id
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
        """
        Получает кошелек пользователя.

        Args:
            db (AsyncSession): Сессия БД.
            user_id (str): user_id пользователя.
        Returns:
            list[UserWallet] | None : Обьект кошелька юзера или None если не найден.
        """
        stmt = select(UserWallet).where(UserWallet.user_id == user_id)
        result = await db.execute(stmt)
        wallet = result.scalars().all()

        if not wallet:
            return None
        
        return wallet
    
    @staticmethod
    async def update_wallet(db: AsyncSession, user_id: str, currency: str, delta: int) -> "UserWallet":
        """
        Изменяет баланс определённой валюты пользователя.

        Если у пользователя уже есть запись этой валюты в кошельке — увеличивает (или уменьшает) её баланс на заданную величину.
        Если такой записи ещё нет — создаёт новую с указанным балансом.

        Args:
            db (AsyncSession): Асинхронная сессия SQLAlchemy.
            user_id (str): Внутренний ID пользователя (ForeignKey на Users.id).
            currency (str): Название валюты (например, "Shards", "Cells", "Bloodpoints").
            delta (int): Изменение баланса (может быть отрицательным или положительным).

        Returns:
            UserWallet: Объект UserWallet с актуальным балансом пользователя для данной валюты.
        """
        stmt = select(UserWallet).where(
            UserWallet.user_id == user_id,
            UserWallet.currency == currency
        )
        result = await db.execute(stmt)
        entry = result.scalar_one_or_none()
        if entry:
            if entry.balance + delta < 0:
                raise ValueError("Not enough currency!")
            entry.balance += delta
        else:
            entry = UserWallet(user_id=user_id, currency=currency, balance=delta)
            db.add(entry)
        await db.commit()
        await db.refresh(entry)
        return entry
    
    @staticmethod
    async def set_wallet_balance(db: AsyncSession, user_id: str, currency: str, balance: int):
        stmt = select(UserWallet).where(
            UserWallet.user_id == user_id,
            UserWallet.currency == currency
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
        if not steam_ids:
            return {}
        stmt = select(DBUser.steam_id, DBUser.user_id).where(
            DBUser.steam_id.in_(bindparam('steam_ids', expanding=True))
        )
        result = await db.execute(stmt, {"steam_ids": steam_ids})
        return {str(row.steam_id): row.user_id for row in result.fetchall()}
    
    @staticmethod
    async def update_player_progress(
        db: AsyncSession,
        user_id: int,
        xp: int,
        level: int,
        prestige_level: int
    ) -> None:
        """
        Обновляет прогресс игрока в базе:
        XP, уровень, престиж.

        :param db: сессия базы
        :param user_id: ID игрока
        :param xp: новый XP игрока
        :param level: новый уровень игрока
        :param prestige_level: новый престиж игрока
        """
        result = await db.execute(select(DBUser).where(DBUser.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            return

        user.xp = xp
        user.level = level
        user.prestige_level = prestige_level
        await db.commit()