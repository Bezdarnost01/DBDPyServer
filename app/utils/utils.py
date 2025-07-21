import httpx
import os
import re
import base64
import zlib
import struct
import json
from Crypto.Cipher import AES
from pathlib import Path
from typing import Optional, List
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
    async def fetch_names_batch(steam_ids: List[str]) -> dict:
        async with httpx.AsyncClient() as client:
            ids_str = ','.join(steam_ids)
            params = {
                'key': STEAM_API_KEY,
                'steamids': ids_str
            }
            resp = await client.get(STEAM_API_URL, params=params)
            data = resp.json()
            return {p['steamid']: p['personaname'] for p in data['response']['players']}
        
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