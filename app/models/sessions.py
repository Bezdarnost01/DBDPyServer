from datetime import datetime

import pytz
from db.sessions import SessionsBase
from sqlalchemy import BigInteger, Column, DateTime, Integer, String

MOSCOW = pytz.timezone("Europe/Moscow")

class Sessions(SessionsBase):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True)
    bhvr_session = Column(String, unique=True, nullable=False)
    user_id = Column(String, nullable=False)
    steam_id = Column(BigInteger, nullable=False)
    expires = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.now(MOSCOW))
