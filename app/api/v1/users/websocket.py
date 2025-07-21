from fastapi import APIRouter, Depends, HTTPException, Response, Request, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from schemas.config import settings
from db.users import get_user_session
from db.sessions import get_sessions_session
from crud.sessions import SessionManager
from crud.users import UserManager
import uuid
from utils.utils import Utils
from utils.users import UserWorker

router = APIRouter(tags=["RTM"])

class WSConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, user_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[user_id] = websocket

    def disconnect(self, user_id: str):
        self.active_connections.pop(user_id, None)

    async def send_to_user(self, user_id: str, message: dict):
        ws = self.active_connections.get(user_id)
        if ws:
            await ws.send_json(message)
            return True
        return False

ws_manager = WSConnectionManager()

@router.get("/offtrack/api/realTimeMessaging/getUrl")
async def get_rtm_url(request: Request,
                      db_users: AsyncSession = Depends(get_user_session),
                      db_sessions: AsyncSession = Depends(get_sessions_session)):
    bhvr_session = request.cookies.get("bhvrSession")
    if not bhvr_session:
        raise HTTPException(status_code=401, detail="No session cookie")
    
    user_id = await SessionManager.get_user_id_by_session(db_sessions, bhvr_session)
    if not user_id:
        raise HTTPException(status_code=401, detail="Session not found")
    
    token1 = uuid.uuid4()
    token2 = uuid.uuid4()

    path = f"{user_id}:{str(token1)}:{str(token2)}"
    url = f"wss://dbdclub.live/{path}"
    return {"url": url, "path": f"/{path}"}

@router.websocket("/{path}")
async def websocket_rtm(websocket: WebSocket, path: str, db_sessions: AsyncSession = Depends(get_sessions_session)):
    try:
        user_id, token1, token2 = path.split(":")
    except ValueError:
        await websocket.close()
        return

    await ws_manager.connect(user_id, websocket)
    await ws_manager.send_to_user(user_id, {"topic": "connection", "event": "successful"})
    await ws_manager.send_to_user(user_id, {"topic": "initialization", "event": "Fully initialized"})

    try:
        while True:
            data = await websocket.receive_text()
            # Можешь здесь обрабатывать входящие сообщения, например
            # await ws_manager.send_to_user(user_id, {"echo": data})
    except WebSocketDisconnect:
        ws_manager.disconnect(user_id)
        # Здесь можно сделать дополнительный cleanup в БД, если нужно

# Пример использования из другого кода:
# await ws_manager.send_to_user(user_id, {"topic": "your_topic", "event": "push!"})
