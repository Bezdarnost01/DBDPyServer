import pytz
from db.users import UsersBase
from datetime import datetime
from sqlalchemy import Integer, BigInteger, String, Column, DateTime, Text, Boolean
from utils.users import UserWorker

MOSCOW = pytz.timezone("Europe/Moscow")

class Users(UsersBase):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    user_id = Column(String, default=UserWorker.generate_unique_user_id)
    steam_id = Column(BigInteger, default=None)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(MOSCOW))
    last_login = Column(DateTime(timezone=True), default=None)
    save_data = Column(Text, default=UserWorker.get_default_save)
    is_banned = Column(Boolean, default=False)