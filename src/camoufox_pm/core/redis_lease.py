"""Redis Distributed Locking & Lease Coordinator for CamouHub fleet.

Implements sub-millisecond Redlock mutual exclusion across distributed machines
to prevent multi-instance / multi-host profile concurrent opening:
Key pattern: camouhub:lease:{tenant_id}:{profile_id}
"""

import os
from typing import Any

from loguru import logger

try:
    import redis.asyncio as aioredis
except ImportError:
    aioredis = None  # type: ignore[assignment]


# Lua script for atomic lease release
_RELEASE_LUA = """
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("del", KEYS[1])
else
    return 0
end
"""

# Lua script for atomic lease renewal
_RENEW_LUA = """
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("expire", KEYS[1], ARGV[2])
else
    return 0
end
"""


class RedisLeaseManager:
    """Enterprise distributed lease manager backed by Redis."""

    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self._client: Any = None
        self._release_script: Any = None
        self._renew_script: Any = None

    async def initialize(self) -> bool:
        """Connect to Redis and register Lua scripts."""
        if aioredis is None:
            logger.warning("Redis library not available; distributed locking disabled")
            return False

        try:
            self._client = aioredis.from_url(
                self.redis_url, decode_responses=True, socket_connect_timeout=3.0
            )
            await self._client.ping()
            self._release_script = self._client.register_script(_RELEASE_LUA)
            self._renew_script = self._client.register_script(_RENEW_LUA)
            logger.info(f"Connected to Redis distributed lease hub at {self.redis_url}")
            return True
        except Exception as exc:
            logger.warning(f"Failed to connect to Redis at {self.redis_url}: {exc}")
            self._client = None
            return False

    @property
    def is_available(self) -> bool:
        return self._client is not None

    def _make_key(self, profile_id: str, tenant_id: str = "default") -> str:
        return f"camouhub:lease:{tenant_id}:{profile_id}"

    async def acquire_lease(
        self, profile_id: str, holder: str, ttl_seconds: int = 60, tenant_id: str = "default"
    ) -> bool:
        """Atomically acquire distributed lock for profile.

        Returns True if acquired (or already held by this holder), False if busy.
        """
        if not self.is_available:
            return True  # Fallback to local DB lease if Redis is not configured

        key = self._make_key(profile_id, tenant_id)
        try:
            # 1. Try to set if not exists
            acquired = await self._client.set(key, holder, nx=True, ex=ttl_seconds)
            if acquired:
                logger.debug(f"Redis lease acquired for {profile_id} by {holder}")
                return True

            # 2. If already exists, check if held by same holder (idempotent re-acquisition)
            current_holder = await self._client.get(key)
            if current_holder == holder:
                await self._client.expire(key, ttl_seconds)
                return True

            logger.warning(
                f"Redis lease conflict for {profile_id}: already held by operator '{current_holder}'"
            )
            return False
        except Exception as exc:
            logger.warning(f"Redis error during acquire_lease for {profile_id}: {exc}")
            return True  # Graceful degradation to local database lock

    async def renew_lease(
        self, profile_ids: list[str], holder: str, ttl_seconds: int = 60, tenant_id: str = "default"
    ) -> int:
        """Renew heartbeat for all held leases."""
        if not self.is_available or not profile_ids:
            return len(profile_ids)

        renewed_count = 0
        try:
            for pid in profile_ids:
                key = self._make_key(pid, tenant_id)
                res = await self._renew_script(keys=[key], args=[holder, ttl_seconds])
                if res == 1:
                    renewed_count += 1
        except Exception as exc:
            logger.warning(f"Redis error during renew_lease: {exc}")
            return len(profile_ids)

        return renewed_count

    async def release_lease(
        self, profile_id: str, holder: str, tenant_id: str = "default"
    ) -> bool:
        """Release distributed lock if held by this holder."""
        if not self.is_available:
            return True

        key = self._make_key(profile_id, tenant_id)
        try:
            res = await self._release_script(keys=[key], args=[holder])
            return res == 1
        except Exception as exc:
            logger.warning(f"Redis error during release_lease for {profile_id}: {exc}")
            return False

    async def get_lease_holder(self, profile_id: str, tenant_id: str = "default") -> str | None:
        """Query current lease holder from Redis."""
        if not self.is_available:
            return None
        key = self._make_key(profile_id, tenant_id)
        try:
            return await self._client.get(key)
        except Exception:
            return None

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None


_global_redis_manager: RedisLeaseManager | None = None


def get_redis_lease_manager() -> RedisLeaseManager | None:
    global _global_redis_manager
    if _global_redis_manager is None:
        redis_url = os.environ.get("REDIS_URL") or os.environ.get("CPM_REDIS_URL")
        if redis_url:
            _global_redis_manager = RedisLeaseManager(redis_url)
    return _global_redis_manager
