from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UserCreate(BaseModel):
    """Класс `UserCreate` наследуется от BaseModel и описывает структуру приложения."""

    steam_id: int
    user_id: str | None = None
    save_data: str | None = None

    model_config = ConfigDict(from_attributes=False)


class UserRead(BaseModel):
    """Класс `UserRead` наследуется от BaseModel и описывает структуру приложения."""

    id: int
    user_id: str
    steam_id: int
    created_at: datetime
    last_login: datetime | None = None
    save_data: str
    is_banned: bool

    model_config = ConfigDict(from_attributes=True)


class UserProfileBase(BaseModel):
    """Класс `UserProfileBase` наследуется от BaseModel и описывает структуру приложения."""

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
    """Класс `UserProfileCreate` наследуется от UserProfileBase и описывает структуру приложения."""

    user_id: str


class UserProfileRead(UserProfileBase):
    """Класс `UserProfileRead` наследуется от UserProfileBase и описывает структуру приложения."""

    id: int
    user_id: str

    class Config:
        """Класс `Config` описывает структуру приложения."""

        from_attributes = True


class UserWalletBase(BaseModel):
    """Класс `UserWalletBase` наследуется от BaseModel и описывает структуру приложения."""

    currency: str | None = None
    balance: int = 0


class UserWalletCreate(UserWalletBase):
    """Класс `UserWalletCreate` наследуется от UserWalletBase и описывает структуру приложения."""

    user_id: str


class UserWalletRead(UserWalletBase):
    """Класс `UserWalletRead` наследуется от UserWalletBase и описывает структуру приложения."""

    id: int
    user_id: str

    class Config:
        """Класс `Config` описывает структуру приложения."""

        from_attributes = True


class UserInventoryBase(BaseModel):
    """Класс `UserInventoryBase` наследуется от BaseModel и описывает структуру приложения."""

    object_id: str | None = None
    quantity: int = 1
    last_update_at: int | None = None


class UserInventoryCreate(UserInventoryBase):
    """Класс `UserInventoryCreate` наследуется от UserInventoryBase и описывает структуру приложения."""

    user_id: str


class UserInventoryRead(UserInventoryBase):
    """Класс `UserInventoryRead` наследуется от UserInventoryBase и описывает структуру приложения."""

    id: int
    user_id: str

    class Config:
        """Класс `Config` описывает структуру приложения."""

        from_attributes = True


class UserStats(BaseModel):
    """Класс `UserStats` наследуется от BaseModel и описывает структуру приложения."""

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
    """Класс `SessionBase` наследуется от BaseModel и описывает структуру приложения."""

    bhvr_session: str
    user_id: str
    steam_id: int
    expires: int


class SessionCreate(SessionBase):
    """Класс `SessionCreate` наследуется от SessionBase и описывает структуру приложения."""

    pass


class SessionRead(SessionBase):
    """Класс `SessionRead` наследуется от SessionBase и описывает структуру приложения."""

    id: int
    created_at: datetime | None

    class Config:
        """Класс `Config` описывает структуру приложения."""

        from_attributes = True
