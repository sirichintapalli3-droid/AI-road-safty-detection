from datetime import datetime, timezone

from fastapi import WebSocket

from app.schemas.detection import AlertMessage


class AlertManager:
    def __init__(self) -> None:
        self.connections: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.connections.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self.connections.discard(websocket)

    async def broadcast(self, alert: AlertMessage) -> None:
        disconnected: list[WebSocket] = []
        for websocket in self.connections.copy():
            try:
                await websocket.send_json(alert.model_dump(mode="json"))
            except Exception:
                disconnected.append(websocket)
        for websocket in disconnected:
            self.disconnect(websocket)


def create_alert(alert_type: str, message: str, details: dict[str, object] | None = None) -> AlertMessage:
    return AlertMessage(
        alert_type=alert_type,
        message=message,
        timestamp=datetime.now(timezone.utc),
        details=details or {},
    )


alert_manager = AlertManager()
