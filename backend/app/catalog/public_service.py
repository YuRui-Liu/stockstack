from __future__ import annotations

import asyncio
from typing import Any, Protocol
from uuid import UUID

from app.catalog.cache import ProductCache
from app.catalog.schemas import ProductView
from app.catalog.service import _view
from app.core.errors import AppError
from app.core.metrics import (
    CACHE_RESULTS,
    DB_FALLBACKS,
    DEPENDENCY_ERRORS,
    LOCK_CONTENTION,
)


class PublicRepository(Protocol):
    async def get_public(self, product_id: UUID) -> Any: ...


class PublicProductService:
    def __init__(
        self,
        repository: PublicRepository,
        cache: ProductCache,
        *,
        db_concurrency: int = 10,
        wait_budget_ms: int = 250,
        redis_timeout_seconds: float = 0.2,
    ) -> None:
        self.repository = repository
        self.cache = cache
        self.wait_budget_ms = wait_budget_ms
        self.redis_timeout_seconds = redis_timeout_seconds
        self._db_slots = asyncio.Semaphore(db_concurrency)
        self._flights: dict[UUID, asyncio.Task[ProductView]] = {}
        self._flights_lock = asyncio.Lock()

    async def detail(self, product_id: UUID) -> ProductView:
        cached = await self._cache_get(product_id)
        if cached is not None:
            return self._cached_view(cached)
        async with self._flights_lock:
            task = self._flights.get(product_id)
            if task is None or task.done():
                task = asyncio.create_task(self._run_flight(product_id))
                self._flights[product_id] = task
        return await asyncio.shield(task)

    async def _run_flight(self, product_id: UUID) -> ProductView:
        task = asyncio.current_task()
        try:
            return await self._load(product_id)
        finally:
            async with self._flights_lock:
                if self._flights.get(product_id) is task:
                    self._flights.pop(product_id, None)

    async def _cache_get(self, product_id: UUID) -> dict[str, Any] | None:
        try:
            value = await asyncio.wait_for(
                self.cache.get(product_id), self.redis_timeout_seconds
            )
            CACHE_RESULTS.labels("miss" if value is None else value["kind"]).inc()
            return value
        except Exception:  # noqa: BLE001 -- any cache failure must degrade safely
            DEPENDENCY_ERRORS.labels("redis", "cache_get").inc()
            return None

    @staticmethod
    def _cached_view(value: dict[str, Any]) -> ProductView:
        if value["kind"] == "missing":
            raise AppError("product_not_found", "Product not found", 404)
        return ProductView.model_validate(value["product"])

    async def _load(self, product_id: UUID) -> ProductView:
        try:
            token = await asyncio.wait_for(
                self.cache.acquire_lock(product_id), self.redis_timeout_seconds
            )
        except Exception:  # noqa: BLE001 -- any cache failure must degrade safely
            DEPENDENCY_ERRORS.labels("redis", "lock").inc()
            return await self._query_db(product_id, fallback_reason="redis_error")
        if token is not None:
            try:
                return await self._query_db(product_id, populate_cache=True)
            finally:
                try:
                    await asyncio.wait_for(
                        self.cache.release_lock(product_id, token),
                        self.redis_timeout_seconds,
                    )
                except Exception:  # noqa: BLE001 -- lock expiry remains the safety net
                    DEPENDENCY_ERRORS.labels("redis", "lock_release").inc()

        LOCK_CONTENTION.inc()
        deadline = asyncio.get_running_loop().time() + self.wait_budget_ms / 1000
        while asyncio.get_running_loop().time() < deadline:
            await asyncio.sleep(min(0.025, self.wait_budget_ms / 1000))
            cached = await self._cache_get(product_id)
            if cached is not None:
                return self._cached_view(cached)
        return await self._query_db(product_id, fallback_reason="lock_timeout")

    async def _query_db(
        self,
        product_id: UUID,
        *,
        populate_cache: bool = False,
        fallback_reason: str | None = None,
    ) -> ProductView:
        if fallback_reason:
            DB_FALLBACKS.labels(fallback_reason).inc()
        try:
            async with self._db_slots:
                product = await self.repository.get_public(product_id)
        except Exception as error:
            DEPENDENCY_ERRORS.labels("postgres", "public_product").inc()
            raise AppError("dependency_unavailable", "Product service unavailable", 503) from error
        if product is None:
            if populate_cache:
                try:
                    await asyncio.wait_for(
                        self.cache.put_missing(product_id), self.redis_timeout_seconds
                    )
                except Exception:  # noqa: BLE001 -- cache population is best effort
                    DEPENDENCY_ERRORS.labels("redis", "cache_write").inc()
            raise AppError("product_not_found", "Product not found", 404)
        view = ProductView.model_validate(product) if isinstance(product, dict) else _view(product)
        if populate_cache:
            try:
                await asyncio.wait_for(
                    self.cache.put_product(product_id, view.model_dump(mode="json")),
                    self.redis_timeout_seconds,
                )
            except Exception:  # noqa: BLE001 -- cache population is best effort
                DEPENDENCY_ERRORS.labels("redis", "cache_write").inc()
        return view
