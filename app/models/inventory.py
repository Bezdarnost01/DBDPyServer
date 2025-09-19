from db.users import UsersBase
from sqlalchemy import BigInteger, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship


class UserInventory(UsersBase):
    """Класс `UserInventory` наследуется от UsersBase и описывает структуру приложения."""

    __tablename__ = "user_inventory"
    id = Column(Integer, primary_key=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    object_id = Column(String)
    quantity = Column(Integer, default=1)
    last_update_at = Column(BigInteger)
    user = relationship("Users", back_populates="inventory")
