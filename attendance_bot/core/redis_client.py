# attendance_bot/core/redis_client.py
import json
from typing import Any, Optional

import redis.asyncio as redis
from redis.asyncio import Redis

from config.settings import get_settings

settings = get_settings()

_redis_client: Optional[Redis] = None


class RedisClient:
    def __init__(self):
        self._client: Optional[Redis] = None

    async def connect(self):
        global _redis_client
        if _redis_client is None:
            _redis_client = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                max_connections=settings.REDIS_POOL_SIZE,
            )
        self._client = _redis_client

    async def disconnect(self):
        global _redis_client
        if _redis_client:
            await _redis_client.close()
            _redis_client = None

    async def get(self, key: str) -> Optional[str]:
        return await self._client.get(key)

    async def set(self, key: str, value: str, expire: Optional[int] = None):
        await self._client.set(key, value, ex=expire)

    async def delete(self, key: str):
        await self._client.delete(key)

    async def exists(self, key: str) -> bool:
        return await self._client.exists(key) > 0

    async def get_json(self, key: str) -> Optional[Any]:
        value = await self.get(key)
        if value:
            return json.loads(value)
        return None

    async def set_json(self, key: str, value: Any, expire: Optional[int] = None):
        await self.set(key, json.dumps(value), expire)

    async def acquire_lock(self, lock_name: str, timeout: int = 10) -> bool:
        return await self._client.set(lock_name, "1", nx=True, ex=timeout)

    async def release_lock(self, lock_name: str):
        await self._client.delete(lock_name)

    async def rate_limit(self, key: str, limit: int, window: int) -> bool:
        current = await self._client.get(key)
        if current is None:
            await self._client.set(key, "1", ex=window)
            return True
        count = int(current)
        if count >= limit:
            return False
        await self._client.incr(key)
        return True


async def get_redis() -> RedisClient:
    client = RedisClient()
    await client.connect()
    return client
