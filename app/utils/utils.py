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
