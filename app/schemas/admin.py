from pydantic import BaseModel


class KickUserRequest(BaseModel):
    """Класс `KickUserRequest` наследуется от BaseModel и описывает структуру приложения."""

    bhvr_session: str | None = None
    user_id: str | None = None
    steam_id: int | None = None
    steam_name: str | None = None


class BanUserRequest(BaseModel):
    """Класс `BanUserRequest` наследуется от BaseModel и описывает структуру приложения."""

    bhvr_session: str | None = None
    user_id: str | None = None
    steam_id: int | None = None
    steam_name: str | None = None


class SetUserSaveRequest(BaseModel):
    """Класс `SetUserSaveRequest` наследуется от BaseModel и описывает структуру приложения."""

    save_json: dict
