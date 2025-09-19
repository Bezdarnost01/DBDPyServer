import base64
import json
import os
import uuid
import zlib
from typing import Any

from Crypto.Cipher import AES
from schemas.config import settings
from schemas.users import UserStats
from sqlalchemy.ext.asyncio import AsyncSession


class UserWorker:
    """Класс `UserWorker` описывает структуру приложения."""

    _default_save_path: str = os.path.join("..", "assets", "default_save.json")
    _cached_default_save: str | None = None

    @staticmethod
    def generate_unique_user_id() -> str:
        """Функция `generate_unique_user_id` выполняет прикладную задачу приложения.
        
        Параметры:
            Отсутствуют.
        
        Возвращает:
            str: Результат выполнения функции.
        """
        return str(uuid.uuid4())

    @staticmethod
    def compress_for_save(data: str) -> str:
        """Функция `compress_for_save` выполняет прикладную задачу приложения.
        
        Параметры:
            data (str): Структура данных.
        
        Возвращает:
            str: Результат выполнения функции.
        """
        return base64.b64encode(zlib.compress(data.encode("utf-8"))).decode("utf-8")

    @staticmethod
    def decompress_from_save(data_b64: str) -> str:
        """Функция `decompress_from_save` выполняет прикладную задачу приложения.
        
        Параметры:
            data_b64 (str): Структура данных.
        
        Возвращает:
            str: Результат выполнения функции.
        """
        return zlib.decompress(base64.b64decode(data_b64)).decode("utf-8")


    @staticmethod
    def encrypt_save_dbhvr(plain_data: Any) -> str:
        """Функция `encrypt_save_dbhvr` выполняет прикладную задачу приложения.
        
        Параметры:
            plain_data (Any): Структура данных.
        
        Возвращает:
            str: Результат выполнения функции.
        """
        if isinstance(plain_data, dict):
            plain_data = json.dumps(plain_data, ensure_ascii=False)
        buf = plain_data.encode("utf-16le")
        buf_len = len(buf)
        bufA = buf_len.to_bytes(4, "little")
        zipped = zlib.compress(buf)
        total = bufA + zipped
        b64 = base64.b64encode(total)
        magic = bytes([0x44, 0x62, 0x64, 0x44, 0x41, 0x51, 0x45, 0x42])
        data = magic + b64
        data = bytearray(data)
        for i in range(len(data)):
            data[i] = (data[i] - 1) % 256
        cipher = AES.new(settings.save_key_bytes, AES.MODE_ECB)
        pad = 32 - (len(data) % 32) if len(data) % 32 != 0 else 32
        data += bytes([0] * pad)
        enc = cipher.encrypt(bytes(data))
        out = base64.b64encode(enc).decode()
        return "DbdDAgAC" + out

    @staticmethod
    def decrypt_save_dbhvr(encrypted: str) -> str:
        """Функция `decrypt_save_dbhvr` выполняет прикладную задачу приложения.
        
        Параметры:
            encrypted (str): Параметр `encrypted`.
        
        Возвращает:
            str: Результат выполнения функции.
        """
        assert encrypted.startswith("DbdDAgAC"), "Invalid DBD save format!"
        encrypted = encrypted[8:]
        data = base64.b64decode(encrypted)
        cipher = AES.new(settings.save_key_bytes, AES.MODE_ECB)
        data = cipher.decrypt(data)
        data = bytearray(data)
        last_nonzero = len(data) - 1
        while last_nonzero >= 0 and data[last_nonzero] == 0:
            last_nonzero -= 1
        data = data[:last_nonzero + 1]
        for i in range(len(data)):
            data[i] = (data[i] + 1) % 256
        data = data[8:]
        data = base64.b64decode(data)
        data = data[4:]
        out = zlib.decompress(data)
        return out.decode("utf-16le")

    @classmethod
    def get_default_save(cls) -> bytes:
        """Функция `get_default_save` выполняет прикладную задачу приложения.
        
        Параметры:
            cls (Any): Класс, к которому привязан метод.
        
        Возвращает:
            bytes: Результат выполнения функции.
        """
        if cls._cached_default_save is None:
            with open(cls._default_save_path, encoding="utf-8") as f:
                data = json.load(f)
            encrypted_str = cls.encrypt_save_dbhvr(data)
            if isinstance(encrypted_str, str):
                cls._cached_default_save = encrypted_str.encode("utf-8")
            else:
                cls._cached_default_save = encrypted_str
        return cls._cached_default_save

    @staticmethod
    def save_json_to_encrypted(save_json: dict) -> str:
        """Функция `save_json_to_encrypted` выполняет прикладную задачу приложения.
        
        Параметры:
            save_json (dict): Параметр `save_json`.
        
        Возвращает:
            str: Результат выполнения функции.
        """
        return UserWorker.encrypt_save_dbhvr(save_json)

    @staticmethod
    async def set_user_save(db: AsyncSession, user_id: str, save_json: dict) -> bool:
        """Функция `set_user_save` выполняет прикладную задачу приложения.
        
        Параметры:
            db (AsyncSession): Подключение к базе данных.
            user_id (str): Идентификатор пользователя.
            save_json (dict): Параметр `save_json`.
        
        Возвращает:
            bool: Результат выполнения функции.
        """
        from crud.users import UserManager

        user = await UserManager.get_user(db, user_id=user_id)
        if not user:
            msg = "User not found"
            raise Exception(msg)

        save_bin = UserWorker.encrypt_save_dbhvr(save_json)
        if isinstance(save_bin, str):
            save_bin = save_bin.encode("utf-8")

        result = await UserManager.update_save_data(db=db, user_id=user_id, save_data=save_bin)

        if result:
            return True
        return None

    @staticmethod
    def encrypted_to_json(save_encrypted: str) -> dict:
        """Функция `encrypted_to_json` выполняет прикладную задачу приложения.
        
        Параметры:
            save_encrypted (str): Параметр `save_encrypted`.
        
        Возвращает:
            dict: Результат выполнения функции.
        """
        return json.loads(UserWorker.decrypt_save_dbhvr(save_encrypted))

    @staticmethod
    async def get_user_json_save(db: AsyncSession, user_id: str) -> dict:
        """Функция `get_user_json_save` выполняет прикладную задачу приложения.
        
        Параметры:
            db (AsyncSession): Подключение к базе данных.
            user_id (str): Идентификатор пользователя.
        
        Возвращает:
            dict: Результат выполнения функции.
        """
        from crud.users import UserManager

        user = await UserManager.get_user(db, user_id=user_id)
        if not user:
            msg = "User not found"
            raise Exception(msg)

        return UserWorker.encrypted_to_json(user.save_data.decode("utf-8"))



    @staticmethod
    async def set_experience_in_save(db: AsyncSession, *, user_id: str | None = None, steam_id: int | None = None, new_experience: int) -> bool:
        """Функция `set_experience_in_save` выполняет прикладную задачу приложения.
        
        Параметры:
            db (AsyncSession): Подключение к базе данных.
            user_id (str | None): Идентификатор пользователя. Значение по умолчанию: None.
            steam_id (int | None): Идентификатор steam. Значение по умолчанию: None.
            new_experience (int): Параметр `new_experience`.
        
        Возвращает:
            bool: Результат выполнения функции.
        """
        from crud.users import UserManager
        user = await UserManager.get_user(db, user_id=user_id, steam_id=steam_id)
        if not user:
            msg = "User not found"
            raise Exception(msg)
        save_dict = UserWorker.encrypted_to_json(user.save_data.decode("utf-8"))

        if "experience" in save_dict:
            save_dict["experience"] = new_experience
        else:
            items = list(save_dict.items())
            new_items = []
            inserted = False
            for k, v in items:
                new_items.append((k, v))
                if k == "lastSurvivorMatchEndTime":
                    new_items.append(("experience", new_experience))
                    inserted = True
            if not inserted:
                new_items.append(("experience", new_experience))
            save_dict = dict(new_items)

        encrypted_save = UserWorker.save_json_to_encrypted(save_dict)
        await UserManager.update_save_data(
            db,
            user_id=user_id,
            steam_id=steam_id,
            save_data=encrypted_save.encode("utf-8"),
        )
        return True

    @staticmethod
    async def get_stats_from_save(db: AsyncSession, *, user_id: str | None = None, steam_id: int | None = None) -> dict:
        """Функция `get_stats_from_save` выполняет прикладную задачу приложения.
        
        Параметры:
            db (AsyncSession): Подключение к базе данных.
            user_id (str | None): Идентификатор пользователя. Значение по умолчанию: None.
            steam_id (int | None): Идентификатор steam. Значение по умолчанию: None.
        
        Возвращает:
            dict: Результат выполнения функции.
        """
        from crud.users import UserManager
        user = await UserManager.get_user(db, user_id=user_id, steam_id=steam_id)
        if not user:
            msg = "User not found"
            raise Exception(msg)
        save_dict = UserWorker.encrypted_to_json(user.save_data.decode("utf-8"))

        stats = {
            "experience": save_dict.get("experience", 0),
            "playerUId": save_dict.get("playerUId"),
            "selectedCamperIndex": save_dict.get("selectedCamperIndex"),
            "selectedSlasherIndex": save_dict.get("selectedSlasherIndex"),
            "firstTimePlaying": save_dict.get("firstTimePlaying"),
            "consecutiveMatchStreak": save_dict.get("consecutiveMatchStreak"),
            "currentSeasonTicks": save_dict.get("currentSeasonTicks"),
            "lastConnectedCharacterIndex": save_dict.get("lastConnectedCharacterIndex"),
            "disconnectPenaltyTime": save_dict.get("disconnectPenaltyTime"),
            "lastMatchEndTime": save_dict.get("lastMatchEndTime"),
            "lastMatchStartTime": save_dict.get("lastMatchStartTime"),
            "lastKillerMatchEndTime": save_dict.get("lastKillerMatchEndTime"),
            "lastSurvivorMatchEndTime": save_dict.get("lastSurvivorMatchEndTime"),
        }
        return UserStats(**stats)
