from sqlalchemy import Column, Integer, String, DateTime, BigInteger, JSON, func
from sqlalchemy.ext.mutable import MutableList, MutableDict
from sqlalchemy.orm import declarative_base

from db.matchmaking import MatchsBase

class Party(MatchsBase):
    __tablename__ = "parties"
    party_id = Column(String, primary_key=True, index=True)
    host_player_id = Column(String, nullable=False)
    privacy_state = Column(String, default='public')
    player_limit = Column(Integer, default=4)
    auto_join_key = Column(BigInteger)
    expiry_time = Column(BigInteger)
    player_count = Column(Integer, default=1)
    game_specific_state = Column(MutableDict.as_mutable(JSON), default=dict)
    members = Column(MutableList.as_mutable(JSON), default=list)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
