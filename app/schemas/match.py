
from pydantic import BaseModel


class MatchData(BaseModel):
    matchTime: int
    matchId: str
    isFirstMatch: bool
    consecutiveMatch: int
    playerType: str
    emblemQualities: list[str]
    platformVersion: str
    levelVersion: int
