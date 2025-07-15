from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime

class SessionCreate(BaseModel):
    bhvr_session: str
    steam_id: int
    expires: int

    model_config = ConfigDict(from_attributes=False)

class SessionRead(BaseModel):
    id: int
    bhvr_session: str
    steam_id: int
    expires: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)