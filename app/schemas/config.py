from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import BaseModel
from schemas.utils import ContentVersionResponse
import json

class VersionConfig(BaseModel):
    coreVersion: str
    krakenVersion: str

class Settings(BaseSettings):
    api_prefix: str
    version: VersionConfig
    content_version: ContentVersionResponse
    save_key: str

    model_config = SettingsConfigDict(env_file="configs/.env", env_file_encoding="utf-8")

    @classmethod
    def model_validate_json(cls, value: str):
        return json.loads(value)

settings = Settings()
