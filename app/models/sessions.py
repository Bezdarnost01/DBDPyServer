from db.sessions import SessionsBase
from sqlalchemy import Integer, String, Column

class Sessions(SessionsBase):
    __tablename__ = "sessions"
    id = Column(Integer, primary_key=True)
    code = Column(String)
