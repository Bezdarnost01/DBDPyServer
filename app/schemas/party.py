
from pydantic import BaseModel


class PartyInviteRequest(BaseModel):
    """Класс `PartyInviteRequest` наследуется от BaseModel и описывает структуру приложения."""

    players: list[str]
    ttl: int
