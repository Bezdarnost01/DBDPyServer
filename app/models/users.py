from sqlalchemy import Integer, BigInteger, String, Column, DateTime, Boolean, LargeBinary
from sqlalchemy.orm import relationship
from db.users import UsersBase
from utils.users import UserWorker
from datetime import datetime
import pytz

MOSCOW = pytz.timezone("Europe/Moscow")

class Users(UsersBase):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    user_id = Column(String, default=UserWorker.generate_unique_user_id)
    steam_id = Column(BigInteger, default=None)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(MOSCOW))
    last_login = Column(DateTime(timezone=True), default=None)
    save_data = Column(LargeBinary, default=UserWorker.get_default_save)
    is_banned = Column(Boolean, default=False)
    is_first_login = Column(Boolean, default=True)
    xp = Column(Integer, default=0)
    rank = Column(Integer, default=0)
    level = Column(Integer, default=0)
    pips = Column(Integer, default=0)
    killer_pips = Column(Integer, default=0)
    survivor_pips = Column(Integer, default=0)
    prestige_level = Column(Integer, default=0)

    inventory = relationship("UserInventory", back_populates="user", cascade="all, delete-orphan")
    wallet = relationship("UserWallet", back_populates="user", cascade="all, delete-orphan")
