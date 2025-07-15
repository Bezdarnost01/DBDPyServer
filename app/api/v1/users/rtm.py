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
async def websocket_rtm(websocket: WebSocket, path: str):
    await websocket.accept()
    await websocket.send_json({"topic": "connection", "event": "successful"})
    await websocket.send_json({"topic": "initialization", "event": "Fully initialized"})
    try:
        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        pass