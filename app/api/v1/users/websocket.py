from fastapi import APIRouter, Depends, HTTPException, Request, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from db.users import get_user_session
from db.sessions import get_sessions_session
from crud.sessions import SessionManager
import uuid
from crud.websocket import ws_manager


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
async def websocket_rtm(websocket: WebSocket, path: str, db_sessions: AsyncSession = Depends(get_sessions_session)):
    try:
        user_id, token1, token2 = path.split(":")
    except ValueError:
        await websocket.close()
        return

    await ws_manager.connect(user_id, websocket=websocket, db=db_sessions)
    await ws_manager.send_to_user(user_id, {"topic": "connection", "event": "successful"})
    await ws_manager.send_to_user(user_id, {"topic": "initialization", "event": "Fully initialized"})

    try:
        while True:
            await websocket.receive_text()
            # Можешь здесь обрабатывать входящие сообщения, например
            # await ws_manager.send_to_user(user_id, {"echo": data})
    except WebSocketDisconnect:
        await ws_manager.disconnect(user_id)
        await SessionManager.delete_session(db_sessions, user_id=user_id)

# _active_clients: dict[WebSocket, str] = {}
# _clients_lock = asyncio.Lock()

# async def _broadcast(payload: dict, exclude: WebSocket | None = None):
#     async with _clients_lock:
#         targets = [ws for ws in _active_clients.keys() if ws is not exclude]
#     tasks = [asyncio.create_task(ws.send_json(payload)) for ws in targets]
#     if tasks:
#         await asyncio.gather(*tasks, return_exceptions=True)

# async def _broadcast_bytes(data: bytes, exclude: WebSocket | None = None):
#     async with _clients_lock:
#         targets = [ws for ws in _active_clients.keys() if ws is not exclude]
#     tasks = [asyncio.create_task(ws.send_bytes(data)) for ws in targets]
#     if tasks:
#         await asyncio.gather(*tasks, return_exceptions=True)

# @router.websocket("/ws/test")
# async def websocket_test(websocket: WebSocket, name: str | None = Query(default=None)):
#     user_name = name.strip() if name else f"user-{uuid.uuid4().hex[:6]}"
#     await websocket.accept()

#     async with _clients_lock:
#         _active_clients[websocket] = user_name
#         users_online = len(_active_clients)

#     logging.info(f"[WS] Connected: {user_name} from {websocket.client}")

#     await websocket.send_json({
#         "type": "welcome",
#         "message": "Test WebSocket connection established",
#         "you": user_name,
#         "online": users_online
#     })
#     await _broadcast({
#         "type": "system",
#         "message": f"{user_name} joined the chat",
#         "online": users_online
#     }, exclude=websocket)

#     try:
#         while True:
#             try:
#                 msg = await websocket.receive()
#             except WebSocketDisconnect:
#                 break  # выходим из цикла, не даём упасть в RuntimeError

#             if msg["type"] == "websocket.disconnect":
#                 break

#             if msg.get("text") is not None:
#                 text = msg["text"]
#                 logging.info(f"[WS] {user_name} (text): {text}")

#                 if text.strip().lower() == "ping":
#                     await websocket.send_text("pong")
#                     continue

#                 await _broadcast({
#                     "type": "message",
#                     "from": user_name,
#                     "text": text
#                 }, exclude=websocket)

#                 await websocket.send_json({
#                     "type": "you",
#                     "text": text
#                 })

#             elif msg.get("bytes") is not None:
#                 data = msg["bytes"]
#                 logging.info(f"[WS] {user_name} (binary): {len(data)} bytes")

#                 await _broadcast({
#                     "type": "system",
#                     "message": f"{user_name} sent binary payload ({len(data)} bytes)"
#                 })

#                 await _broadcast_bytes(data, exclude=websocket)

#                 await websocket.send_json({
#                     "type": "you-binary",
#                     "bytes": base64.b64encode(data).decode("utf-8")
#                 })

#     except WebSocketDisconnect:
#         async with _clients_lock:
#             _active_clients.pop(websocket, None)
#             users_online = len(_active_clients)

#         logging.info(f"[WS] Disconnected: {user_name} from {websocket.client}")
#         print(f"[WS] Client disconnected: {user_name} {websocket.client}")
#         await _broadcast({
#             "type": "system",
#             "message": f"{user_name} left the chat",
#             "online": users_online
#         })
#     except Exception as e:
#         logging.exception(f"[WS] Error for {user_name}: {e}")
#         try:
#             await websocket.close(code=1011)
#         except RuntimeError:
#             pass
#         finally:
#             async with _clients_lock:
#                 _active_clients.pop(websocket, None)
#             await _broadcast({
#                 "type": "system",
#                 "message": f"{user_name} disconnected (error)",
#                 "online": len(_active_clients)
#             })