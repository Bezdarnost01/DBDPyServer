from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UserCreate(BaseModel):
    steam_id: int
    user_id: str | None = None
    save_data: str | None = None

    model_config = ConfigDict(from_attributes=False)

class UserRead(BaseModel):
    id: int
    user_id: str
    steam_id: int
    created_at: datetime
    last_login: datetime | None = None
    save_data: str
    is_banned: bool

    model_config = ConfigDict(from_attributes=True)

class UserProfileBase(BaseModel):
    user_name: str | None = None
    user_code: str | None = None
    user_state: str | None = None
    xp: int = 0
    rank: int = 0
    level: int = 0
    pips: int = 0
    killer_pips: int = 0
    survivor_pips: int = 0
    prestige_level: int = 0

class UserProfileCreate(UserProfileBase):
    user_id: str

class UserProfileRead(UserProfileBase):
    id: int
    user_id: str

    class Config:
        from_attributes=True

class UserWalletBase(BaseModel):
    currency: str | None = None
    balance: int = 0

class UserWalletCreate(UserWalletBase):
    user_id: str

class UserWalletRead(UserWalletBase):
    id: int
    user_id: str

    class Config:
        from_attributes=True

class UserInventoryBase(BaseModel):
    object_id: str | None = None
    quantity: int = 1
    last_update_at: int | None = None

class UserInventoryCreate(UserInventoryBase):
    user_id: str

class UserInventoryRead(UserInventoryBase):
    id: int
    user_id: str

    class Config:
        from_attributes=True

class UserStats(BaseModel):
    experience: int = 0
    playerUId: str | None
    selectedCamperIndex: int | None
    selectedSlasherIndex: int | None
    firstTimePlaying: bool | None
    consecutiveMatchStreak: int | None
    currentSeasonTicks: int | None
    lastConnectedCharacterIndex: int | None
    disconnectPenaltyTime: str | None
    lastMatchEndTime: str | None
    lastMatchStartTime: str | None
    lastKillerMatchEndTime: str | None
    lastSurvivorMatchEndTime: str | None

class SessionBase(BaseModel):
    bhvr_session: str
    user_id: str
    steam_id: int
    expires: int

class SessionCreate(SessionBase):
    pass

class SessionRead(SessionBase):
    id: int
    created_at: datetime | None

    class Config:
        from_attributes=True
