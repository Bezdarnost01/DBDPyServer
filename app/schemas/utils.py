
from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Класс `HealthResponse` наследуется от BaseModel и описывает структуру приложения."""

    health: str


class VersionResponse(BaseModel):
    """Класс `VersionResponse` наследуется от BaseModel и описывает структуру приложения."""

    version: str


class ContentVersionResponse(BaseModel):
    """Класс `ContentVersionResponse` наследуется от BaseModel и описывает структуру приложения."""

    availableVersions: dict[str, str]


class EacChallengeResponse(BaseModel):
    """Класс `EacChallengeResponse` наследуется от BaseModel и описывает структуру приложения."""

    challenge: str


class ValidateChallengeResponse(BaseModel):
    """Класс `ValidateChallengeResponse` наследуется от BaseModel и описывает структуру приложения."""

    valid: bool
    stateUpdated: bool


class ClientVersionResponse(BaseModel):
    """Класс `ClientVersionResponse` наследуется от BaseModel и описывает структуру приложения."""

    isValid: bool
