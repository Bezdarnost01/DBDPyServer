import httpx
import os
import re
import base64
import zlib
import struct
import json
import asyncio
from Crypto.Cipher import AES
from pathlib import Path
from typing import Optional, List
from typing import List, Dict
from configs.config import XP_TABLE
import logging
logger = logging.getLogger(__name__) 

KEY = b'5BCC2D6A95D4DF04A005504E59A9B36E'
STEAM_API_KEY = '3DF53DC286EA45499117277D037D87C3'
STEAM_API_URL = "https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/"


class Utils:
    @staticmethod
    async def _decrypt_dbd(encrypted_bytes: bytes) -> str:
        if not encrypted_bytes.startswith(b"DbdDAgAC"):
            raise ValueError("Неверный формат зашифрованной строки.")
        encrypted_body = encrypted_bytes[8:]
        encrypted_body = base64.b64decode(encrypted_body)
        cipher = AES.new(KEY, AES.MODE_ECB)
        decrypted_padded = cipher.decrypt(encrypted_body)
        decrypted = decrypted_padded.rstrip(b'\x00')
        decrypted = bytes((b + 1) % 256 for b in decrypted)
        decrypted = decrypted[8:]
        inner_b64_str = decrypted.decode('utf-8', errors='ignore')
        inner_b64_str = re.sub(r'[^A-Za-z0-9+/=]', '', inner_b64_str)
        inner_b64_str = inner_b64_str + '=' * (-len(inner_b64_str) % 4)
        inner_data = base64.b64decode(inner_b64_str)
        inner_data = inner_data[4:]
        plain_data = zlib.decompress(inner_data)
        
        try:
            json_str = plain_data.decode("utf-16-le")
        except UnicodeDecodeError:
            try:
                json_str = plain_data.decode("utf-8")
            except Exception as e:
                print("Can't decode as utf-16-le or utf-8:", e)
                raise

        start = json_str.find("[")
        end = json_str.rfind("]")
        if start == -1 or end == -1:
            print("Не удалось найти массив json")
            print(repr(json_str[:500]))
            print(repr(json_str[-500:]))
            raise Exception("json array not found")
        json_str = json_str[start:end+1]
        return json_str

    @staticmethod
    def token_to_steam_id(token: str) -> Optional[str]:
        """
        Преобразует токен (hex-строку) в steam_id.

        Args:
            token (str): Токен в hex-формате.

        Returns:
            Optional[str]: Строковое представление steam_id, либо None если ошибка.
        """
        if not isinstance(token, str) or len(token) < 40:
            return None
        try:
            data = bytes.fromhex(token)
            steam_id_int = int.from_bytes(data[12:20], byteorder='little', signed=False)
            return str(steam_id_int)
        except (ValueError, IndexError):
            return None
    
    @staticmethod
    def xp_to_player_level(xp: int):
        level_version = 34
        prestige_level = 0
        level = min(xp // 2100 + 1, 100)
        current_xp = xp % 2100
        current_xp_upper_bound = 2100
        return {
            "totalXp": xp,
            "levelVersion": level_version,
            "level": level,
            "prestigeLevel": prestige_level,
            "currentXp": current_xp,
            "currentXpUpperBound": current_xp_upper_bound
        }
    
    @staticmethod
    def calc_match_xp(match_time: int, is_first_match: bool, consecutive_match: int, emblem_qualities: List[str]) -> Dict[str, int]:
        """
        Рассчитывает опыт, полученный за матч.

        Аргументы:
            match_time (int): время матча в секундах или минутах (зависит от твоей логики).
            is_first_match (bool): является ли это первый матч игрока в сессии (даёт бонус).
            consecutive_match (int): множитель за серию матчей (например: 1, 1.1, 1.2 ...).
            emblem_qualities (List[str]): список эмблем игрока, возможные значения:
                "None", "Bronze", "Silver", "Gold", "Iridescent".

        Возвращает:
            dict:
                {
                    "baseMatchXp": int,                # XP за время матча
                    "emblemsBonus": int,               # XP за эмблемы
                    "firstMatchBonus": int,            # XP за первый матч
                    "consecutiveMatchMultiplier": int, # множитель серии матчей
                    "totalXpGained": int               # итоговый XP за матч
                }
        """
        time_xp = match_time * 10

        emblem_values = {
            "None": 0,
            "Bronze": 100,
            "Silver": 200,
            "Gold": 400,
            "Iridescent": 600
        }
        emblem_xp = sum(emblem_values.get(e, 0) for e in emblem_qualities)

        first_match_bonus = 300 if is_first_match else 0

        base_xp = time_xp + emblem_xp + first_match_bonus
        gained_xp = int(base_xp * consecutive_match)

        return {
            "baseMatchXp": time_xp,
            "emblemsBonus": emblem_xp,
            "firstMatchBonus": first_match_bonus,
            "consecutiveMatchMultiplier": consecutive_match,
            "totalXpGained": gained_xp
        }
    
    @staticmethod
    def process_xp_gain(current_xp: int, current_level: int, current_prestige: int, gained_xp: int) -> Dict[str, int]:
        """
        Пересчитывает текущий опыт, уровень и престиж игрока с учётом полученного XP.

        Аргументы:
            current_xp (int): текущий XP игрока на его уровне.
            current_level (int): текущий уровень игрока (1–99).
            current_prestige (int): текущий престиж игрока.
            gained_xp (int): XP, полученный за матч.
            xp_table (dict): таблица {уровень: XP до следующего уровня}.

        Возвращает:
            dict:
                {
                    "currentXp": int,           # XP после пересчёта
                    "currentXpUpperBound": int, # XP, требуемый до следующего уровня
                    "level": int,               # новый уровень
                    "prestigeLevel": int        # новый престиж
                }
        """
        new_xp = current_xp + gained_xp
        new_level = current_level
        new_prestige = current_prestige

        while True:
            xp_needed = XP_TABLE.get(new_level + 1, 4200)
            if new_xp >= xp_needed:
                new_xp -= xp_needed
                new_level += 1
                if new_level > 99:
                    new_prestige += 1
                    new_level = 1
                    new_xp = 0
            else:
                break

        return {
            "currentXp": new_xp,
            "currentXpUpperBound": XP_TABLE.get(new_level + 1, 4200),
            "level": new_level,
            "prestigeLevel": new_prestige
        }

    @staticmethod
    def calc_rewards(old_level: int, new_level: int, old_prestige: int, new_prestige: int) -> List[Dict[str, int]]:
        """
        Рассчитывает награды игроку за повышение уровня или престижа.

        Аргументы:
            old_level (int): уровень до матча.
            new_level (int): уровень после матча.
            old_prestige (int): престиж до матча.
            new_prestige (int): престиж после матча.

        Возвращает:
            List[dict]: список наград в формате:
                [
                    {"currency": "Shards", "balance": 100},
                    {"currency": "Cells", "balance": 50},
                ]

        Правила (можешь менять под себя):
            - Каждый новый уровень → +100 Shards
            - Каждый 10-й уровень → дополнительно +50 Cells
            - Каждый новый престиж → +500 Cells и +2000 Shards
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
        steam_ids: List[str],
        *,
        api_key: Optional[str] = None,
        timeout: float = 10.0,
        max_retries: int = 3,
        base_backoff: float = 1.0,
        concurrency: int = 3,
    ) -> Dict[str, str]:
        api_key = STEAM_API_KEY
        if not steam_ids:
            return {}

        chunks: List[List[str]] = [steam_ids[i:i+100] for i in range(0, len(steam_ids), 100)]
        results: Dict[str, str] = {}
        sem = asyncio.Semaphore(max(1, concurrency))

        async def fetch_chunk(client: httpx.AsyncClient, chunk: List[str]) -> Dict[str, str]:
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
                        logger.error(f"[Steam] не удалось распарсить JSON. Превью: {text_preview!r}")
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
    async def get_item_price(character_name: str = None, outfit_id: str = None, item_id: str = None, currency_id: str = None, redis=None):
        from dependency.redis import Redis
        bin_path = Path("../assets/cdn/catalog.bin").resolve()
        data = None
        if redis:
            data = await Redis.get_catalog_from_redis(redis)
            if data is None:
                with open(bin_path, "rb") as f:
                    bin_data = f.read()
                json_str = await Utils._decrypt_dbd(bin_data)
                json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)
                data = json.loads(json_str)
                await Redis.update_catalog_in_redis(data, redis)
            else:
                if not isinstance(data, list):
                    data = json.loads(data.decode() if isinstance(data, bytes) else data)
        else:
            with open(bin_path, "rb") as f:
                bin_data = f.read()
            json_str = await Utils._decrypt_dbd(bin_data)
            json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)
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
                            redis=redis
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
        rec = next((w for w in wallet if getattr(w, "currency", None) == currency), None)
        return getattr(rec, "balance", default) if rec else default