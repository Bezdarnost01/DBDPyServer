import json

from crud.users import UserManager
from fastapi import Request
from utils.utils import Utils


class Redis:
    """Класс `Redis` описывает структуру приложения."""

    @staticmethod
    async def get_redis(request: Request):
        """Функция `get_redis` выполняет прикладную задачу приложения.
        
        Параметры:
            request (Request): Входящий HTTP-запрос.
        
        Возвращает:
            Any: Результат выполнения функции.
        """

        return request.app.state.redis

    @staticmethod
    async def update_catalog_in_redis(json_data, redis) -> None:
        """Функция `update_catalog_in_redis` выполняет прикладную задачу приложения.
        
        Параметры:
            json_data (Any): Структура данных.
            redis (Any): Подключение к Redis.
        
        Возвращает:
            None: Функция не возвращает значение.
        """
        # json_data — это уже python-список (list[dict])
        await redis.set("catalog:json", json.dumps(json_data))

    @staticmethod
    async def get_catalog_from_redis(redis):
        """Функция `get_catalog_from_redis` выполняет прикладную задачу приложения.
        
        Параметры:
            redis (Any): Подключение к Redis.
        
        Возвращает:
            Any: Результат выполнения функции.
        """
        raw = await redis.get("catalog:json")
        if not raw:
            return None
        if isinstance(raw, bytes):
            raw = raw.decode()
        return json.loads(raw)

    @staticmethod
    async def get_cloud_ids(redis, steam_ids, db_users):
        """Функция `get_cloud_ids` выполняет прикладную задачу приложения.
        
        Параметры:
            redis (Any): Подключение к Redis.
            steam_ids (Any): Параметр `steam_ids`.
            db_users (Any): Подключение к базе данных.
        
        Возвращает:
            Any: Результат выполнения функции.
        """

        result = {}
        missed = []
        for sid in steam_ids:
            cache_key = f"cloudid:{sid}"
            cached = await redis.get(cache_key)
            if cached:
                result[str(sid)] = cached
            else:
                missed.append(sid)
        if missed:
            db_result = await UserManager.get_user_ids_by_steam_ids(db_users, missed)
            for sid in missed:
                cloud_id = db_result.get(str(sid))
                if cloud_id:
                    await redis.set(f"cloudid:{sid}", cloud_id, ex=3600)
                    result[str(sid)] = cloud_id
        return result

    @staticmethod
    async def get_steam_names(redis, steam_ids):
        """Функция `get_steam_names` выполняет прикладную задачу приложения.
        
        Параметры:
            redis (Any): Подключение к Redis.
            steam_ids (Any): Параметр `steam_ids`.
        
        Возвращает:
            Any: Результат выполнения функции.
        """

        result = {}
        missed = []
        for sid in steam_ids:
            cache_key = f"steamname:{sid}"
            cached = await redis.get(cache_key)
            if cached:
                result[str(sid)] = cached
            else:
                missed.append(sid)
        if missed:
            names = await Utils.fetch_names_batch(missed)
            for sid in missed:
                name = names.get(sid)
                if name:
                    await redis.set(f"steamname:{sid}", name, ex=3600)
                    result[str(sid)] = name
        return result

    @staticmethod
    async def get_friends_list(redis, user_id, ids):
        """Функция `get_friends_list` выполняет прикладную задачу приложения.
        
        Параметры:
            redis (Any): Подключение к Redis.
            user_id (Any): Идентификатор пользователя.
            ids (Any): Параметр `ids`.
        
        Возвращает:
            Any: Результат выполнения функции.
        """

        cache_key = f"friendslist:{user_id}:{hash(tuple(sorted(ids)))}"
        cached = await redis.get(cache_key)
        if cached:
            return json.loads(cached)
        return None

    @staticmethod
    async def set_friends_list(redis, user_id, ids, friends_list, ttl=15) -> None:
        """Функция `set_friends_list` выполняет прикладную задачу приложения.
        
        Параметры:
            redis (Any): Подключение к Redis.
            user_id (Any): Идентификатор пользователя.
            ids (Any): Параметр `ids`.
            friends_list (Any): Параметр `friends_list`.
            ttl (Any): Параметр `ttl`. Значение по умолчанию: 15.
        
        Возвращает:
            None: Функция не возвращает значение.
        """

        cache_key = f"friendslist:{user_id}:{hash(tuple(sorted(ids)))}"
        await redis.set(cache_key, json.dumps(friends_list), ex=ttl)

    @staticmethod
    async def set_friend_ids(redis, user_id, steam_ids, ttl=60) -> None:
        """Функция `set_friend_ids` выполняет прикладную задачу приложения.
        
        Параметры:
            redis (Any): Подключение к Redis.
            user_id (Any): Идентификатор пользователя.
            steam_ids (Any): Параметр `steam_ids`.
            ttl (Any): Параметр `ttl`. Значение по умолчанию: 60.
        
        Возвращает:
            None: Функция не возвращает значение.
        """
        cache_key = f"friendsids:{user_id}"
        await redis.set(cache_key, json.dumps(steam_ids), ex=ttl)

    @staticmethod
    async def get_friend_ids(redis, user_id):
        """Функция `get_friend_ids` выполняет прикладную задачу приложения.
        
        Параметры:
            redis (Any): Подключение к Redis.
            user_id (Any): Идентификатор пользователя.
        
        Возвращает:
            Any: Результат выполнения функции.
        """
        cache_key = f"friendsids:{user_id}"
        cached = await redis.get(cache_key)
        if cached:
            return json.loads(cached)
        return None
