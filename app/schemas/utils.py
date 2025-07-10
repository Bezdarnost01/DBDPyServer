from pydantic import BaseModel
from typing import Dict

class HealthResponse(BaseModel):
    health: str

class VersionResponse(BaseModel):
    version: str

class ContentVersionResponse(BaseModel):
    availableVersions: Dict[str, str]