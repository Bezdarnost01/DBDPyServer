import json
import math
import time
import uuid
from typing import Any, Literal

from aioredis import Redis

from .lobby import LobbyManager


class MatchQueue:
    """
    Очередь матчмейкинга:
    - B-игроки заполняют A-лобби в порядке их создания (FIFO по лобби).
    - Позиция игрока в очереди B учитывает уже открытые лобби и их свободные места.
    """

    LUA_JOIN_NONHOST = r"""
    -- KEYS[1] = lobby:{id}
    -- ARGV[1] = player_json
    -- ARGV[2] = max_survivors (int)
    local lobby_key = KEYS[1]
    local player_json = ARGV[1]
    local max_surv = tonumber(ARGV[2])

    local raw = redis.call("GET", lobby_key)
    if not raw then return 0 end

    local lobby = cjson.decode(raw)
    if not lobby then return 0 end

    if not lobby["isReady"] or lobby["hasStarted"] then
        return 0
    end

    if lobby["nonHosts"] == nil then
        lobby["nonHosts"] = {}
    end

    local player = cjson.decode(player_json)
    local uid = player["userId"]

    -- уже есть?
    for _,p in ipairs(lobby["nonHosts"]) do
        if p["userId"] == uid then
            return 2
        end
    end

    if #lobby["nonHosts"] >= max_surv then
        return 0
    end

    table.insert(lobby["nonHosts"], player)
    redis.call("SET", lobby_key, cjson.encode(lobby))
    return 1
    """

    def __init__(
        self,
        redis: Redis,
        side: Literal["A", "B"],
        lobby_manager: LobbyManager,
        avg_match_seconds: int = 10,
        max_survivors: int = 4,
    ) -> None:
        self.redis = redis
        self.side = side.upper()
        self.key = f"queue:{self.side}"  # Redis list
        self.max_survivors = int(max_survivors)
        self.lobby_manager = lobby_manager
        self.avg_match_seconds = max(1, int(avg_match_seconds))

        # Упорядоченное множество открытых лобби по времени создания
        # - множество:       "lobbies:open"    (как и раньше)
        # - сортированное Z: "lobbies:open:z"  (score = creation_ts)
        self.key_open_set = "lobbies:open"
        self.key_open_zset = "lobbies:open:z"


    async def _decode(self, v) -> str | None:
        if v is None:
            return None
        if isinstance(v, bytes):
            return v.decode("utf-8", errors="ignore")
        if isinstance(v, str):
            return v
        return None

    async def _llen(self, side: Literal["A", "B"]) -> int:
        return int(await self.redis.llen(f"queue:{side}"))

    async def _sizes(self) -> tuple[int, int]:
        size_a = await self._llen("A")
        size_b = await self._llen("B")
        return size_a, size_b

    async def _register_open_lobby(self, lobby_id: str, created_ts: float | None = None) -> None:
        """Регистрирует лобби в сетах открытых лобби и в zset (FIFO-порядок по score)."""
        ts = float(created_ts or time.time())
        pipe = self.redis.pipeline()
        pipe.sadd(self.key_open_set, lobby_id)
        pipe.zadd(self.key_open_zset, {lobby_id: ts})
        await pipe.execute()

    async def _unregister_open_lobby(self, lobby_id: str) -> None:
        pipe = self.redis.pipeline()
        pipe.srem(self.key_open_set, lobby_id)
        pipe.zrem(self.key_open_zset, lobby_id)
        await pipe.execute()

    async def _get_open_lobby_ids_fifo(self) -> list[str]:
        """Возвращает список lobby_id в порядке FIFO (по score)."""
        ids = await self.redis.zrange(self.key_open_zset, 0, -1)
        out: list[str] = []
        for raw in ids:
            s = await self._decode(raw)
            if s:
                out.append(s)
        return out

    async def _get_open_lobbies_fifo(self) -> list[dict[str, Any]]:
        """Возвращает список лобби (JSON) в FIFO-порядке. Фильтрует мёртвые."""
        out: list[dict[str, Any]] = []
        for lid in await self._get_open_lobby_ids_fifo():
            lobby = await self.lobby_manager.get_lobby_by_id(lid)
            if not lobby:
                # подчистим мусор
                await self._unregister_open_lobby(lid)
                continue
            if lobby.get("isReady", False) and not lobby.get("hasStarted", False):
                out.append(lobby)
        return out

    async def _available_b_slots_fifo(self) -> int:
        """Считает суммарное кол-во свободных слотов B во всех открытых лобби (FIFO)."""
        total = 0
        for lobby in await self._get_open_lobbies_fifo():
            nonhosts = lobby.get("nonHosts") or []
            free = max(0, self.max_survivors - len(nonhosts))
            total += free
        return total


    async def get_queued_player(self, bhvr_session: str) -> tuple[dict | None, int, str | None]:
        """Ищет игрока в своей очереди по bhvr_session. Возвращает (obj, idx, raw_json)."""
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
        last_checked_for_match: float | None = None,
    ) -> None:
        """
        Добавляет игрока в очередь соответствующей стороны.
        Для стороны A: игрок не должен добавляться в очередь B-очереди-экземпляра и наоборот.
        """
        side = side.upper()
        if side != self.side:
            msg = f"MatchQueue(side={self.side}) cannot accept player of side={side}"
            raise Exception(msg)
        if last_checked_for_match is None:
            last_checked_for_match = time.time()

        player, _, _ = await self.get_queued_player(bhvr_session)
        if player:
            return  # уже в очереди

        data = {
            "bhvrSession": bhvr_session,
            "userId": user_id,
            "side": side,
            "lastCheckedForMatch": last_checked_for_match,
        }
        await self.redis.rpush(self.key, json.dumps(data))

    async def remove_player(self, bhvr_session: str) -> bool:
        player, _, raw = await self.get_queued_player(bhvr_session)
        if not player or not raw:
            return False
        await self.redis.lrem(self.key, 1, raw)
        return True


    def _queue_response(self, eta_sec: int, position: int, size_a: int, size_b: int):
        # position — 1-based, реальная с учётом свободных мест в открытых лобби
        return {
            "queueData": {
                "ETA": eta_sec,        # сек; -10000 если "неизвестно"
                "position": position,  # 1-based
                "sizeA": size_a,
                "sizeB": size_b,
                "stable": True,
            },
            "status": "QUEUED",
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
                "props": {"countA": 1, "countB": self.max_survivors, "gameMode": "None", "platform": "Windows"},
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


    async def _real_position_for_B(self, index_0based: int) -> int:
        """
        Реальная 1-based позиция B-игрока в очереди с учётом свободных мест в уже открытых лобби.
        Пример: 1 лобби (3/4) → свободно 1; в очереди 5 игроков.
            i=0 → матчится (вы это увидите через MATCHED), у остальных позиции 1..4.
            Формула: max(1, i - free_slots_total + 1).
        """
        free_total = await self._available_b_slots_fifo()
        return max(1, index_0based - free_total + 1)

    async def _eta_for_B(self, position_1based: int) -> int:
        """
        Примерная оценка ETA: количество «волн» по avg_match_seconds.
        В одной «волне» мы заполняем: свободные места в открытых лобби + будущие лобби от A (size_a * max_survivors).
        """
        size_a, size_b = await self._sizes()
        free_now = await self._available_b_slots_fifo()
        capacity = free_now + size_a * self.max_survivors
        capacity = max(1, capacity)
        players_ahead = max(0, position_1based - 1)
        batches = math.ceil(players_ahead / capacity) if players_ahead > 0 else 0
        return int(batches * self.avg_match_seconds)

    async def _eta_for_A(self) -> int:
        """Примерная оценка ETA для A: сколько B нужно добрать до полного лобби."""
        size_a, size_b = await self._sizes()
        # Сколько уже в открытых лобби людей B (сумма nonHosts) нас не интересует для ETA А,
        # здесь грубо считаем, что нужно self.max_survivors B, и их даст очередь B.
        need_b = max(0, self.max_survivors - size_b)
        return int(need_b * self.avg_match_seconds)

    async def get_stats(self) -> dict[str, int]:
        """
        Возвращает статистику:
         - openLobbies: кол-во открытых лобби (готовых и не начатых)
         - queueA: длина очереди A
         - queueB: длина очереди B
         - queuedTotal: суммарная очередь.
        """
        open_lobbies = len(await self._get_open_lobbies_fifo())
        size_a, size_b = await self._sizes()
        queue_len = size_a if self.side == "A" else size_b
        return {
            "openLobbies": open_lobbies,
            "queue": queue_len,
        }

    async def get_queue_status(self, session: dict[str, Any]):
        """
        Основной метод для клиента.
        - Если игрок сматчен → MATCHED + данные матча.
        - Иначе → статус QUEUED + реальная позиция и ETA.
        """
        qp, idx, _raw = await self.get_queued_player(session["bhvrSession"])
        if not qp:
            return {}

        user_id = qp["userId"]
        side = qp["side"]

        if side == "B":
            # Попытка присоединиться к самому старому открытому лобби (FIFO), атомарно.
            for lobby in await self._get_open_lobbies_fifo():
                lobby_id = lobby["id"]

                # уже внутри?
                if any(p.get("userId") == user_id for p in (lobby.get("nonHosts") or [])):
                    # на всякий случай очищаем очередь
                    await self.remove_player(qp["bhvrSession"])
                    return self._make_matched_response(
                        creator_id=lobby["host"]["userId"],
                        match_id=lobby_id,
                        side_a=[lobby["host"]["userId"]],
                        side_b=[p["userId"] for p in (lobby.get("nonHosts") or [])],
                    )

                # атомарная попытка присоединиться
                added = await self.redis.eval(
                    self.LUA_JOIN_NONHOST,
                    keys=[f"lobby:{lobby_id}"],
                    args=[json.dumps(qp), str(self.max_survivors)],
                )
                if int(added) == 1:
                    # успешно → удалить из очереди и вернуть MATCHED
                    await self.remove_player(qp["bhvrSession"])

                    # перечитать лобби для ответа (не обязательно, но красиво)
                    updated = await self.lobby_manager.get_lobby_by_id(lobby_id)
                    side_b = [p["userId"] for p in (updated.get("nonHosts") or [])] if updated else \
                             [p["userId"] for p in (lobby.get("nonHosts") or [])]

                    return self._make_matched_response(
                        creator_id=lobby["host"]["userId"],
                        match_id=lobby_id,
                        side_a=[lobby["host"]["userId"]],
                        side_b=side_b,
                    )
                # added == 0 → либо лобби уже заполнено/закрыто, пробуем следующее
                # added == 2 → уже внутри, обработано выше

            # Не смогли присоединиться — остаёмся в очереди
            size_a, size_b = await self._sizes()
            position_real = await self._real_position_for_B(idx)  # 1-based
            eta = await self._eta_for_B(position_real)
            return self._queue_response(eta_sec=eta, position=position_real, size_a=size_a, size_b=size_b)

        # side == "A"
        # Если у хоста уже есть лобби — вернём его
        existing = await self.lobby_manager.find_lobby_by_host_session(qp["bhvrSession"])
        if existing:
            # убедимся, что оно зарегистрировано в FIFO-наборе
            await self._register_open_lobby(existing["id"], created_ts=existing.get("createdAtTs", time.time()))
            return self._make_matched_response(
                creator_id=existing["host"]["userId"],
                match_id=existing["id"],
                side_a=[existing["host"]["userId"]],
                side_b=[p["userId"] for p in (existing.get("nonHosts") or [])],
            )

        # Создаём лобби немедленно: A всегда создаёт при первом запросе статуса
        match_id = str(uuid.uuid4())
        new_lobby = await self.lobby_manager.create_lobby(qp, match_id=match_id)
        # ожидаем, что create_lobby вернёт структуру лобби или хотя бы выставит ключ "lobby:{id}"
        created_ts = float(new_lobby.get("createdAtTs", time.time())) if isinstance(new_lobby, dict) else time.time()
        await self._register_open_lobby(match_id, created_ts)

        # удаляем A из очереди — он «занят» хостингом
        await self.remove_player(qp["bhvrSession"])

        return self._make_matched_response(
            creator_id=qp["userId"],
            match_id=match_id,
            side_a=[qp["userId"]],
            side_b=[],
        )

    @staticmethod
    async def create_match_response(lobby_manager: LobbyManager, match_id: str, killed: bool = False):
        """Возвращает снэпшот матча по match_id."""
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
