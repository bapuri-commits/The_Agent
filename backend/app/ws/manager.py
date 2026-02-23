"""
The Agent — WebSocket 연결 관리자
Step 3.1 (Enforcement) 알림에서 본격 활용. 지금은 인프라만 구성.
"""

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def send_personal(self, websocket: WebSocket, data: dict):
        await websocket.send_json(data)

    async def broadcast(self, data: dict):
        disconnected = []
        for conn in self.active_connections:
            try:
                await conn.send_json(data)
            except Exception:
                disconnected.append(conn)
        for conn in disconnected:
            self.disconnect(conn)

    @property
    def connection_count(self) -> int:
        return len(self.active_connections)


ws_manager = ConnectionManager()
