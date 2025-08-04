import time
import json
from aioredis import Redis
from typing import Literal
import uuid
from .lobby import LobbyManager

class MatchQueue:
    """
    Класс управления матчмейкинг-очередью в Redis для одной из сторон (A/B).
    """
    def __init__(self, redis: Redis, side: str, lobby_manager: LobbyManager):
        self.redis = redis
        self.key = f"queue:{side.upper()}"
        self.max_survivors = 4
        self.lobby_manager = lobby_manager

    async def get_queued_player(self, bhvr_session: str):
        players = await self.redis.lrange(self.key, 0, -1)
        for idx, player_bytes in enumerate(players):
            if not player_bytes:
                continue
            if isinstance(player_bytes, bytes):
                player_str = player_bytes
            else:
                player_str = player_bytes
            try:
                player = json.loads(player_str)
            except Exception:
                continue
            if player["bhvrSession"] == bhvr_session:
                return player, idx
        return None, -1

    async def add_player(self, bhvr_session: str, user_id: str, side: Literal["A", "B"], last_checked_for_match: float = None):
        if side != "A" and self.key.endswith("A"):
            raise Exception("Only side A can create lobby")
        if last_checked_for_match is None:
            last_checked_for_match = time.time()
        player, _ = await self.get_queued_player(bhvr_session)
        if player:
            return
        data = {
            "bhvrSession": bhvr_session,
            "userId": user_id,
            "side": side,
            "lastCheckedForMatch": last_checked_for_match
        }
        await self.redis.rpush(self.key, json.dumps(data))

    async def remove_player(self, bhvr_session: str):
        player, _ = await self.get_queued_player(bhvr_session)
        if not player:
            return False
        player_bytes = json.dumps(player).encode()
        await self.redis.lrem(self.key, 1, player_bytes)
        return True

    async def get_queue_status(self, session):
        """
        Проверяет статус игрока в очереди и лобби.
        Очищает все лобби, где этот игрок хост, если он пытается попасть в sideB.
        Не допускает дублирования userId в sideA и sideB.
        """
        qp, idx = await self.get_queued_player(session['bhvrSession'])
        if not qp:
            return {}

        user_id = qp["userId"]
        side = qp["side"]

        # Если side == "B", очищаем все лобби, где этот игрок хост (sideA)
        if side == "B":
            open_ids = await self.lobby_manager.redis.smembers("lobbies:open")
            to_delete = []
            for lobby_id in open_ids:
                lobby = await self.lobby_manager.get_lobby_by_id(lobby_id)
                if not lobby:
                    continue
                host = lobby.get("host", {})
                # Если игрок является хостом — удаляем это лобби
                if host.get("userId") == user_id:
                    to_delete.append(lobby_id)
            for lobby_id in to_delete:
                await self.lobby_manager.delete_match(lobby_id)

            # После удаления обновляем список лобби
            open_ids = await self.lobby_manager.redis.smembers("lobbies:open")
            for lobby_id in open_ids:
                lobby = await self.lobby_manager.get_lobby_by_id(lobby_id)
                if not lobby:
                    continue

                # Не допускаем дублирования userId в nonHosts
                if any(p["userId"] == user_id for p in lobby["nonHosts"]):
                    continue

                if (
                    lobby.get("isReady", False)
                    and not lobby.get("hasStarted", False)
                    and len(lobby["nonHosts"]) < self.max_survivors
                ):
                    lobby["nonHosts"].append(qp)
                    await self.remove_player(qp["bhvrSession"])
                    await self.lobby_manager.redis.set(f"lobby:{lobby['id']}", json.dumps(lobby))
                    return self._make_matched_response(
                        creator_id=lobby["host"]["userId"],
                        match_id=lobby["id"],
                        side_a=[lobby["host"]["userId"]],
                        side_b=[qp["userId"]],
                    )
            return {
                "queueData": {"ETA": -10000, "position": 0, "sizeA": 0, "sizeB": 1},
                "status": "QUEUED",
            }

        # Проверяем, не является ли этот игрок уже хостом открытого лобби
        existing = await self.lobby_manager.find_lobby_by_host_session(qp["bhvrSession"])
        if existing:
            return self._make_matched_response(
                creator_id=existing["host"]["userId"],
                match_id=existing["id"],
                side_a=[existing["host"]["userId"]],
                side_b=[],
            )

        if side == "A":
            match_id = str(uuid.uuid4())
            await self.lobby_manager.create_lobby(qp, match_id=match_id)
            await self.remove_player(qp["bhvrSession"])
            return self._make_matched_response(
                creator_id=qp["userId"],
                match_id=match_id,
                side_a=[qp["userId"]],
                side_b=[],
            )
        else:
            return {
                "queueData": {"ETA": -10000, "position": 0, "sizeA": 0, "sizeB": 1},
                "status": "QUEUED",
            }
    
    async def create_match_response(lobby_manager: LobbyManager, match_id: str, killed: bool = False):
        lobby = await lobby_manager.get_lobby_by_id(match_id)
        if not lobby:
            lobby = await lobby_manager.get_killed_lobby_by_id(match_id)
        if not lobby:
            return {}
        return {
            "category": "live-138518-live:None:Windows:::1:4:0:G:2",
            "churn": 0,
            "creationDateTime": int(time.time() * 1000),
            "creator": lobby["host"]["userId"],
            "customData": {
                "SessionSettings": lobby.get("sessionSettings", "")
            },
            "geolocation": {},
            "matchId": match_id,
            "props": {"countA": 1, "countB": 4, "gameMode": "None", "platform": "Windows"},
            "rank": 1,
            "reason": lobby.get("reason", ""),
            "schema": 3,
            "sideA": [lobby["host"]["userId"]],
            "sideB": [p["userId"] for p in lobby["nonHosts"]],
            "skill": {"rank": 20, "version": 2, "x": 20},
            "status": "CLOSED" if killed else "OPENED",
            "version": 2,
        }

    def _make_matched_response(self, creator_id, match_id, side_a, side_b):
        return {
            "status": "MATCHED",
            "matchData": {
                "category": "live-138518-live:None:Windows:all::1:4:0:G:2",
                "churn": 0,
                "creationDateTime": int(time.time() * 1000),
                "creator": creator_id,
                "customData": {},
                "geolocation": {},
                "matchId": match_id,
                "props": {
                    "countA": 1,
                    "countB": 4,
                    "gameMode": "None",
                    "platform": "Windows",
                },
                "rank": 1,
                "reason": "",
                "schema": 3,
                "sideA": side_a,
                "sideB": side_b,
                "skill": {"rank": 20, "version": 2, "x": 20},
                "status": "CREATED",
                "version": 1,
            },
        }