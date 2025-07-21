from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.sql import func
from db.sessions import SessionsBase
from datetime import datetime
import pytz

MOSCOW = pytz.timezone("Europe/Moscow")

class WebsocketSession(SessionsBase):
    __tablename__ = "websocket_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, nullable=False, index=True)
    session_id = Column(String, unique=True, nullable=False)
    token1 = Column(String, nullable=True)
    token2 = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.now(MOSCOW))
    is_active = Column(Boolean, default=True)
    user_agent = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)

    def __repr__(self):
        return f"<WS user_id={self.user_id} session_id={self.session_id} active={self.is_active}>"
