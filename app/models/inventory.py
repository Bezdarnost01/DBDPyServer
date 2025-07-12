from sqlalchemy import Integer, String, Column, BigInteger, ForeignKey
from sqlalchemy.orm import relationship
from db.users import UsersBase

class UserInventory(UsersBase):
    __tablename__ = "user_inventory"
    id = Column(Integer, primary_key=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"))
    object_id = Column(String)
    quantity = Column(Integer, default=1)
    last_update_at = Column(BigInteger)
    user = relationship("Users", back_populates="inventory")
