from pydantic_settings import BaseSettings, SettingsConfigDict
from schemas.utils import ContentVersionResponse, ValidateChallengeResponse
from pydantic import BaseModel
import json

class VersionConfig(BaseModel):
    coreVersion: str
    krakenVersion: str

class Settings(BaseSettings):
    api_prefix: str
    version: VersionConfig
    content_version: ContentVersionResponse
    save_key: str
    eac_challenge: str
    validate_challenge: ValidateChallengeResponse
    cleanup_interval: int
    bonus_bloodpoints: int
    next_rank_reset_date: int

    model_config = SettingsConfigDict(env_file="configs/.env", env_file_encoding="utf-8")

    @classmethod
    def model_validate_json(cls, value: str):
        return json.loads(value)
    
    @property
    def save_key_bytes(self) -> bytes:
        return self.save_key.encode()

settings = Settings()
