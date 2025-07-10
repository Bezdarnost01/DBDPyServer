from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime

class UserCreate(BaseModel):
    steam_id: int
    user_id: Optional[str] = None
    save_data: Optional[str] = None

    model_config = ConfigDict(from_attributes=False)

class UserRead(BaseModel):
    id: int
    user_id: str
    steam_id: int
    created_at: datetime
    last_login: Optional[datetime] = None
    save_data: str
    is_banned: bool

    model_config = ConfigDict(from_attributes=True)