from typing import Literal

from pydantic import BaseModel


class QueueRequest(BaseModel):
    """Класс `QueueRequest` наследуется от BaseModel и описывает структуру приложения."""

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
    """Класс `CustomData` наследуется от BaseModel и описывает структуру приложения."""

    SessionSettings: str
