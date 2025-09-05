from sqlalchemy import Column, Integer, String, DateTime, Boolean
from db.sessions import SessionsBase
from datetime import datetime
import pytz

MOSCOW = pytz.timezone("Europe/Moscow")

class WebsocketSession(SessionsBase):
    __tablename__ = "websocket_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, nullable=False, index=True)
    connected_at = Column(DateTime, default=lambda: datetime.now(MOSCOW))
    disconnected_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
