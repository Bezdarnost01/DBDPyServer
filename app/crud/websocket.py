from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from models.websocket import WebsocketSession
from datetime import datetime
from fastapi import WebSocket
from typing import List, Dict
import pytz

MOSCOW = pytz.timezone("Europe/Moscow")

class WSManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, user_id: str, websocket: WebSocket, db: AsyncSession):
        await websocket.accept()
        self.active_connections[user_id] = websocket
        await self.add_connect(db, user_id)
        
    async def disconnect(self, user_id: str, db: AsyncSession = None, code: int = 1000, reason: str = "Disconnect"):
        ws = self.active_connections.pop(user_id, None)
        if ws:
            try:
                await ws.close(code=code, reason=reason)
            except RuntimeError as e:
                if "Unexpected ASGI message 'websocket.close'" not in str(e):
                    raise
        if db:
            await self.delete_by_user_id(db, user_id)

    async def send_to_user(self, user_id: str, message: dict):
        ws = self.active_connections.get(user_id)
        if ws:
            await ws.send_json(message)
            return True
        return False
    
    @staticmethod
    async def add_connect(db: AsyncSession, user_id: str) -> WebsocketSession:
        await db.execute(
            delete(WebsocketSession).where(WebsocketSession.user_id == user_id)
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
    async def disconnect_db(user_id: str, db: AsyncSession):
        q = (
            update(WebsocketSession)
            .where(WebsocketSession.user_id == user_id)
            .values(disconnected_at=datetime.now(MOSCOW), is_active=False)
        )
        await db.execute(q)
        await db.commit()

    @staticmethod
    async def get_active_by_user(db: AsyncSession, user_id: str) -> List[WebsocketSession]:
        q = (
            select(WebsocketSession)
            .where(WebsocketSession.user_id == user_id)
            .where(WebsocketSession.is_active)
        )
        res = await db.execute(q)
        return res.scalars().all()

    @staticmethod
    async def delete_by_user_id(db: AsyncSession, user_id: str):
        q = (
            delete(WebsocketSession)
            .where(WebsocketSession.user_id == user_id)
        )
        await db.execute(q)
        await db.commit()


ws_manager = WSManager()