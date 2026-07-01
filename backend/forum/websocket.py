from typing import Dict, List, Optional
from uuid import UUID

from fastapi import WebSocket


class ForumConnectionManager:
    """Tracks forum websocket clients and broadcasts post changes.

    Each connection is bound to the authenticated user's id so recipient-scoped
    events (e.g. notifications) go ONLY to that user's sockets, while genuinely
    public forum events still fan out to everyone via broadcast().
    """

    def __init__(self) -> None:
        # websocket -> owning user id. A user may have several open tabs.
        self.active_connections: Dict[WebSocket, UUID] = {}

    async def connect(self, websocket: WebSocket, user_id: UUID) -> None:
        await websocket.accept()
        self.active_connections[websocket] = user_id

    def disconnect(self, websocket: WebSocket) -> None:
        self.active_connections.pop(websocket, None)

    async def _send(self, websocket: WebSocket, message: Dict, dead: List[WebSocket]) -> None:
        try:
            await websocket.send_json(message)
        except Exception:
            dead.append(websocket)

    async def broadcast(self, message: Dict) -> None:
        """Send to every connected client. Use ONLY for public forum events."""
        dead: List[WebSocket] = []
        for websocket in list(self.active_connections):
            await self._send(websocket, message, dead)
        for websocket in dead:
            self.disconnect(websocket)

    async def send_to_user(self, user_id: Optional[UUID], message: Dict) -> None:
        """Send only to the sockets owned by user_id (all their open tabs).

        Recipient-scoped events (notifications) must use this, never broadcast,
        so a user can never receive another user's targeted payloads.
        """
        if user_id is None:
            return
        dead: List[WebSocket] = []
        for websocket, owner in list(self.active_connections.items()):
            if owner == user_id:
                await self._send(websocket, message, dead)
        for websocket in dead:
            self.disconnect(websocket)


manager = ForumConnectionManager()
