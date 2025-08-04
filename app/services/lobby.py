import uuid
import json
from typing import Optional, List
from aioredis import Redis
import time

class LobbyManager:
    """
    Менеджер игровых лобби в Redis.
    Хранит каждое лобби как ключ 'lobby:{id}' (JSON),
    а список всех лобби — как SET 'lobbies:open'.
    """
    def __init__(self, redis: Redis):
        self.redis = redis

    async def get_lobby_by_id(self, id: int):
        lobby_json = await self.redis.get(f"lobby:{id}")
        if not lobby_json:
            return None
        lobby = json.loads(lobby_json)

        return lobby

    async def get_killed_lobby_by_id(self, lobby_id: str):
        lobby_json = await self.redis.get(f"killed_lobby:{lobby_id}")
        if not lobby_json:
            return None
        return json.loads(lobby_json)

    async def create_lobby(self, host: dict, match_id: str = None) -> str:
        if not match_id:
            match_id = str(uuid.uuid4())
        lobby_key = f"lobby:{match_id}"

        open_ids = await self.redis.smembers("lobbies:open")
        for lobby_id in open_ids:
            lobby_json = await self.redis.get(f"lobby:{lobby_id}")
            if not lobby_json:
                continue
            lobby = json.loads(lobby_json)
            if lobby["host"]["bhvrSession"] == host["bhvrSession"]:
                await self.delete_match(lobby_id)

        exists = await self.redis.exists(lobby_key)
        if exists:
            return match_id

        lobby = {
            "id": match_id,
            "host": host,
            "nonHosts": [],
            "isReady": False,
            "isPrepared": False,
            "hasStarted": False
        }
        await self.redis.set(lobby_key, json.dumps(lobby))
        await self.redis.sadd("lobbies:open", match_id)
        return match_id
    
    async def register_match(self, match_id: str, session_settings: dict):
        lobby_json = await self.redis.get(f"lobby:{match_id}")
        if not lobby_json:
            return None

        lobby = json.loads(lobby_json)
        lobby["isReady"] = True
        lobby["sessionSettings"] = session_settings

        await self.redis.set(f"lobby:{match_id}", json.dumps(lobby))
        return lobby 
    
    async def delete_match(self, match_id: str):
        lobby_json = await self.redis.get(f"lobby:{match_id}")
        if not lobby_json:
            return
        lobby = json.loads(lobby_json)
        await self.redis.srem("lobbies:open", match_id)
        await self.redis.delete(f"lobby:{match_id}")

        lobby["killedTime"] = int(time.time() * 1000)
        await self.redis.set(f"killed_lobby:{match_id}", json.dumps(lobby))
        await self.redis.sadd("lobbies:killed", match_id)

    async def is_owner(self, match_id: str, bhvr_session: str) -> bool:
        lobby_json = await self.redis.get(f"lobby:{match_id}")
        if not lobby_json:
            return False
        lobby = json.loads(lobby_json)
        return lobby["host"]["bhvrSession"] == bhvr_session
    
    async def delete_old_matches(self, minutes: int = 5):
        cutoff = int(time.time() * 1000) - minutes * 60 * 1000
        killed_ids = await self.redis.smembers("lobbies:killed")
        for lobby_id in killed_ids:
            lobby_json = await self.redis.get(f"killed_lobby:{lobby_id}")
            if not lobby_json:
                continue
            lobby = json.loads(lobby_json)
            if lobby.get("killedTime", 0) < cutoff:
                await self.redis.delete(f"killed_lobby:{lobby_id}")
                await self.redis.srem("lobbies:killed", lobby_id)

    async def remove_player_from_lobby(self, match_id: str, bhvr_session: str) -> bool:
        """
        Удаляет игрока из nonHosts по bhvr_session.
        Возвращает True если игрок был удалён, иначе False.
        """
        lobby_json = await self.redis.get(f"lobby:{match_id}")
        if not lobby_json:
            return False

        lobby = json.loads(lobby_json)
        before_count = len(lobby.get("nonHosts", []))

        lobby["nonHosts"] = [
            player for player in lobby.get("nonHosts", [])
            if player.get("bhvrSession") != bhvr_session
        ]
        after_count = len(lobby["nonHosts"])

        if after_count == before_count:
            return False

        await self.redis.set(f"lobby:{match_id}", json.dumps(lobby))
        return True

    async def find_lobby_by_host_session(self, bhvr_session: str):
        open_ids = await self.redis.smembers("lobbies:open")
        for lobby_id in open_ids:
            lobby_json = await self.redis.get(f"lobby:{lobby_id}")
            if not lobby_json:
                continue
            lobby = json.loads(lobby_json)
            host = lobby.get("host", {})
            bhvr = host.get("bhvrSession")
            if bhvr is None:
                continue
            if bhvr == bhvr_session and not lobby.get("hasStarted", False):
                return lobby
        return None