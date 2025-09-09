
from pydantic import BaseModel


class PartyInviteRequest(BaseModel):
    players: list[str]
    ttl: int
