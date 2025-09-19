import random
import string


class SessionWorker:
    """Класс `SessionWorker` описывает структуру приложения."""


    @staticmethod
    def _gen_friendly_random_string(length: int) -> str:
        """Функция `_gen_friendly_random_string` выполняет прикладную задачу приложения.
        
        Параметры:
            length (int): Параметр `length`.
        
        Возвращает:
            str: Результат выполнения функции.
        """
        chars = string.ascii_letters + string.digits
        return "".join(random.choices(chars, k=length))

    @classmethod
    def gen_bhvr_session(cls, now: int, valid_for: int) -> str:
        """Функция `gen_bhvr_session` выполняет прикладную задачу приложения.
        
        Параметры:
            cls (Any): Класс, к которому привязан метод.
            now (int): Параметр `now`.
            valid_for (int): Параметр `valid_for`.
        
        Возвращает:
            str: Результат выполнения функции.
        """
        return (
            f"{cls._gen_friendly_random_string(22)}."
            f"{cls._gen_friendly_random_string(192)}."
            f"{now * 1000}."
            f"{valid_for * 1000}."
            f"{cls._gen_friendly_random_string(43)}"
        )
