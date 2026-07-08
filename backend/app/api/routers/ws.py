"""WebSocket router for engagement event streaming."""
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core import events

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/engagements/{engagement_id}")
async def engagement_ws(websocket: WebSocket, engagement_id: int):
    await websocket.accept()
    channel = f"engagement:{engagement_id}"
    queue = await events.subscribe(channel)
    try:
        while True:
            event = await queue.get()
            await websocket.send_text(json.dumps(event, default=str))
    except WebSocketDisconnect:
        pass
    finally:
        events.unsubscribe(channel, queue)
