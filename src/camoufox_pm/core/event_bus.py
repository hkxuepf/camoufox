"""WebSocket Real-Time Event Bus for CamouHub fleet synchronization.

Broadcasts live state changes (PROFILE_SYNC_COMPLETED, PROFILE_STATUS_CHANGED,
LEASE_ACQUIRED, LEASE_RELEASED) to all connected desktop/web clients without
requiring frequent polling.
"""

import asyncio
import datetime
import json
from typing import Any

from fastapi import WebSocket
from loguru import logger


class EventBus:
    """Manages active client WebSocket connections and broadcasts events."""

    def __init__(self):
        self._active_connections: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        async with self._lock:
            self._active_connections.add(websocket)
        logger.debug(f"EventBus: Client connected. Total active: {len(self._active_connections)}")
        try:
            await websocket.send_text(
                json.dumps({
                    "event": "SYSTEM_CONNECTED",
                    "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    "message": "CamouHub Real-Time Event Bus Connected",
                })
            )
        except Exception:
            pass

    async def disconnect(self, websocket: WebSocket) -> None:
        """Unregister a disconnected WebSocket."""
        async with self._lock:
            self._active_connections.discard(websocket)
        logger.debug(f"EventBus: Client disconnected. Total active: {len(self._active_connections)}")

    async def broadcast(self, event_type: str, payload: dict[str, Any] | None = None) -> None:
        """Broadcast an event to all connected clients."""
        if not self._active_connections:
            return

        message = {
            "event": event_type,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            **(payload or {}),
        }
        encoded = json.dumps(message, default=str)

        async with self._lock:
            targets = list(self._active_connections)

        dead_connections = []
        for ws in targets:
            try:
                await ws.send_text(encoded)
            except Exception:
                dead_connections.append(ws)

        if dead_connections:
            async with self._lock:
                for ws in dead_connections:
                    self._active_connections.discard(ws)


# Global singleton instance
event_bus = EventBus()
