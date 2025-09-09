from pydantic import BaseModel


class KickUserRequest(BaseModel):
    bhvr_session: str | None = None
    user_id: str | None = None
    steam_id: int | None = None
    steam_name: str | None = None

class BanUserRequest(BaseModel):
    bhvr_session: str | None = None
    user_id: str | None = None
    steam_id: int | None = None
    steam_name: str | None = None

class SetUserSaveRequest(BaseModel):
    save_json: dict
