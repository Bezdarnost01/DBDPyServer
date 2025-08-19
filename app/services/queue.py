import time
import math
import json
from aioredis import Redis
from typing import Literal, Tuple, Optional
import uuid
from .lobby import LobbyManager


class MatchQueue:
    def __init__(self, redis: Redis, side: str, lobby_manager: LobbyManager, avg_match_seconds: int = 10):
        self.redis = redis
        self.side = side.upper()
        self.key = f"queue:{self.side}"
        self.max_survivors = 4
        self.lobby_manager = lobby_manager
        self.avg_match_seconds = max(1, int(avg_match_seconds))  # базовая эвристика

    async def _decode(self, v) -> Optional[str]:
        if v is None:
            return None
        if isinstance(v, bytes):
            return v.decode("utf-8", errors="ignore")
        if isinstance(v, str):
            return v
        return None

    async def _llen(self, side: Literal["A", "B"]) -> int:
        return int(await self.redis.llen(f"queue:{side}"))

    async def _sizes(self) -> Tuple[int, int]:
        size_a = await self._llen("A")
        size_b = await self._llen("B")
        return size_a, size_b

    async def _available_b_slots_in_open_lobbies(self) -> int:
        total = 0
        open_ids = await self.lobby_manager.redis.smembers("lobbies:open")
        for lid_raw in open_ids:
            lid = await self._decode(lid_raw)
            if not lid:
                continue
            lobby = await self.lobby_manager.get_lobby_by_id(lid)
            if not lobby:
                continue
            if lobby.get("isReady", False) and not lobby.get("hasStarted", False):
                nonhosts = lobby.get("nonHosts", []) or []
                free = max(0, self.max_survivors - len(nonhosts))
                total += free
        return total

    async def get_queued_player(self, bhvr_session: str) -> Tuple[Optional[dict], int, Optional[str]]:
        items = await self.redis.lrange(self.key, 0, -1)
        for idx, raw in enumerate(items):
            raw_str = await self._decode(raw)
            if not raw_str:
                continue
            try:
                obj = json.loads(raw_str)
            except Exception:
                continue
            if obj.get("bhvrSession") == bhvr_session:
                return obj, idx, raw_str
        return None, -1, None

    async def add_player(
        self,
        bhvr_session: str,
        user_id: str,
        side: Literal["A", "B"],
        last_checked_for_match: float = None
    ):
        if side != "A" and self.key.endswith("A"):
            raise Exception("Only side A can create lobby")
        if last_checked_for_match is None:
            last_checked_for_match = time.time()
        player, _, _ = await self.get_queued_player(bhvr_session)
        if player:
            return
        data = {
            "bhvrSession": bhvr_session,
            "userId": user_id,
            "side": side,
            "lastCheckedForMatch": last_checked_for_match
        }
        await self.redis.rpush(self.key, json.dumps(data))

    async def remove_player(self, bhvr_session: str) -> bool:
        player, _, raw = await self.get_queued_player(bhvr_session)
        if not player or not raw:
            return False
        await self.redis.lrem(self.key, 1, raw)
        return True

    def _queue_response(self, eta_sec: int, position: int, size_a: int, size_b: int):
        return {
            "queueData": {
                "ETA": eta_sec,       # секунды; -10000 как «неизвестно»
                "position": position, # 1-based
                "sizeA": size_a,
                "sizeB": size_b,
                "stable": False
            },
            "status": "QUEUED"
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
                "props": {"countA": 1, "countB": 4, "gameMode": "None", "platform": "Windows"},
                "rank": 1,
                "reason": "",
                "schema": 3,
                "sideA": side_a,
                "sideB": side_b,
                "skill": {"rank": 20, "version": 2, "x": 20},
                "status": "CREATED",
                "version": 1
            }
        }

    async def _eta_for_B(self, position_1based: int) -> int:
        players_ahead = max(0, position_1based - 1)

        free_now = await self._available_b_slots_in_open_lobbies()
        size_a, size_b = await self._sizes()

        incoming_from_A = size_a * self.max_survivors
        capacity = free_now + incoming_from_A
        capacity = max(1, capacity)

        batches = math.ceil(players_ahead / capacity) if players_ahead > 0 else 0
        eta = batches * self.avg_match_seconds
        return int(eta)

    async def _eta_for_A(self) -> int:
        size_a, size_b = await self._sizes()
        need_b = max(0, self.max_survivors - size_b)
        eta = need_b * self.avg_match_seconds
        return int(eta)

    async def get_queue_status(self, session):
        qp, idx, _raw = await self.get_queued_player(session['bhvrSession'])
        if not qp:
            return {}

        user_id = qp["userId"]
        side = qp["side"]

        if side == "B":
            # чистим свои лобби, если вдруг были
            open_ids = await self.lobby_manager.redis.smembers("lobbies:open")
            to_delete = []
            for lobby_id_raw in open_ids:
                lobby_id = await self._decode(lobby_id_raw)
                if not lobby_id:
                    continue
                lobby = await self.lobby_manager.get_lobby_by_id(lobby_id)
                if not lobby:
                    continue
                host = lobby.get("host", {})
                if host.get("userId") == user_id:
                    to_delete.append(lobby_id)
            for lobby_id in to_delete:
                await self.lobby_manager.delete_match(lobby_id)

            # попытка присоединиться
            open_ids = await self.lobby_manager.redis.smembers("lobbies:open")
            for lobby_id_raw in open_ids:
                lobby_id = await self._decode(lobby_id_raw)
                if not lobby_id:
                    continue
                lobby = await self.lobby_manager.get_lobby_by_id(lobby_id)
                if not lobby:
                    continue

                if any(p.get("userId") == user_id for p in (lobby.get("nonHosts") or [])):
                    continue

                if lobby.get("isReady", False) and not lobby.get("hasStarted", False) and len(lobby.get("nonHosts") or []) < self.max_survivors:
                    lobby.setdefault("nonHosts", []).append(qp)
                    await self.remove_player(qp["bhvrSession"])
                    await self.lobby_manager.redis.set(f"lobby:{lobby['id']}", json.dumps(lobby))
                    return self._make_matched_response(
                        creator_id=lobby["host"]["userId"],
                        match_id=lobby["id"],
                        side_a=[lobby["host"]["userId"]],
                        side_b=[p["userId"] for p in lobby["nonHosts"]],
                    )

            # не смогли присоединиться — остаёмся в очереди с ETA/position
            size_a, size_b = await self._sizes()
            position = idx + 1 if idx >= 0 else 0
            eta = await self._eta_for_B(position)
            return self._queue_response(eta_sec=eta, position=position, size_a=size_a, size_b=size_b)

        # side == "A"
        existing = await self.lobby_manager.find_lobby_by_host_session(qp["bhvrSession"])
        if existing:
            return self._make_matched_response(
                creator_id=existing["host"]["userId"],
                match_id=existing["id"],
                side_a=[existing["host"]["userId"]],
                side_b=[p["userId"] for p in (existing.get("nonHosts") or [])],
            )

        # создаём лобби немедленно при checkOnly
        match_id = str(uuid.uuid4())
        await self.lobby_manager.create_lobby(qp, match_id=match_id)
        await self.remove_player(qp["bhvrSession"])
        return self._make_matched_response(
            creator_id=qp["userId"],
            match_id=match_id,
            side_a=[qp["userId"]],
            side_b=[],
        )

    @staticmethod
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
            "customData": {"SessionSettings": lobby.get("sessionSettings", "")},
            "geolocation": {},
            "matchId": match_id,
            "props": {"countA": 1, "countB": 4, "gameMode": "None", "platform": "Windows"},
            "rank": 1,
            "reason": lobby.get("reason", ""),
            "schema": 3,
            "sideA": [lobby["host"]["userId"]],
            "sideB": [p["userId"] for p in (lobby.get("nonHosts") or [])],
            "skill": {"rank": 20, "version": 2, "x": 20},
            "status": "CLOSED" if killed else "OPENED",
            "version": 2,
        }
