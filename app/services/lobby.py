import json
import time
import uuid

from aioredis import Redis


class LobbyManager:
    """Класс `LobbyManager` описывает структуру приложения."""

    def __init__(self, redis: Redis) -> None:
        """Функция `__init__` выполняет прикладную задачу приложения.
        
        Параметры:
            self (Any): Текущий экземпляр класса.
            redis (Redis): Подключение к Redis.
        
        Возвращает:
            None: Функция не возвращает значение.
        """

        self.redis = redis

    async def get_lobby_by_id(self, id: int):
        """Функция `get_lobby_by_id` выполняет прикладную задачу приложения.
        
        Параметры:
            self (Any): Текущий экземпляр класса.
            id (int): Идентификатор объекта.
        
        Возвращает:
            Any: Результат выполнения функции.
        """

        lobby_json = await self.redis.get(f"lobby:{id}")
        if not lobby_json:
            return None
        return json.loads(lobby_json)


    async def get_killed_lobby_by_id(self, lobby_id: str):
        """Функция `get_killed_lobby_by_id` выполняет прикладную задачу приложения.
        
        Параметры:
            self (Any): Текущий экземпляр класса.
            lobby_id (str): Идентификатор лобби.
        
        Возвращает:
            Any: Результат выполнения функции.
        """

        lobby_json = await self.redis.get(f"killed_lobby:{lobby_id}")
        if not lobby_json:
            return None
        return json.loads(lobby_json)

    async def create_lobby(self, host: dict, match_id: str | None = None) -> str:
        """Функция `create_lobby` выполняет прикладную задачу приложения.
        
        Параметры:
            self (Any): Текущий экземпляр класса.
            host (dict): Параметр `host`.
            match_id (str | None): Идентификатор матча. Значение по умолчанию: None.
        
        Возвращает:
            str: Результат выполнения функции.
        """

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
            "hasStarted": False,
        }
        await self.redis.set(lobby_key, json.dumps(lobby))
        await self.redis.sadd("lobbies:open", match_id)
        return match_id

    async def register_match(self, match_id: str, session_settings: dict):
        """Функция `register_match` выполняет прикладную задачу приложения.
        
        Параметры:
            self (Any): Текущий экземпляр класса.
            match_id (str): Идентификатор матча.
            session_settings (dict): Объект сессии.
        
        Возвращает:
            Any: Результат выполнения функции.
        """

        lobby_json = await self.redis.get(f"lobby:{match_id}")
        if not lobby_json:
            return None

        lobby = json.loads(lobby_json)
        lobby["isReady"] = True
        lobby["sessionSettings"] = session_settings

        await self.redis.set(f"lobby:{match_id}", json.dumps(lobby))
        return lobby

    async def delete_match(self, match_id: str) -> None:
        """Функция `delete_match` выполняет прикладную задачу приложения.
        
        Параметры:
            self (Any): Текущий экземпляр класса.
            match_id (str): Идентификатор матча.
        
        Возвращает:
            None: Функция не возвращает значение.
        """

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
        """Функция `is_owner` выполняет прикладную задачу приложения.
        
        Параметры:
            self (Any): Текущий экземпляр класса.
            match_id (str): Идентификатор матча.
            bhvr_session (str): Объект сессии.
        
        Возвращает:
            bool: Результат выполнения функции.
        """

        lobby_json = await self.redis.get(f"lobby:{match_id}")
        if not lobby_json:
            return False
        lobby = json.loads(lobby_json)
        return lobby["host"]["bhvrSession"] == bhvr_session

    async def delete_old_matches(self, minutes: int = 5) -> None:
        """Функция `delete_old_matches` выполняет прикладную задачу приложения.
        
        Параметры:
            self (Any): Текущий экземпляр класса.
            minutes (int): Параметр `minutes`. Значение по умолчанию: 5.
        
        Возвращает:
            None: Функция не возвращает значение.
        """

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
        """Функция `remove_player_from_lobby` выполняет прикладную задачу приложения.
        
        Параметры:
            self (Any): Текущий экземпляр класса.
            match_id (str): Идентификатор матча.
            bhvr_session (str): Объект сессии.
        
        Возвращает:
            bool: Результат выполнения функции.
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
        """Функция `find_lobby_by_host_session` выполняет прикладную задачу приложения.
        
        Параметры:
            self (Any): Текущий экземпляр класса.
            bhvr_session (str): Объект сессии.
        
        Возвращает:
            Any: Результат выполнения функции.
        """

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
