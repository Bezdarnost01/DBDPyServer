import json

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

from schemas.utils import ContentVersionResponse, ValidateChallengeResponse


class VersionConfig(BaseModel):
    """Класс `VersionConfig` наследуется от BaseModel и описывает структуру приложения."""

    coreVersion: str
    krakenVersion: str


class Settings(BaseSettings):
    """Класс `Settings` наследуется от BaseSettings и описывает структуру приложения."""

    api_prefix: str
    version: VersionConfig
    content_version: ContentVersionResponse
    save_key: str
    eac_challenge: str
    validate_challenge: ValidateChallengeResponse
    cleanup_interval: int
    bonus_bloodpoints: int
    next_rank_reset_date: int
    redis_url: str
    api_admin_prefix: str
    ip_admin_list: list

    model_config = SettingsConfigDict(env_file="configs/.env", env_file_encoding="utf-8")

    @classmethod
    def model_validate_json(cls, value: str):
        """Функция `model_validate_json` выполняет прикладную задачу приложения.
        
        Параметры:
            cls (Any): Класс, к которому привязан метод.
            value (str): Параметр `value`.
        
        Возвращает:
            Any: Результат выполнения функции.
        """

        return json.loads(value)

    @property
    def save_key_bytes(self) -> bytes:
        """Функция `save_key_bytes` выполняет прикладную задачу приложения.
        
        Параметры:
            self (Any): Текущий экземпляр класса.
        
        Возвращает:
            bytes: Результат выполнения функции.
        """

        return self.save_key.encode()


settings = Settings()
