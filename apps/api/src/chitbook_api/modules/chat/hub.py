"""Live chat fan-out across API workers using Postgres LISTEN/NOTIFY.

Flow: a message is saved -> `pg_notify('chat_messages', json)` runs in the same transaction ->
Postgres delivers it on commit to every worker's listener -> each worker pushes it to the
WebSockets of that group connected to it.
"""

from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from typing import Any

import asyncpg
import structlog
from fastapi import WebSocket
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from chitbook_api.core.config import get_settings

log = structlog.get_logger("chitbook.chat.hub")

CHANNEL = "chat_messages"


class ChatHub:
    def __init__(self) -> None:
        self._rooms: dict[int, set[WebSocket]] = defaultdict(set)
        self._conn: asyncpg.Connection | None = None

    async def start(self) -> None:
        s = get_settings()
        self._conn = await asyncpg.connect(
            host=s.db_host, port=s.db_port, user=s.db_user, password=s.db_password.get_secret_value(),
            database=s.db_name, server_settings={"application_name": "chitbook-chat-listener"},
        )  # fmt: skip
        await self._conn.add_listener(CHANNEL, self._on_notify)
        log.info("chat.hub_started")

    async def stop(self) -> None:
        if self._conn is not None:
            await self._conn.close()
            self._conn = None

    def join(self, group_id: int, ws: WebSocket) -> None:
        self._rooms[group_id].add(ws)

    def leave(self, group_id: int, ws: WebSocket) -> None:
        self._rooms[group_id].discard(ws)

    def _on_notify(self, _conn: Any, _pid: int, _channel: str, payload: str) -> None:
        data = json.loads(payload)
        asyncio.get_running_loop().create_task(self._broadcast(int(data["groupId"]), data["message"]))

    async def _broadcast(self, group_id: int, message: dict[str, Any]) -> None:
        for ws in list(self._rooms.get(group_id, ())):
            try:
                await ws.send_json({"type": "message", "data": message})
            except Exception:  # client went away; its handler cleans up
                self.leave(group_id, ws)


hub = ChatHub()


async def publish(session: AsyncSession, group_id: int, message: dict[str, Any]) -> None:
    """Queues a notification that Postgres sends only if the transaction commits."""
    payload = json.dumps({"groupId": group_id, "message": message})
    await session.execute(
        text("SELECT pg_notify(:channel, :payload)"), {"channel": CHANNEL, "payload": payload}
    )
