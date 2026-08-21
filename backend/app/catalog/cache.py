from __future__ import annotations

import json
import secrets
import time
from typing import Any, Protocol
from uuid import UUID


class RedisProtocol(Protocol):
    async def get(self, key: str) -> Any: ...
    async def set(self, key: str, value: str, **kwargs: Any) -> Any: ...
    async def delete(self, key: str) -> Any: ...
    async def eval(self, script: str, numkeys: int, *args: Any) -> Any: ...


RELEASE_LOCK_LUA = """
if redis.call('get', KEYS[1]) == ARGV[1] then
  return redis.call('del', KEYS[1])
end
return 0
"""

RATE_LIMIT_LUA = """
redis.call('ZREMRANGEBYSCORE', KEYS[1], 0, ARGV[1])
local count = redis.call('ZCARD', KEYS[1])
if count >= tonumber(ARGV[2]) then return {0, count} end
redis.call('ZADD', KEYS[1], ARGV[3], ARGV[5])
redis.call('PEXPIRE', KEYS[1], ARGV[4])
return {1, count + 1}
"""


class ProductCache:
    def __init__(
        self,
        redis: RedisProtocol,
        *,
        base_ttl_seconds: int = 300,
        jitter_seconds: int = 30,
        negative_ttl_seconds: int = 30,
        lock_ttl_ms: int = 3000,
    ) -> None:
        self.redis = redis
        self.base_ttl_seconds = base_ttl_seconds
        self.jitter_seconds = jitter_seconds
        self.negative_ttl_seconds = negative_ttl_seconds
        self.lock_ttl_ms = lock_ttl_ms

    @staticmethod
    def key(product_id: UUID) -> str:
        return f"product:v1:{product_id}"

    @staticmethod
    def lock_key(product_id: UUID) -> str:
        return f"product-lock:v1:{product_id}"

    async def get(self, product_id: UUID) -> dict[str, Any] | None:
        raw = await self.redis.get(self.key(product_id))
        if raw is None:
            return None
        if isinstance(raw, bytes):
            raw = raw.decode()
        return json.loads(raw)

    async def put_product(self, product_id: UUID, product: dict[str, Any]) -> None:
        jitter = secrets.randbelow(self.jitter_seconds + 1) if self.jitter_seconds else 0
        payload = {"kind": "product", "product": product, "version": product["version"]}
        await self.redis.set(
            self.key(product_id), json.dumps(payload), ex=self.base_ttl_seconds + jitter
        )

    async def put_missing(self, product_id: UUID) -> None:
        await self.redis.set(
            self.key(product_id),
            json.dumps({"kind": "missing"}),
            ex=self.negative_ttl_seconds,
        )

    async def delete(self, product_id: UUID) -> None:
        await self.redis.delete(self.key(product_id))

    async def acquire_lock(self, product_id: UUID) -> str | None:
        token = secrets.token_urlsafe(24)
        acquired = await self.redis.set(
            self.lock_key(product_id), token, nx=True, px=self.lock_ttl_ms
        )
        return token if acquired else None

    async def release_lock(self, product_id: UUID, token: str) -> None:
        await self.redis.eval(RELEASE_LOCK_LUA, 1, self.lock_key(product_id), token)

    async def rate_limit(
        self, client_ip: str, *, limit: int, window_seconds: int, now_ms: int | None = None
    ) -> tuple[bool, int]:
        current = now_ms if now_ms is not None else int(time.time() * 1000)
        member = f"{current}:{secrets.token_urlsafe(12)}"
        result = await self.redis.eval(
            RATE_LIMIT_LUA,
            1,
            f"public-rate:v1:{client_ip}",
            current - window_seconds * 1000,
            limit,
            current,
            window_seconds * 1000,
            member,
        )
        return bool(result[0]), int(result[1])
