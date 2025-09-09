from db.users import UsersBase
from sqlalchemy import BigInteger, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship


class UserWallet(UsersBase):
    __tablename__ = "user_wallet"
    id = Column(Integer, primary_key=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    currency = Column(String)
    balance = Column(BigInteger, default=0)
    user = relationship("Users", back_populates="wallet")
