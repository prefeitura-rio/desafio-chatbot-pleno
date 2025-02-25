"""
Redis service for caching and rate limiting.
"""

import json
from typing import Any, Optional, Union
from datetime import datetime, timedelta

import redis.asyncio as redis

from app.core.config import settings


class RedisService:
    """
    Redis service for caching and rate limiting.
    """

    def __init__(self):
        """Initialize the Redis service."""
        self.redis_url = settings.REDIS_URI
        self.redis_client = None
        self.default_ttl = settings.CACHE_TTL_SECONDS

    async def connect(self) -> None:
        """
        Connect to Redis.
        """
        if not self.redis_client:
            self.redis_client = redis.from_url(self.redis_url, decode_responses=True)

    async def disconnect(self) -> None:
        """
        Disconnect from Redis.
        """
        if self.redis_client:
            await self.redis_client.close()
            self.redis_client = None

    async def get(self, key: str) -> Any:
        """
        Get value from Redis.

        Args:
            key: Redis key

        Returns:
            Any: Value from Redis or None if not found
        """
        await self.connect()
        try:
            value = await self.redis_client.get(key)
            if value:
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return value
            return None
        except Exception as e:
            return None

    async def set(
        self, key: str, value: Any, ttl: Optional[int] = None
    ) -> bool:
        """
        Set value in Redis.

        Args:
            key: Redis key
            value: Value to set
            ttl: Time-to-live in seconds

        Returns:
            bool: True if successful, False otherwise
        """
        await self.connect()
        try:
            if isinstance(value, (dict, list, tuple, set)):
                value = json.dumps(value)
            return await self.redis_client.set(
                key, value, ex=ttl or self.default_ttl
            )
        except Exception as e:
            return False

    async def delete(self, key: str) -> bool:
        """
        Delete key from Redis.

        Args:
            key: Redis key

        Returns:
            bool: True if successful, False otherwise
        """
        await self.connect()
        try:
            return await self.redis_client.delete(key) > 0
        except Exception as e:
            return False

    async def increment(self, key: str, ttl: Optional[int] = None) -> int:
        """
        Increment key in Redis.

        Args:
            key: Redis key
            ttl: Time-to-live in seconds

        Returns:
            int: New value after increment
        """
        await self.connect()
        try:
            value = await self.redis_client.incr(key)
            if ttl:
                await self.redis_client.expire(key, ttl)
            return value
        except Exception as e:
            return 0

    async def check_rate_limit(
        self, key: str, limit: int, window_seconds: int
    ) -> tuple[bool, int, int]:
        """
        Check if rate limit is exceeded.

        Args:
            key: Rate limit key
            limit: Maximum number of requests
            window_seconds: Time window in seconds

        Returns:
            tuple[bool, int, int]: (is_allowed, current_count, reset_seconds)
        """
        await self.connect()
        try:
            # Get current time window
            current_ts = int(datetime.utcnow().timestamp())
            window_start = current_ts - (current_ts % window_seconds)
            window_key = f"rate:{key}:{window_start}"

            # Get current count
            count = await self.redis_client.incr(window_key)
            
            # Set expiration if this is the first increment
            if count == 1:
                await self.redis_client.expire(window_key, window_seconds)

            # Calculate reset time
            reset_seconds = window_seconds - (current_ts % window_seconds)

            # Check if limit exceeded
            is_allowed = count <= limit

            return is_allowed, count, reset_seconds
        except Exception as e:
            # On error, allow the request but return 0 remaining
            return True, limit, 0

    async def cache_get(self, key: str) -> Any:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Any: Cached value or None if not found
        """
        cache_key = f"cache:{key}"
        return await self.get(cache_key)

    async def cache_set(
        self, key: str, value: Any, ttl: Optional[int] = None
    ) -> bool:
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds

        Returns:
            bool: True if successful, False otherwise
        """
        cache_key = f"cache:{key}"
        return await self.set(cache_key, value, ttl)

    async def cache_delete(self, key: str) -> bool:
        """
        Delete key from cache.

        Args:
            key: Cache key

        Returns:
            bool: True if successful, False otherwise
        """
        cache_key = f"cache:{key}"
        return await self.delete(cache_key)

    async def cache_invalidate_pattern(self, pattern: str) -> int:
        """
        Invalidate cache keys matching pattern.

        Args:
            pattern: Key pattern to invalidate

        Returns:
            int: Number of keys invalidated
        """
        await self.connect()
        try:
            cache_pattern = f"cache:{pattern}"
            cursor = '0'
            count = 0
            
            while cursor != 0:
                cursor, keys = await self.redis_client.scan(cursor, match=cache_pattern, count=100)
                if keys:
                    count += await self.redis_client.delete(*keys)
                    
            return count
        except Exception as e:
            return 0

    async def login_rate_limit(self, email_or_ip: str) -> tuple[bool, int, int]:
        """
        Check login rate limit.

        Args:
            email_or_ip: Email or IP address

        Returns:
            tuple[bool, int, int]: (is_allowed, current_count, reset_seconds)
        """
        key = f"login_limit:{email_or_ip}"
        return await self.check_rate_limit(
            key,
            settings.LOGIN_RATE_LIMIT_PER_MINUTE,
            60  # 1 minute window
        )

    async def signup_rate_limit(self, ip_address: str) -> tuple[bool, int, int]:
        """
        Check signup rate limit.

        Args:
            ip_address: IP address

        Returns:
            tuple[bool, int, int]: (is_allowed, current_count, reset_seconds)
        """
        key = f"signup_limit:{ip_address}"
        return await self.check_rate_limit(
            key,
            settings.SIGNUP_RATE_LIMIT_PER_DAY,
            86400  # 24 hour window
        ) 