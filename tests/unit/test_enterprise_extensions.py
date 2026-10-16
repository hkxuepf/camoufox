import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from camoufox_pm.core.event_bus import EventBus
from camoufox_pm.core.redis_lease import RedisLeaseManager
from camoufox_pm.core.database import StorageManager

@pytest.mark.asyncio
async def test_event_bus_broadcast():
    bus = EventBus()
    ws1 = AsyncMock()
    ws2 = AsyncMock()

    await bus.connect(ws1)
    await bus.connect(ws2)

    await bus.broadcast("TEST_EVENT", {"foo": "bar"})

    # Both websockets should receive the event
    assert ws1.send_text.call_count >= 2  # initial CONNECTED + TEST_EVENT
    assert ws2.send_text.call_count >= 2

    # Disconnect
    await bus.disconnect(ws1)
    await bus.broadcast("AFTER_DISCONNECT", {})
    assert ws2.send_text.call_count >= 3

@pytest.mark.asyncio
async def test_redis_lease_manager_fallback():
    # When redis is offline or invalid URL, lease calls degrade gracefully without error
    mgr = RedisLeaseManager("redis://invalid-host-that-does-not-exist:6379/0")
    connected = await mgr.initialize()
    assert connected is False
    assert mgr.is_available is False

    # Graceful degradation returns True
    acquired = await mgr.acquire_lease("test_p1", "holder1")
    assert acquired is True

    renewed = await mgr.renew_lease(["test_p1"], "holder1")
    assert renewed == 1

    released = await mgr.release_lease("test_p1", "holder1")
    assert released is True

    await mgr.close()

def test_storage_manager_dual_engine_switch(tmp_path: Path):
    sqlite_db = tmp_path / "dual_test.db"
    storage_lite = StorageManager(str(sqlite_db))
    # By default, without postgres in URL, uses DatabaseManager (SQLite)
    from camoufox_pm.core.database import DatabaseManager
    assert isinstance(storage_lite.db, DatabaseManager)

@pytest.mark.asyncio
async def test_storage_manager_postgres_fallback(tmp_path: Path, monkeypatch):
    sqlite_db = tmp_path / "fallback_test.db"
    monkeypatch.setenv("DATABASE_URL", "postgresql://invalid-user:pass@127.0.0.1:54399/nonexistent")
    storage = StorageManager(str(sqlite_db))
    from camoufox_pm.core.postgres_database import PostgresDatabaseManager
    assert isinstance(storage.db, PostgresDatabaseManager)

    # Calling initialize should gracefully fall back to SQLite DatabaseManager without raising exception
    await storage.initialize()
    from camoufox_pm.core.database import DatabaseManager
    assert isinstance(storage.db, DatabaseManager)
    await storage.close()

