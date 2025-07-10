import random
import string

class SessionWorker:

    @staticmethod
    def _gen_friendly_random_string(length: int) -> str:
        """
        Генерирует случайную строку из латинских букв и цифр.

        Args:
            length (int): Длина строки.

        Returns:
            str: Случайная строка, например 'A8fGh2L9Qz'.
        """
        chars = string.ascii_letters + string.digits
        return ''.join(random.choices(chars, k=length))

    @classmethod
    def gen_bhvr_session(cls, now: int, valid_for: int) -> str:
        """
        Генерирует сессионный ключ формата: <22>.<192>.<timestamp>.<valid_for>.<43>

        Args:
            now (int): Текущее время (обычно timestamp в секундах).
            valid_for (int): Время действия сессии (секунд).

        Returns:
            str: Сессионная строка вида 'part1.part2.part3.part4.part5'
        """
        return (
            f"{cls._gen_friendly_random_string(22)}."
            f"{cls._gen_friendly_random_string(192)}."
            f"{now * 1000}."
            f"{valid_for * 1000}."
            f"{cls._gen_friendly_random_string(43)}"
        )