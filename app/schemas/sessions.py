from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SessionCreate(BaseModel):
    """Класс `SessionCreate` наследуется от BaseModel и описывает структуру приложения."""

    bhvr_session: str
    steam_id: int
    expires: int

    model_config = ConfigDict(from_attributes=False)

class SessionRead(BaseModel):
    """Класс `SessionRead` наследуется от BaseModel и описывает структуру приложения."""

    id: int
    bhvr_session: str
    steam_id: int
    expires: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
