from pydantic import BaseModel, ConfigDict, Field
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

class UserProfileBase(BaseModel):
    user_name: Optional[str] = None
    user_code: Optional[str] = None
    user_state: Optional[str] = None
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
    currency: Optional[str] = None
    balance: int = 0

class UserWalletCreate(UserWalletBase):
    user_id: str

class UserWalletRead(UserWalletBase):
    id: int
    user_id: str

    class Config:
        from_attributes=True

class UserInventoryBase(BaseModel):
    object_id: Optional[str] = None
    quantity: int = 1
    last_update_at: Optional[int] = None

class UserInventoryCreate(UserInventoryBase):
    user_id: str

class UserInventoryRead(UserInventoryBase):
    id: int
    user_id: str

    class Config:
        from_attributes=True

class UserStats(BaseModel):
    experience: int = 0
    playerUId: Optional[str]
    selectedCamperIndex: Optional[int]
    selectedSlasherIndex: Optional[int]
    firstTimePlaying: Optional[bool]
    consecutiveMatchStreak: Optional[int]
    currentSeasonTicks: Optional[int]
    lastConnectedCharacterIndex: Optional[int]
    disconnectPenaltyTime: Optional[str]
    lastMatchEndTime: Optional[str]
    lastMatchStartTime: Optional[str]
    lastKillerMatchEndTime: Optional[str]
    lastSurvivorMatchEndTime: Optional[str]

class SessionBase(BaseModel):
    bhvr_session: str
    user_id: str
    steam_id: int
    expires: int

class SessionCreate(SessionBase):
    pass

class SessionRead(SessionBase):
    id: int
    created_at: Optional[datetime]

    class Config:
        from_attributes=True