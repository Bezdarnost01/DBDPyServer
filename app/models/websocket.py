from datetime import datetime

import pytz
from db.sessions import SessionsBase
from sqlalchemy import Boolean, Column, DateTime, Integer, String

MOSCOW = pytz.timezone("Europe/Moscow")

class WebsocketSession(SessionsBase):
    """Класс `WebsocketSession` наследуется от SessionsBase и описывает структуру приложения."""

    __tablename__ = "websocket_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, nullable=False, index=True)
    connected_at = Column(DateTime, default=lambda: datetime.now(MOSCOW))
    disconnected_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
