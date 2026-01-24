"""Redis client for caching and message broker."""

import json
from typing import Any

import redis.asyncio as redis
import structlog

from app.config import settings

logger = structlog.get_logger()


class RedisClient:
    """Async Redis client wrapper."""

    def __init__(self) -> None:
        self._client: redis.Redis | None = None

    async def connect(self) -> None:
        """Connect to Redis server."""
        try:
            self._client = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
            )
            # Test connection
            await self._client.ping()
            logger.info("Redis connection established", url=settings.REDIS_URL)
        except Exception as e:
            logger.error("Failed to connect to Redis", error=str(e))
            raise

    async def disconnect(self) -> None:
        """Disconnect from Redis server."""
        if self._client:
            await self._client.close()
            logger.info("Redis connection closed")

    @property
    def client(self) -> redis.Redis:
        """Get the Redis client instance."""
        if not self._client:
            raise RuntimeError("Redis client not connected")
        return self._client

    async def get(self, key: str) -> str | None:
        """Get a value from Redis."""
        return await self.client.get(key)

    async def set(
        self,
        key: str,
        value: str,
        expire: int | None = None,
    ) -> bool:
        """Set a value in Redis with optional expiration in seconds."""
        return await self.client.set(key, value, ex=expire)

    async def delete(self, key: str) -> int:
        """Delete a key from Redis."""
        return await self.client.delete(key)

    async def exists(self, key: str) -> bool:
        """Check if a key exists in Redis."""
        return await self.client.exists(key) > 0

    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiration on a key."""
        return await self.client.expire(key, seconds)

    async def ttl(self, key: str) -> int:
        """Get time to live for a key in seconds."""
        return await self.client.ttl(key)

    # JSON helpers
    async def get_json(self, key: str) -> Any | None:
        """Get a JSON value from Redis."""
        value = await self.get(key)
        if value:
            return json.loads(value)
        return None

    async def set_json(
        self,
        key: str,
        value: Any,
        expire: int | None = None,
    ) -> bool:
        """Set a JSON value in Redis."""
        return await self.set(key, json.dumps(value), expire=expire)

    # Hash operations
    async def hget(self, name: str, key: str) -> str | None:
        """Get a field from a hash."""
        return await self.client.hget(name, key)

    async def hset(self, name: str, key: str, value: str) -> int:
        """Set a field in a hash."""
        return await self.client.hset(name, key, value)

    async def hgetall(self, name: str) -> dict[str, str]:
        """Get all fields from a hash."""
        return await self.client.hgetall(name)

    async def hdel(self, name: str, *keys: str) -> int:
        """Delete fields from a hash."""
        return await self.client.hdel(name, *keys)

    # List operations
    async def lpush(self, key: str, *values: str) -> int:
        """Push values to the left of a list."""
        return await self.client.lpush(key, *values)

    async def rpush(self, key: str, *values: str) -> int:
        """Push values to the right of a list."""
        return await self.client.rpush(key, *values)

    async def lrange(self, key: str, start: int, end: int) -> list[str]:
        """Get a range of elements from a list."""
        return await self.client.lrange(key, start, end)

    async def llen(self, key: str) -> int:
        """Get the length of a list."""
        return await self.client.llen(key)

    # Set operations
    async def sadd(self, key: str, *values: str) -> int:
        """Add members to a set."""
        return await self.client.sadd(key, *values)

    async def smembers(self, key: str) -> set[str]:
        """Get all members of a set."""
        return await self.client.smembers(key)

    async def sismember(self, key: str, value: str) -> bool:
        """Check if a value is a member of a set."""
        return await self.client.sismember(key, value)

    # Pub/Sub
    async def publish(self, channel: str, message: str) -> int:
        """Publish a message to a channel."""
        return await self.client.publish(channel, message)

    def pubsub(self) -> redis.client.PubSub:
        """Get a PubSub instance."""
        return self.client.pubsub()

    # Locking
    def lock(
        self,
        name: str,
        timeout: float | None = None,
        blocking: bool = True,
        blocking_timeout: float | None = None,
    ) -> redis.lock.Lock:
        """Create a distributed lock."""
        return self.client.lock(
            name,
            timeout=timeout,
            blocking=blocking,
            blocking_timeout=blocking_timeout,
        )


class CacheService:
    """High-level caching service."""

    def __init__(self, redis_client: RedisClient) -> None:
        self.redis = redis_client

    def _make_key(self, namespace: str, key: str) -> str:
        """Create a namespaced cache key."""
        return f"cache:{namespace}:{key}"

    async def get(self, namespace: str, key: str) -> Any | None:
        """Get a cached value."""
        cache_key = self._make_key(namespace, key)
        return await self.redis.get_json(cache_key)

    async def set(
        self,
        namespace: str,
        key: str,
        value: Any,
        ttl: int = 3600,
    ) -> bool:
        """Cache a value with TTL in seconds."""
        cache_key = self._make_key(namespace, key)
        return await self.redis.set_json(cache_key, value, expire=ttl)

    async def delete(self, namespace: str, key: str) -> int:
        """Delete a cached value."""
        cache_key = self._make_key(namespace, key)
        return await self.redis.delete(cache_key)

    async def invalidate_namespace(self, namespace: str) -> int:
        """Invalidate all keys in a namespace."""
        pattern = self._make_key(namespace, "*")
        deleted = 0
        async for key in self.redis.client.scan_iter(match=pattern):
            deleted += await self.redis.delete(key)
        return deleted


# Singleton instance for dependency injection
redis_client = RedisClient()
