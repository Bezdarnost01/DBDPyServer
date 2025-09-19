import asyncio
import base64
import json
import logging
import random
import re
import zlib
from pathlib import Path

import httpx
from configs.config import (
    CAP,
    EMBLEM_XP,
    FIRST_MATCH_BONUS,
    XP_PER_UNIT,
    XP_TABLE,
)
from Crypto.Cipher import AES

logger = logging.getLogger(__name__)

KEY = b"5BCC2D6A95D4DF04A005504E59A9B36E"
STEAM_API_KEY = "3DF53DC286EA45499117277D037D87C3"
STEAM_API_URL = "https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/"


class Utils:
    """Класс `Utils` описывает структуру приложения."""

    @staticmethod
    async def _decrypt_dbd(encrypted_bytes: bytes) -> str:
        """Функция `_decrypt_dbd` выполняет прикладную задачу приложения.
        
        Параметры:
            encrypted_bytes (bytes): Параметр `encrypted_bytes`.
        
        Возвращает:
            str: Результат выполнения функции.
        """

        if not encrypted_bytes.startswith(b"DbdDAgAC"):
            msg = "Неверный формат зашифрованной строки."
            raise ValueError(msg)
        encrypted_body = encrypted_bytes[8:]
        encrypted_body = base64.b64decode(encrypted_body)
        cipher = AES.new(KEY, AES.MODE_ECB)
        decrypted_padded = cipher.decrypt(encrypted_body)
        decrypted = decrypted_padded.rstrip(b"\x00")
        decrypted = bytes((b + 1) % 256 for b in decrypted)
        decrypted = decrypted[8:]
        inner_b64_str = decrypted.decode("utf-8", errors="ignore")
        inner_b64_str = re.sub(r"[^A-Za-z0-9+/=]", "", inner_b64_str)
        inner_b64_str = inner_b64_str + "=" * (-len(inner_b64_str) % 4)
        inner_data = base64.b64decode(inner_b64_str)
        inner_data = inner_data[4:]
        plain_data = zlib.decompress(inner_data)

        try:
            json_str = plain_data.decode("utf-16-le")
        except UnicodeDecodeError:
            try:
                json_str = plain_data.decode("utf-8")
            except Exception:
                raise

        start = json_str.find("[")
        end = json_str.rfind("]")
        if start == -1 or end == -1:
            msg = "json array not found"
            raise Exception(msg)
        return json_str[start:end+1]

    @staticmethod
    def token_to_steam_id(token: str) -> str | None:
        """Функция `token_to_steam_id` выполняет прикладную задачу приложения.
        
        Параметры:
            token (str): Параметр `token`.
        
        Возвращает:
            str | None: Результат выполнения функции.
        """
        if not isinstance(token, str) or len(token) < 40:
            return None
        try:
            data = bytes.fromhex(token)
            steam_id_int = int.from_bytes(data[12:20], byteorder="little", signed=False)
            return str(steam_id_int)
        except (ValueError, IndexError):
            return None

    @staticmethod
    def xp_to_player_level(total_xp: int, current_level: int) -> dict[str, int]:
        """Функция `xp_to_player_level` выполняет прикладную задачу приложения.
        
        Параметры:
            total_xp (int): Параметр `total_xp`.
            current_level (int): Параметр `current_level`.
        
        Возвращает:
            dict[str, int]: Результат выполнения функции.
        """
        level_version = 34
        prestige = 0
        level = current_level
        cur_xp = total_xp

        while True:
            xp_needed = XP_TABLE.get(level + 1, 4200)
            if cur_xp >= xp_needed:
                cur_xp -= xp_needed
                level += 1
                if level > 99:
                    prestige += 1
                    level = 1
                    cur_xp = 0
            else:
                break

        return {
            "totalXp": total_xp,
            "levelVersion": level_version,
            "level": level,
            "prestigeLevel": prestige,
            "currentXp": cur_xp,
            "currentXpUpperBound": XP_TABLE.get(level + 1, 4200),
        }

    @staticmethod
    def calc_match_xp(
        match_time: int,
        is_first_match: bool,
        player_type: str,
        consecutive_match: float,
        emblem_qualities: list[str],
    ) -> dict[str, int]:
        """Функция `calc_match_xp` выполняет прикладную задачу приложения.
        
        Параметры:
            match_time (int): Параметр `match_time`.
            is_first_match (bool): Логический флаг.
            player_type (str): Параметр `player_type`.
            consecutive_match (float): Параметр `consecutive_match`.
            emblem_qualities (list[str]): Параметр `emblem_qualities`.
        
        Возвращает:
            dict[str, int]: Результат выполнения функции.
        """
        time_xp_raw = match_time * XP_PER_UNIT
        base_time_xp = min(round(time_xp_raw), CAP)

        emblems_bonus = sum(EMBLEM_XP.get(e, 0) for e in emblem_qualities)

        first_bonus = FIRST_MATCH_BONUS if is_first_match and player_type != "killer" else 0

        m = max(1.0, float(consecutive_match))

        gained = round((base_time_xp + emblems_bonus + first_bonus) * m)

        return {
            "baseMatchXp": base_time_xp,
            "emblemsBonus": emblems_bonus,
            "firstMatchBonus": first_bonus,
            "consecutiveMatchMultiplier": m,
            "totalXpGained": gained,
        }

    @staticmethod
    def process_xp_gain(
        current_xp: int,
        current_level: int,       # 1..99
        current_prestige: int,    # Devotion
        gained_xp: int,
    ) -> dict[str, int]:
        """Функция `process_xp_gain` выполняет прикладную задачу приложения.
        
        Параметры:
            current_xp (int): Параметр `current_xp`.
            current_level (int): Параметр `current_level`.
            current_prestige (int): Параметр `current_prestige`.
            gained_xp (int): Параметр `gained_xp`.
        
        Возвращает:
            dict[str, int]: Результат выполнения функции.
        """
        new_xp = current_xp + gained_xp
        level = current_level
        prestige = current_prestige

        # Защита от кривых входов
        level = max(level, 1)
        level = min(level, 99)

        # Пока хватает XP на ап
        while True:
            # Сколько надо до след. уровня?
            # Если вы храните "XP до след. уровня" как XP_TABLE[level], используйте это.
            # Если наоборот XP_TABLE[level+1], оставьте как ниже — главное, чтобы по всему проекту было единообразно.
            xp_needed = XP_TABLE.get(level + 1)
            if xp_needed is None:
                # нет записи — по умолчанию 4200 (как у вас)
                xp_needed = 4200

            if new_xp >= xp_needed:
                new_xp -= xp_needed
                level += 1
                if level > 99:
                    prestige += 1
                    level = 1
                    new_xp = 0  # в старой системе часто сбрасывали; если нет — уберите это
            else:
                break

        return {
            "currentXp": new_xp,
            "currentXpUpperBound": XP_TABLE.get(level + 1, 4200),
            "level": level,
            "prestigeLevel": prestige,
        }

    @staticmethod
    def calc_rewards(old_level: int, new_level: int, old_prestige: int, new_prestige: int) -> list[dict[str, int]]:
        """Функция `calc_rewards` выполняет прикладную задачу приложения.
        
        Параметры:
            old_level (int): Параметр `old_level`.
            new_level (int): Параметр `new_level`.
            old_prestige (int): Параметр `old_prestige`.
            new_prestige (int): Параметр `new_prestige`.
        
        Возвращает:
            list[dict[str, int]]: Результат выполнения функции.
        """
        rewards = []

        for lvl in range(old_level + 1, new_level + 1):
            rewards.append({"currency": "Shards", "balance": 100})
            if lvl % 10 == 0:
                rewards.append({"currency": "Cells", "balance": 50})

        if new_prestige > old_prestige:
            rewards.append({"currency": "Cells", "balance": 500})
            rewards.append({"currency": "Shards", "balance": 2000})

        return rewards

    @staticmethod
    async def fetch_names_batch(
        steam_ids: list[str],
        *,
        api_key: str | None = None,
        timeout: float = 10.0,
        max_retries: int = 3,
        base_backoff: float = 1.0,
        concurrency: int = 3,
    ) -> dict[str, str]:
        """Функция `fetch_names_batch` выполняет прикладную задачу приложения.
        
        Параметры:
            steam_ids (list[str]): Параметр `steam_ids`.
            api_key (str | None): Параметр `api_key`. Значение по умолчанию: None.
            timeout (float): Параметр `timeout`. Значение по умолчанию: 10.0.
            max_retries (int): Параметр `max_retries`. Значение по умолчанию: 3.
            base_backoff (float): Параметр `base_backoff`. Значение по умолчанию: 1.0.
            concurrency (int): Параметр `concurrency`. Значение по умолчанию: 3.
        
        Возвращает:
            dict[str, str]: Результат выполнения функции.
        """

        api_key = STEAM_API_KEY
        if not steam_ids:
            return {}

        chunks: list[list[str]] = [steam_ids[i:i+100] for i in range(0, len(steam_ids), 100)]
        results: dict[str, str] = {}
        sem = asyncio.Semaphore(max(1, concurrency))

        async def fetch_chunk(client: httpx.AsyncClient, chunk: list[str]) -> dict[str, str]:
            """Функция `fetch_chunk` выполняет прикладную задачу приложения.
            
            Параметры:
                client (httpx.AsyncClient): Параметр `client`.
                chunk (list[str]): Параметр `chunk`.
            
            Возвращает:
                dict[str, str]: Результат выполнения функции.
            """

            nonlocal api_key
            params = {"key": api_key, "steamids": ",".join(chunk)}

            attempt = 0
            while True:
                attempt += 1
                try:
                    async with sem:
                        resp = await client.get(STEAM_API_URL, params=params)
                except httpx.RequestError as e:
                    logger.warning(f"[Steam] сетевой сбой (попытка {attempt}/{max_retries}): {e}")
                    # Повторяем только если есть попытки
                    if attempt <= max_retries:
                        await asyncio.sleep(base_backoff * (2 ** (attempt - 1)) + random.random())
                        continue
                    return {}

                # Обработка статусов
                if resp.status_code == 200:
                    ctype = resp.headers.get("Content-Type", "").lower()
                    text_preview = resp.text[:200] if resp.text else ""
                    if "application/json" not in ctype:
                        logger.error(f"[Steam] неожиданный Content-Type='{ctype}'. Превью: {text_preview!r}")
                        return {}
                    try:
                        data = resp.json()
                        players = data.get("response", {}).get("players", [])
                        return {p.get("steamid", ""): p.get("personaname", "") for p in players if p.get("steamid")}
                    except ValueError:
                        logger.exception(f"[Steam] не удалось распарсить JSON. Превью: {text_preview!r}")
                        return {}
                elif resp.status_code in (429, 500, 502, 503, 504):
                    # Рейт-лимит / временные ошибки — повторяем
                    retry_after_hdr = resp.headers.get("Retry-After")
                    if retry_after_hdr and retry_after_hdr.isdigit():
                        delay = float(retry_after_hdr)
                    else:
                        delay = base_backoff * (2 ** (attempt - 1)) + random.random()
                    logger.warning(f"[Steam] статус {resp.status_code}, повтор через {delay:.2f}s "
                                   f"(попытка {attempt}/{max_retries}). Тело: {resp.text[:200]!r}")
                    if attempt <= max_retries:
                        await asyncio.sleep(delay)
                        continue
                    return {}
                else:
                    # Прочие ошибки — лог и без повторов
                    logger.error(f"[Steam] ошибка {resp.status_code}: {resp.text[:200]!r}")
                    return {}

        async with httpx.AsyncClient(http2=True, timeout=timeout) as client:
            chunk_tasks = [asyncio.create_task(fetch_chunk(client, ch)) for ch in chunks]
            for t in asyncio.as_completed(chunk_tasks):
                try:
                    partial = await t
                except Exception as e:
                    logger.exception(f"[Steam] необработанное исключение при запросе чанка: {e}")
                    partial = {}
                results.update(partial)

        return results

    @staticmethod
    async def get_item_price(character_name: str | None = None, outfit_id: str | None = None, item_id: str | None = None, currency_id: str | None = None, redis=None):
        """Функция `get_item_price` выполняет прикладную задачу приложения.
        
        Параметры:
            character_name (str | None): Параметр `character_name`. Значение по умолчанию: None.
            outfit_id (str | None): Идентификатор outfit. Значение по умолчанию: None.
            item_id (str | None): Идентификатор item. Значение по умолчанию: None.
            currency_id (str | None): Идентификатор currency. Значение по умолчанию: None.
            redis (Any): Подключение к Redis. Значение по умолчанию: None.
        
        Возвращает:
            Any: Результат выполнения функции.
        """

        from dependency.redis import Redis
        bin_path = Path("../assets/cdn/catalog.bin").resolve()
        data = None
        if redis:
            data = await Redis.get_catalog_from_redis(redis)
            if data is None:
                with open(bin_path, "rb") as f:
                    bin_data = f.read()
                json_str = await Utils._decrypt_dbd(bin_data)
                json_str = re.sub(r",(\s*[}\]])", r"\1", json_str)
                data = json.loads(json_str)
                await Redis.update_catalog_in_redis(data, redis)
            elif not isinstance(data, list):
                data = json.loads(data.decode() if isinstance(data, bytes) else data)
        else:
            with open(bin_path, "rb") as f:
                bin_data = f.read()
            json_str = await Utils._decrypt_dbd(bin_data)
            json_str = re.sub(r",(\s*[}\]])", r"\1", json_str)
            data = json.loads(json_str)

        if character_name:
            for item in data:
                if item.get("id") == character_name:
                    for cost in item.get("defaultCost", []):
                        if not currency_id or cost.get("currencyId") == currency_id:
                            return cost.get("price")

        if outfit_id:
            for item in data:
                if item.get("id") == outfit_id:
                    prices = {}
                    for part_id in item.get("metaData", {}).get("items", []):
                        prices[part_id] = await Utils.get_item_price(
                            item_id=part_id,
                            currency_id=currency_id,
                            redis=redis,
                        )
                    return prices if prices else None

        if item_id:
            for item in data:
                if item.get("id") == item_id:
                    for cost in item.get("defaultCost", []):
                        if not currency_id or cost.get("currencyId") == currency_id:
                            return cost.get("price")
                    return None
        return None

    @staticmethod
    def get_balance(wallet: list, currency: str, default=None):
        """Функция `get_balance` выполняет прикладную задачу приложения.
        
        Параметры:
            wallet (list): Параметр `wallet`.
            currency (str): Параметр `currency`.
            default (Any): Параметр `default`. Значение по умолчанию: None.
        
        Возвращает:
            Any: Результат выполнения функции.
        """

        rec = next((w for w in wallet if getattr(w, "currency", None) == currency), None)
        return getattr(rec, "balance", default) if rec else default
