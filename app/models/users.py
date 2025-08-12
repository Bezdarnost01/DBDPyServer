from sqlalchemy import Integer, BigInteger, String, Column, DateTime, Boolean, LargeBinary
from sqlalchemy.orm import relationship
from db.users import UsersBase
from utils.users import UserWorker
from models.inventory import UserInventory
from models.wallet import UserWallet
from datetime import datetime
import pytz

MOSCOW = pytz.timezone("Europe/Moscow")

class Users(UsersBase):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    user_id = Column(String, default=UserWorker.generate_unique_user_id, index=True)
    steam_id = Column(BigInteger, default=None)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(MOSCOW))
    last_login = Column(DateTime(timezone=True), default=None)
    save_data = Column(LargeBinary, default=UserWorker.get_default_save)
    is_banned = Column(Boolean, default=False)
    is_first_login = Column(Boolean, default=True)

    inventory = relationship("UserInventory", back_populates="user", cascade="all, delete-orphan")
    wallet = relationship("UserWallet", back_populates="user", cascade="all, delete-orphan")
    profile = relationship("UserProfile", back_populates="user", uselist=False)
