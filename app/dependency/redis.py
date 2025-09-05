import json
from fastapi import Request
from crud.users import UserManager
from utils.utils import Utils

class Redis:
    @staticmethod
    async def get_redis(request: Request):
        return request.app.state.redis

    @staticmethod
    async def update_catalog_in_redis(json_data, redis):
        """
        Кладёт сериализованный JSON-каталог в Redis по ключу 'catalog:json'.
        """
        # json_data — это уже python-список (list[dict])
        await redis.set("catalog:json", json.dumps(json_data))

    @staticmethod
    async def get_catalog_from_redis(redis):
        """
        Получает декодированный JSON-каталог из Redis.
        """
        raw = await redis.get("catalog:json")
        if not raw:
            return None
        if isinstance(raw, bytes):
            raw = raw.decode()
        return json.loads(raw)

    @staticmethod
    async def get_cloud_ids(redis, steam_ids, db_users):
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
        cache_key = f"friendslist:{user_id}:{hash(tuple(sorted(ids)))}"
        cached = await redis.get(cache_key)
        if cached:
            return json.loads(cached)
        return None

    @staticmethod
    async def set_friends_list(redis, user_id, ids, friends_list, ttl=15):
        cache_key = f"friendslist:{user_id}:{hash(tuple(sorted(ids)))}"
        await redis.set(cache_key, json.dumps(friends_list), ex=ttl)

    @staticmethod
    async def set_friend_ids(redis, user_id, steam_ids, ttl=60):
        """
        Кэширует список steam_id друзей для user_id.
        """
        cache_key = f"friendsids:{user_id}"
        await redis.set(cache_key, json.dumps(steam_ids), ex=ttl)

    @staticmethod
    async def get_friend_ids(redis, user_id):
        """
        Пробует получить список steam_id друзей пользователя user_id из кэша.
        Если нет в кэше — возвращает None.
        """
        cache_key = f"friendsids:{user_id}"
        cached = await redis.get(cache_key)
        if cached:
            return json.loads(cached)
        return None