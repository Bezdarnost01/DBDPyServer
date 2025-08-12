from pydantic import BaseModel
from typing import Literal

class QueueRequest(BaseModel):
    category: str
    rank: int
    side: Literal["A","B"]
    platform: str
    latencies: list
    additionalUserIds: list
    checkOnly: bool
    region: str
    countA: int
    countB: int

class CustomData(BaseModel):
    SessionSettings: str