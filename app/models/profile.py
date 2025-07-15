from sqlalchemy import Integer, BigInteger, String, Column, DateTime, Boolean, LargeBinary, ForeignKey
from sqlalchemy.orm import relationship
from db.users import UsersBase

class UserProfile(UsersBase):
    __tablename__ = "users_profiles"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String, ForeignKey("users.user_id"), nullable=False, unique=True, index=True)
    steam_id = Column(BigInteger)
    user_name = Column(String, default=None)
    user_code = Column(String, default=None)
    user_state = Column(String, default=None)
    xp = Column(Integer, default=0)
    rank = Column(Integer, default=0)
    level = Column(Integer, default=0)
    pips = Column(Integer, default=0)
    killer_pips = Column(Integer, default=0)
    survivor_pips = Column(Integer, default=0)
    prestige_level = Column(Integer, default=0)

    user = relationship("Users", back_populates="profile")
