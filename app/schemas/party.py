from pydantic import BaseModel
from typing import List

class PartyInviteRequest(BaseModel):
    players: List[str]
    ttl: int