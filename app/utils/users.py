import os
import uuid
import json
import zlib
import base64
from typing import Any, Optional
from schemas.config import settings
from Crypto.Cipher import AES

class UserWorker:
    """
    Утилитный класс для работы с пользовательскими сейвами Dead by Daylight:
    - Полное шифрование/дешифрование по протоколу игры.
    - Конвертация между строкой и JSON.
    - Получение дефолтного сейва из файла.
    """

    _default_save_path: str = os.path.join("..", "assets", "default_save.json")
    _cached_default_save: Optional[str] = None

    @staticmethod
    def generate_unique_user_id() -> str:
        """
        Генерирует уникальный идентификатор пользователя (UUID4).
        """
        return str(uuid.uuid4())

    @staticmethod
    def compress_for_save(data: str) -> str:
        """
        Сжимает строку через zlib и кодирует в base64.
        """
        return base64.b64encode(zlib.compress(data.encode("utf-8"))).decode("utf-8")

    @staticmethod
    def decompress_from_save(data_b64: str) -> str:
        """
        Декодирует строку из base64 и распаковывает из zlib.
        """
        return zlib.decompress(base64.b64decode(data_b64)).decode("utf-8")


    @staticmethod
    def encrypt_save_dbhvr(plain_data: Any) -> str:
        """
        Полностью шифрует сейв по протоколу Dead by Daylight:
        - JSON-строка -> UTF-16LE -> zlib -> base64 -> AES-256-ECB -> base64 + префиксы

        Args:
            plain_data (Any): Исходные данные (dict или str).

        Returns:
            str: Шифрованная строка, совместимая с клиентом DBD.
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
        """
        Дешифрует сейв из протокола Dead by Daylight:
        - Проверяет префикс, base64, AES-256-ECB, postprocessing, zlib, UTF-16LE

        Args:
            encrypted (str): Зашифрованная строка от клиента игры.

        Returns:
            str: Декодированный JSON-сейв (строка).
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
    def get_default_save(cls) -> str:
        """
        Загружает и возвращает дефолтный сейв в виде шифрованной строки для DBD.
        Кэширует результат в памяти (читает файл только при первом вызове).

        Returns:
            str: Шифрованная строка дефолтного сейва (для записи пользователю).
        Raises:
            FileNotFoundError: Если файл шаблона не найден.
        """
        if cls._cached_default_save is None:
            with open(cls._default_save_path, encoding='utf-8') as f:
                data = json.load(f)
            cls._cached_default_save = cls.encrypt_save_dbhvr(data)
        return cls._cached_default_save

    @staticmethod
    def save_json_to_encrypted(save_json: dict) -> str:
        """
        Превращает json-сейв в зашифрованный DBD-формат.
        """
        return UserWorker.encrypt_save_dbhvr(save_json)

    @staticmethod
    def encrypted_to_json(save_encrypted: str) -> dict:
        """
        Превращает зашифрованный сейв DBD в словарь.
        """
        return json.loads(UserWorker.decrypt_save_dbhvr(save_encrypted))
