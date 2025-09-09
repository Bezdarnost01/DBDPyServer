
from pydantic import BaseModel


class HealthResponse(BaseModel):
    health: str

class VersionResponse(BaseModel):
    version: str

class ContentVersionResponse(BaseModel):
    availableVersions: dict[str, str]

class EacChallengeResponse(BaseModel):
    challenge: str

class ValidateChallengeResponse(BaseModel):
    valid: bool
    stateUpdated: bool

class ClientVersionResponse(BaseModel):
    isValid: bool
