from datetime import datetime

import pytz
from fastapi import WebSocket
from models.websocket import WebsocketSession
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

MOSCOW = pytz.timezone("Europe/Moscow")

class WSManager:
    """Класс `WSManager` описывает структуру приложения."""

    def __init__(self) -> None:
        """Функция `__init__` выполняет прикладную задачу приложения.
        
        Параметры:
            self (Any): Текущий экземпляр класса.
        
        Возвращает:
            None: Функция не возвращает значение.
        """

        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, user_id: str, websocket: WebSocket, db: AsyncSession) -> None:
        """Функция `connect` выполняет прикладную задачу приложения.
        
        Параметры:
            self (Any): Текущий экземпляр класса.
            user_id (str): Идентификатор пользователя.
            websocket (WebSocket): Параметр `websocket`.
            db (AsyncSession): Подключение к базе данных.
        
        Возвращает:
            None: Функция не возвращает значение.
        """

        await websocket.accept()
        self.active_connections[user_id] = websocket
        await self.add_connect(db, user_id)

    async def disconnect(self, user_id: str, db: Optional[AsyncSession] = None, code: int = 1000, reason: str = "Disconnect") -> None:
        """Функция `disconnect` выполняет прикладную задачу приложения.
        
        Параметры:
            self (Any): Текущий экземпляр класса.
            user_id (str): Идентификатор пользователя.
            db (Optional[AsyncSession]): Подключение к базе данных. Значение по умолчанию: None.
            code (int): Параметр `code`. Значение по умолчанию: 1000.
            reason (str): Параметр `reason`. Значение по умолчанию: "Disconnect".
        
        Возвращает:
            None: Функция не возвращает значение.
        """

        ws = self.active_connections.pop(user_id, None)
        if ws:
            try:
                await ws.close(code=code, reason=reason)
            except RuntimeError as e:
                if "Unexpected ASGI message 'websocket.close'" not in str(e):
                    raise
        if db:
            await self.delete_by_user_id(db, user_id)

    async def send_to_user(self, user_id: str, message: dict) -> bool:
        """Функция `send_to_user` выполняет прикладную задачу приложения.
        
        Параметры:
            self (Any): Текущий экземпляр класса.
            user_id (str): Идентификатор пользователя.
            message (dict): Параметр `message`.
        
        Возвращает:
            bool: Результат выполнения функции.
        """

        ws = self.active_connections.get(user_id)
        if ws:
            await ws.send_json(message)
            return True
        return False

    @staticmethod
    async def add_connect(db: AsyncSession, user_id: str) -> WebsocketSession:
        """Функция `add_connect` выполняет прикладную задачу приложения.
        
        Параметры:
            db (AsyncSession): Подключение к базе данных.
            user_id (str): Идентификатор пользователя.
        
        Возвращает:
            WebsocketSession: Результат выполнения функции.
        """

        await db.execute(
            delete(WebsocketSession).where(WebsocketSession.user_id == user_id),
        )
        await db.commit()

        ws = WebsocketSession(
            user_id=user_id,
            connected_at=datetime.now(MOSCOW),
            is_active=True,
        )
        db.add(ws)
        await db.commit()
        await db.refresh(ws)
        return ws

    @staticmethod
    async def disconnect_db(user_id: str, db: AsyncSession) -> None:
        """Функция `disconnect_db` выполняет прикладную задачу приложения.
        
        Параметры:
            user_id (str): Идентификатор пользователя.
            db (AsyncSession): Подключение к базе данных.
        
        Возвращает:
            None: Функция не возвращает значение.
        """

        q = (
            update(WebsocketSession)
            .where(WebsocketSession.user_id == user_id)
            .values(disconnected_at=datetime.now(MOSCOW), is_active=False)
        )
        await db.execute(q)
        await db.commit()

    @staticmethod
    async def get_active_by_user(db: AsyncSession, user_id: str) -> list[WebsocketSession]:
        """Функция `get_active_by_user` выполняет прикладную задачу приложения.
        
        Параметры:
            db (AsyncSession): Подключение к базе данных.
            user_id (str): Идентификатор пользователя.
        
        Возвращает:
            list[WebsocketSession]: Результат выполнения функции.
        """

        q = (
            select(WebsocketSession)
            .where(WebsocketSession.user_id == user_id)
            .where(WebsocketSession.is_active)
        )
        res = await db.execute(q)
        return res.scalars().all()

    @staticmethod
    async def delete_by_user_id(db: AsyncSession, user_id: str) -> None:
        """Функция `delete_by_user_id` выполняет прикладную задачу приложения.
        
        Параметры:
            db (AsyncSession): Подключение к базе данных.
            user_id (str): Идентификатор пользователя.
        
        Возвращает:
            None: Функция не возвращает значение.
        """

        q = (
            delete(WebsocketSession)
            .where(WebsocketSession.user_id == user_id)
        )
        await db.execute(q)
        await db.commit()


ws_manager = WSManager()
