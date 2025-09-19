
from pydantic import BaseModel


class MatchData(BaseModel):
    """Класс `MatchData` наследуется от BaseModel и описывает структуру приложения."""

    matchTime: int
    matchId: str
    isFirstMatch: bool
    consecutiveMatch: int
    playerType: str
    emblemQualities: list[str]
    platformVersion: str
    levelVersion: int
