"""Redis cache layer for ARIA — caches LLM responses, web search results, and memory queries."""
import hashlib
import os
from typing import Optional

import redis.asyncio as redis

from .logger import get_logger

logger = get_logger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# TTLs (seconds)
LLM_CACHE_TTL = 3600       # 1 hour for LLM responses
SEARCH_CACHE_TTL = 1800    # 30 min for web search results
MEMORY_CACHE_TTL = 600     # 10 min for memory queries
HISTORY_CACHE_TTL = 300    # 5 min for run history list

_pool: Optional[redis.Redis] = None


async def get_redis() -> redis.Redis:
    """Get or create a Redis connection pool."""
    global _pool
    if _pool is None:
        try:
            _pool = redis.from_url(REDIS_URL, decode_responses=True)
            await _pool.ping()
            logger.info("Redis connected successfully")
        except Exception as e:
            logger.warning(f"Redis unavailable ({e}), caching disabled")
            _pool = None
    return _pool


def _cache_key(prefix: str, data: str) -> str:
    """Create a deterministic cache key."""
    h = hashlib.sha256(data.encode()).hexdigest()[:16]
    return f"aria:{prefix}:{h}"


async def get_cached(prefix: str, key_data: str) -> Optional[str]:
    """Get a cached value by prefix+key_data."""
    r = await get_redis()
    if r is None:
        return None
    try:
        key = _cache_key(prefix, key_data)
        val = await r.get(key)
        if val:
            logger.debug(f"Cache HIT: {key}")
        return val
    except Exception as e:
        logger.warning(f"Redis get error: {e}")
        return None


async def set_cached(prefix: str, key_data: str, value: str, ttl: int = LLM_CACHE_TTL):
    """Set a cached value."""
    r = await get_redis()
    if r is None:
        return
    try:
        key = _cache_key(prefix, key_data)
        await r.set(key, value, ex=ttl)
        logger.debug(f"Cache SET: {key} (ttl={ttl}s)")
    except Exception as e:
        logger.warning(f"Redis set error: {e}")


async def invalidate_cached(prefix: str, key_data: str):
    """Delete a specific cached value."""
    r = await get_redis()
    if r is None:
        return
    try:
        key = _cache_key(prefix, key_data)
        await r.delete(key)
    except Exception as e:
        logger.warning(f"Redis delete error: {e}")


async def invalidate_prefix(prefix: str):
    """Delete all keys with a given prefix."""
    r = await get_redis()
    if r is None:
        return
    try:
        async for key in r.scan_iter(f"aria:{prefix}:*"):
            await r.delete(key)
    except Exception as e:
        logger.warning(f"Redis prefix invalidation error: {e}")


async def close_redis():
    """Close the Redis connection pool."""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
