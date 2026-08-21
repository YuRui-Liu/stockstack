import asyncio
import json
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID

import pytest
from uuid6 import uuid7

from app.catalog.cache import ProductCache
from app.catalog.domain import ProductStatus
from app.catalog.public_service import PublicProductService
from app.catalog.service import ProductService
from app.core.errors import AppError


class FakeRedis:
    def __init__(self):
        self.values = {}
        self.set_calls = []
        self.eval_calls = []

    async def get(self, key):
        return self.values.get(key)

    async def set(self, key, value, **kwargs):
        self.set_calls.append((key, value, kwargs))
        if kwargs.get("nx") and key in self.values:
            return None
        self.values[key] = value
        return True

    async def delete(self, key):
        self.values.pop(key, None)

    async def eval(self, script, numkeys, *args):
        self.eval_calls.append((script, numkeys, args))
        if "ZREMRANGEBYSCORE" in script:
            return [1, 1]
        key, token = args
        if self.values.get(key) == token:
            del self.values[key]
            return 1
        return 0


PRODUCT_ID = UUID("018f3f4e-7b2c-7abc-8def-123456789abc")


class FakeRepository:
    def __init__(self, product=None, error=None):
        self.product = product
        self.error = error
        self.calls = 0

    async def get_public(self, _product_id):
        self.calls += 1
        await asyncio.sleep(0.01)
        if self.error:
            raise self.error
        return self.product


class MemoryProductCache:
    def __init__(self, value=None, broken=False):
        self.value = value
        self.broken = broken

    async def get(self, _product_id):
        if self.broken:
            raise ConnectionError("redis down")
        return self.value

    async def acquire_lock(self, _product_id):
        if self.broken:
            raise ConnectionError("redis down")
        return "token"

    async def release_lock(self, _product_id, _token):
        return None

    async def put_product(self, _product_id, product):
        self.value = {"kind": "product", "product": product, "version": product["version"]}

    async def put_missing(self, _product_id):
        self.value = {"kind": "missing"}

    async def delete(self, _product_id):
        self.value = None


def product_payload():
    return {
        "id": str(PRODUCT_ID), "title": "Public", "short_title": "", "description_html": "",
        "price_amount": "10.00", "stock": 1, "product_type": "physical", "status": "on_shelf",
        "delivery_method": "ems", "return_rule": "seven_days", "attributes": {},
        "schema_version": 1, "images": [], "version": 1,
        "created_at": "2026-01-01T00:00:00Z", "updated_at": "2026-01-01T00:00:00Z",
    }


@pytest.mark.asyncio
async def test_cache_hit_does_not_query_database():
    repo = FakeRepository()
    cache = MemoryProductCache({"kind": "product", "product": product_payload(), "version": 1})
    result = await PublicProductService(repo, cache).detail(PRODUCT_ID)
    assert result.id == PRODUCT_ID
    assert repo.calls == 0


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "cached",
    [
        {"kind": "surprise", "source": "untrusted"},
        {"kind": "product", "product": {"id": str(PRODUCT_ID)}, "version": 1},
    ],
)
async def test_invalid_cache_value_is_deleted_and_treated_as_miss(cached):
    repo = FakeRepository(product_payload())
    cache = MemoryProductCache(cached)
    service = PublicProductService(repo, cache)

    result = await service.detail(PRODUCT_ID)

    assert result.id == PRODUCT_ID
    assert repo.calls == 1


@pytest.mark.asyncio
async def test_negative_cache_prevents_second_database_query():
    repo = FakeRepository()
    service = PublicProductService(repo, MemoryProductCache())
    for _ in range(2):
        with pytest.raises(AppError) as error:
            await service.detail(PRODUCT_ID)
        assert error.value.status_code == 404
    assert repo.calls == 1


@pytest.mark.asyncio
async def test_thirty_concurrent_misses_share_one_database_query():
    repo = FakeRepository(product_payload())
    service = PublicProductService(repo, MemoryProductCache())
    results = await asyncio.gather(*(service.detail(PRODUCT_ID) for _ in range(30)))
    assert len(results) == 30
    assert repo.calls == 1


@pytest.mark.asyncio
async def test_cancelling_one_waiter_keeps_shared_flight_alive_and_cleans_it():
    gate = asyncio.Event()

    class GatedRepository(FakeRepository):
        async def get_public(self, _product_id):
            self.calls += 1
            await gate.wait()
            return self.product

    repo = GatedRepository(product_payload())
    service = PublicProductService(repo, MemoryProductCache())
    cancelled = asyncio.create_task(service.detail(PRODUCT_ID))
    survivor = asyncio.create_task(service.detail(PRODUCT_ID))
    await asyncio.sleep(0)
    cancelled.cancel()
    with pytest.raises(asyncio.CancelledError):
        await cancelled
    gate.set()

    assert (await survivor).id == PRODUCT_ID
    assert repo.calls == 1
    assert service._flights == {}


@pytest.mark.asyncio
@pytest.mark.parametrize("snapshot_after_lock,expected_db_calls", [(True, 0), (False, 1)])
async def test_lock_contention_polling_uses_snapshot_or_bounded_fallback(
    snapshot_after_lock, expected_db_calls
):
    class ContendedCache(MemoryProductCache):
        def __init__(self):
            super().__init__()
            self.get_calls = 0

        async def get(self, _product_id):
            self.get_calls += 1
            if snapshot_after_lock and self.get_calls >= 2:
                return {"kind": "product", "product": product_payload(), "version": 1}
            return None

        async def acquire_lock(self, _product_id):
            return None

    repo = FakeRepository(product_payload())
    service = PublicProductService(repo, ContendedCache(), wait_budget_ms=5)
    result = await service.detail(PRODUCT_ID)
    assert result.id == PRODUCT_ID
    assert repo.calls == expected_db_calls


@pytest.mark.asyncio
async def test_redis_failure_uses_limited_db_fallback_and_db_failure_is_503():
    repo = FakeRepository(error=RuntimeError("db down"))
    service = PublicProductService(repo, MemoryProductCache(broken=True), db_concurrency=1)
    with pytest.raises(AppError) as error:
        await service.detail(PRODUCT_ID)
    assert error.value.status_code == 503


@pytest.mark.asyncio
async def test_redis_failure_bounds_concurrent_database_fallbacks():
    class TrackingRepository:
        def __init__(self):
            self.active = 0
            self.peak = 0

        async def get_public(self, product_id):
            self.active += 1
            self.peak = max(self.peak, self.active)
            await asyncio.sleep(0.02)
            self.active -= 1
            payload = product_payload()
            payload["id"] = str(product_id)
            return payload

    repo = TrackingRepository()
    service = PublicProductService(repo, MemoryProductCache(broken=True), db_concurrency=2)
    await asyncio.gather(*(service.detail(uuid7()) for _ in range(8)))
    assert repo.peak == 2


@pytest.mark.asyncio
async def test_saturated_database_fallback_fails_fast_with_503():
    gate = asyncio.Event()

    class BlockingRepository(FakeRepository):
        async def get_public(self, product_id):
            await gate.wait()
            payload = product_payload()
            payload["id"] = str(product_id)
            return payload

    service = PublicProductService(
        BlockingRepository(),
        MemoryProductCache(broken=True),
        db_concurrency=1,
        db_fallback_wait_ms=5,
    )
    first = asyncio.create_task(service.detail(uuid7()))
    await asyncio.sleep(0)
    with pytest.raises(AppError) as error:
        await service.detail(uuid7())
    assert error.value.status_code == 503
    gate.set()
    await first


@pytest.mark.asyncio
async def test_database_timeout_cleans_flight_and_allows_retry():
    class HangingOnceRepository(FakeRepository):
        async def get_public(self, _product_id):
            self.calls += 1
            if self.calls == 1:
                await asyncio.Event().wait()
            return self.product

    repo = HangingOnceRepository(product_payload())
    service = PublicProductService(
        repo, MemoryProductCache(), db_query_timeout_ms=5
    )

    with pytest.raises(AppError) as error:
        await service.detail(PRODUCT_ID)
    assert error.value.status_code == 503
    assert service._flights == {}
    assert (await service.detail(PRODUCT_ID)).id == PRODUCT_ID
    assert repo.calls == 2


@pytest.mark.asyncio
async def test_status_commit_precedes_cache_delete_and_delete_failure_does_not_rollback():
    class Session:
        committed = False
        rolled_back = False

        async def commit(self):
            self.committed = True

        async def rollback(self):
            self.rolled_back = True

    class Cache:
        calls = 0

        async def delete(self, _product_id):
            self.calls += 1
            assert session.committed
            if self.calls == 1:
                raise ConnectionError("redis down")

    now = datetime.now(UTC)
    product_data = product_payload()
    product_data.update(
        id=PRODUCT_ID,
        price_amount=Decimal("10.00"),
        created_at=now,
        updated_at=now,
        images=[],
    )
    product = SimpleNamespace(**product_data)
    session = Session()
    cache = Cache()
    service = ProductService(session, cache)
    service.repository = SimpleNamespace(
        batch_update_status=lambda *_args, **_kwargs: asyncio.sleep(0, result=[product]),
        get_detail=lambda *_args: asyncio.sleep(0, result=product),
    )

    result = await service.update_status(PRODUCT_ID, 1, ProductStatus.ON_SHELF)
    await asyncio.sleep(0.08)

    assert result.id == PRODUCT_ID
    assert session.committed and not session.rolled_back
    assert cache.calls == 2


@pytest.mark.asyncio
async def test_snapshot_ttl_is_jittered_and_missing_uses_short_fixed_ttl(monkeypatch):
    redis = FakeRedis()
    monkeypatch.setattr("app.catalog.cache.secrets.randbelow", lambda _limit: 7)
    cache = ProductCache(redis, base_ttl_seconds=100, jitter_seconds=10, negative_ttl_seconds=5)

    await cache.put_product(PRODUCT_ID, {"id": str(PRODUCT_ID), "version": 3})
    await cache.put_missing(PRODUCT_ID)

    assert redis.set_calls[0][2]["ex"] == 107
    assert json.loads(redis.set_calls[0][1])["kind"] == "product"
    assert redis.set_calls[1][2]["ex"] == 5
    assert json.loads(redis.set_calls[1][1]) == {"kind": "missing"}


@pytest.mark.asyncio
async def test_lock_uses_random_token_and_lua_compare_delete(monkeypatch):
    redis = FakeRedis()
    tokens = iter(["owner-a", "owner-b"])
    monkeypatch.setattr("app.catalog.cache.secrets.token_urlsafe", lambda _n: next(tokens))
    cache = ProductCache(redis, lock_ttl_ms=2500)

    first = await cache.acquire_lock(PRODUCT_ID)
    second = await cache.acquire_lock(PRODUCT_ID)
    await cache.release_lock(PRODUCT_ID, "wrong-owner")
    assert redis.values[cache.lock_key(PRODUCT_ID)] == "owner-a"
    await cache.release_lock(PRODUCT_ID, first)

    assert first == "owner-a"
    assert second is None
    assert redis.set_calls[0][2] == {"nx": True, "px": 2500}
    assert "redis.call('get'" in redis.eval_calls[0][0]
    assert "redis.call('del'" in redis.eval_calls[0][0]


@pytest.mark.asyncio
async def test_rate_limit_lua_uses_unique_members():
    redis = FakeRedis()
    cache = ProductCache(redis)
    await cache.rate_limit("127.0.0.1", limit=2, window_seconds=10, now_ms=1000)
    await cache.rate_limit("127.0.0.1", limit=2, window_seconds=10, now_ms=1000)

    first_script, _, first_args = redis.eval_calls[0]
    second_args = redis.eval_calls[1][2]
    assert "ZREMRANGEBYSCORE" in first_script
    assert "ZCARD" in first_script
    assert "ZADD" in first_script
    assert first_args[-1] != second_args[-1]
