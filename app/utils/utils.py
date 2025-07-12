from typing import Optional

class Utils:
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