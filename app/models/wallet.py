from sqlalchemy import Integer, String, Column, BigInteger, ForeignKey
from sqlalchemy.orm import relationship
from db.users import UsersBase

class UserWallet(UsersBase):
    __tablename__ = "user_wallet"
    id = Column(Integer, primary_key=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    currency = Column(String)
    balance = Column(BigInteger, default=0)
    user = relationship("Users", back_populates="wallet")
