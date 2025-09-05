from pydantic import BaseModel
from typing import List

class MatchData(BaseModel):
    matchTime: int
    matchId: str
    isFirstMatch: bool
    consecutiveMatch: int
    playerType: str
    emblemQualities: List[str]
    platformVersion: str
    levelVersion: int