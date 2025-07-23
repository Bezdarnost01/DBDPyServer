from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import datetime
from typing import List

class PartyInviteRequest(BaseModel):
    players: List[str]
    ttl: int