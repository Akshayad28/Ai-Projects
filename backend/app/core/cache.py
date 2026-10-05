"""Cache abstraction.

Redis is used whenever REDIS_URL is configured. Without Redis (local
development only) an in-process TTL cache is used and a warning is logged.
Cached payloads always carry their own `cached_at` timestamp so the UI can
show freshness instead of pretending cached data is live.
"""
from __future__ import annotations

import json
import time
from typing import Any, Dict, Optional, Tuple

from app.core.config import get_settings
from app.core.logging import get_logger

log = get_logger(__name__)


class Cache:
    async def get(self, key: str) -> Optional[Any]:
        raise NotImplementedError

    async def set(self, key: str, value: Any, ttl: int) -> None:
        raise NotImplementedError

    async def delete(self, key: str) -> None:
        raise NotImplementedError

    async def incr(self, key: str, ttl: int) -> int:
        raise NotImplementedError


class MemoryCache(Cache):
    def __init__(self, max_size: int = 2000) -> None:
        self._store: Dict[str, Tuple[float, Any]] = {}
        self._max_size = max_size

    def _alive(self, key: str) -> bool:
        item = self._store.get(key)
        if not item:
            return False
        if item[0] < time.time():
            self._store.pop(key, None)
            return False
        return True

    def _cleanup_expired(self) -> None:
        now = time.time()
        expired = [k for k, v in self._store.items() if v[0] < now]
        for k in expired:
            self._store.pop(k, None)

    async def get(self, key: str) -> Optional[Any]:
        return self._store[key][1] if self._alive(key) else None

    async def set(self, key: str, value: Any, ttl: int) -> None:
        if len(self._store) >= self._max_size:
            self._cleanup_expired()
            if len(self._store) >= self._max_size:
                # Evict oldest 20% by expiry time to keep memory bounded
                sorted_entries = sorted(self._store.items(), key=lambda x: x[1][0])
                num_to_evict = max(1, self._max_size // 5)
                for k, _ in sorted_entries[:num_to_evict]:
                    self._store.pop(k, None)
        self._store[key] = (time.time() + ttl, json.loads(json.dumps(value, default=str)))

    async def delete(self, key: str) -> None:
        self._store.pop(key, None)

    async def incr(self, key: str, ttl: int) -> int:
        current = int(await self.get(key) or 0) + 1
        expiry = self._store[key][0] if self._alive(key) else time.time() + ttl
        self._store[key] = (expiry, current)
        return current


class RedisCache(Cache):
    def __init__(self, url: str) -> None:
        import redis.asyncio as redis  # imported lazily

        self._r = redis.from_url(url, decode_responses=True)

    async def get(self, key: str) -> Optional[Any]:
        raw = await self._r.get(key)
        return json.loads(raw) if raw else None

    async def set(self, key: str, value: Any, ttl: int) -> None:
        await self._r.set(key, json.dumps(value, default=str), ex=ttl)

    async def delete(self, key: str) -> None:
        await self._r.delete(key)

    async def incr(self, key: str, ttl: int) -> int:
        pipe = self._r.pipeline()
        pipe.incr(key)
        pipe.expire(key, ttl, nx=True)
        value, _ = await pipe.execute()
        return int(value)


_cache: Optional[Cache] = None


def get_cache() -> Cache:
    global _cache
    if _cache is None:
        settings = get_settings()
        if settings.redis_url:
            _cache = RedisCache(settings.redis_url)
        else:
            if settings.is_production:
                raise RuntimeError("REDIS_URL is required in production.")
            log.warning("REDIS_URL not set – using in-process cache (development only)")
            _cache = MemoryCache()
    return _cache


def set_cache(cache: Cache) -> None:
    """Testing hook."""
    global _cache
    _cache = cache
