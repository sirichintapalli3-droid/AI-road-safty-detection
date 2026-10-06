from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.alerts import alert_manager, create_alert

router = APIRouter(tags=["alerts"])


@router.websocket("/ws/alerts")
async def alerts_websocket(websocket: WebSocket) -> None:
    await alert_manager.connect(websocket)
    await websocket.send_json(create_alert("CONNECTED", "Alert stream connected").model_dump(mode="json"))
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        alert_manager.disconnect(websocket)
    except Exception:
        alert_manager.disconnect(websocket)
