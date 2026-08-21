import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import UUID

from fastapi import FastAPI, Response
from fastapi.staticfiles import StaticFiles
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from redis.asyncio import Redis

from app.auth.router import router as auth_router
from app.catalog.cache import ProductCache
from app.catalog.public_router import router as public_router
from app.catalog.public_service import PublicProductService
from app.catalog.repository import ProductRepository
from app.catalog.router import router as catalog_router
from app.catalog.service import _INVALIDATION_TASKS
from app.core.config import Settings, get_settings
from app.core.errors import install_error_handling
from app.db.session import SessionFactory, engine


class _PublicRepository:
    async def get_public(self, product_id: UUID):
        async with SessionFactory() as session:
            return await ProductRepository(session).get_public(product_id)


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()
    upload_root = Path(resolved_settings.upload_root)
    upload_root.mkdir(mode=0o700, parents=True, exist_ok=True)
    redis = Redis.from_url(
        resolved_settings.redis_url,
        decode_responses=True,
        socket_timeout=resolved_settings.redis_timeout_seconds,
        socket_connect_timeout=resolved_settings.redis_timeout_seconds,
    )
    cache = ProductCache(
        redis,
        base_ttl_seconds=resolved_settings.cache_ttl_seconds,
        jitter_seconds=resolved_settings.cache_ttl_jitter_seconds,
        negative_ttl_seconds=resolved_settings.negative_cache_ttl_seconds,
        lock_ttl_ms=resolved_settings.cache_lock_ttl_ms,
    )

    @asynccontextmanager
    async def lifespan(_application: FastAPI):
        yield
        if _INVALIDATION_TASKS:
            await asyncio.gather(*tuple(_INVALIDATION_TASKS), return_exceptions=True)
        await redis.aclose()
        await engine.dispose()

    application = FastAPI(title="StockStack Product Management", lifespan=lifespan)
    application.state.settings = resolved_settings
    application.state.product_cache = cache
    application.state.public_product_service = PublicProductService(
        _PublicRepository(),
        cache,
        db_concurrency=resolved_settings.db_fallback_concurrency_limit,
        db_fallback_wait_ms=resolved_settings.db_fallback_wait_ms,
        db_query_timeout_ms=resolved_settings.db_query_timeout_ms,
        wait_budget_ms=resolved_settings.cache_wait_budget_ms,
        redis_timeout_seconds=resolved_settings.redis_timeout_seconds,
    )
    application.dependency_overrides[get_settings] = lambda: application.state.settings
    install_error_handling(application)
    application.include_router(auth_router)
    application.include_router(catalog_router)
    application.include_router(public_router)
    application.mount(
        "/uploads",
        StaticFiles(directory=upload_root, check_dir=True),
        name="uploads",
    )

    @application.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @application.get("/metrics", include_in_schema=False)
    def metrics() -> Response:
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    return application


app = create_app()
