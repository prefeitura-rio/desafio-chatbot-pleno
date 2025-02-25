import json
import logging
from typing import Any, Optional, TypeVar, Generic, Type, Dict
import redis.asyncio as redis
from pydantic import BaseModel

from app.core.config import settings

logger = logging.getLogger(__name__)

# Global Redis client
redis_client: Optional[redis.Redis] = None

T = TypeVar("T", bound=BaseModel)


async def init_redis() -> None:
    """Initialize Redis connection."""
    global redis_client
    try:
        redis_client = redis.from_url(
            settings.REDIS_URL, encoding="utf-8", decode_responses=True
        )
        await redis_client.ping()
        logger.info("Redis connection established successfully")
    except Exception as e:
        logger.error(f"Error connecting to Redis: {e}")
        raise


async def close_redis() -> None:
    """Close Redis connection."""
    global redis_client
    if redis_client:
        await redis_client.close()
        logger.info("Redis connection closed")


async def get_redis() -> redis.Redis:
    """
    Get Redis client.

    Returns:
        redis.Redis: Redis client

    Raises:
        RuntimeError: If Redis client is not initialized
    """
    if not redis_client:
        raise RuntimeError("Redis client not initialized")
    return redis_client


class CacheService(Generic[T]):
    """
    Generic service for caching objects in Redis.

    Attributes:
        model_class (Type[T]): Pydantic model class
        prefix (str): Cache key prefix
        ttl (int): Time-to-live in seconds
    """

    def __init__(self, model_class: Type[T], prefix: str, ttl: int = None):
        """
        Initialize CacheService.

        Args:
            model_class (Type[T]): Pydantic model class
            prefix (str): Cache key prefix
            ttl (int, optional): Time-to-live in seconds. Defaults to settings.CACHE_TTL_SECONDS.
        """
        self.model_class = model_class
        self.prefix = prefix
        self.ttl = ttl or settings.CACHE_TTL_SECONDS

    def _get_key(self, obj_id: str) -> str:
        """
        Get cache key for object.

        Args:
            obj_id (str): Object ID

        Returns:
            str: Cache key
        """
        return f"{self.prefix}:{obj_id}"

    async def get(self, obj_id: str) -> Optional[T]:
        """
        Get object from cache.

        Args:
            obj_id (str): Object ID

        Returns:
            Optional[T]: Cached object or None if not found
        """
        redis_conn = await get_redis()
        data = await redis_conn.get(self._get_key(obj_id))

        if not data:
            return None

        try:
            return self.model_class.model_validate_json(data)
        except Exception as e:
            logger.warning(f"Error deserializing cached object: {e}")
            return None

    async def set(self, obj_id: str, obj: T) -> bool:
        """
        Set object in cache.

        Args:
            obj_id (str): Object ID
            obj (T): Object to cache

        Returns:
            bool: True if successful
        """
        redis_conn = await get_redis()
        try:
            await redis_conn.set(
                self._get_key(obj_id), obj.model_dump_json(), ex=self.ttl
            )
            return True
        except Exception as e:
            logger.warning(f"Error caching object: {e}")
            return False

    async def delete(self, obj_id: str) -> bool:
        """
        Delete object from cache.

        Args:
            obj_id (str): Object ID

        Returns:
            bool: True if successful
        """
        redis_conn = await get_redis()
        try:
            await redis_conn.delete(self._get_key(obj_id))
            return True
        except Exception as e:
            logger.warning(f"Error deleting cached object: {e}")
            return False

    async def set_many(self, objects: Dict[str, T]) -> int:
        """
        Set multiple objects in cache.

        Args:
            objects (Dict[str, T]): Dictionary of objects to cache

        Returns:
            int: Number of objects cached
        """
        redis_conn = await get_redis()
        pipe = redis_conn.pipeline()

        try:
            for obj_id, obj in objects.items():
                pipe.set(self._get_key(obj_id), obj.model_dump_json(), ex=self.ttl)
            await pipe.execute()
            return len(objects)
        except Exception as e:
            logger.warning(f"Error caching multiple objects: {e}")
            return 0
