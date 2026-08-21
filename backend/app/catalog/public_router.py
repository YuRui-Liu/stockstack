from __future__ import annotations

import asyncio
import time
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request

from app.catalog.public_service import PublicProductService
from app.catalog.schemas import ProductView
from app.core.errors import AppError
from app.core.metrics import (
    DEPENDENCY_ERRORS,
    PUBLIC_LATENCY,
    PUBLIC_REQUESTS,
    RATE_LIMIT_RESULTS,
)

router = APIRouter(prefix="/api/v1/public", tags=["public-catalog"])


def get_public_service(request: Request) -> PublicProductService:
    return request.app.state.public_product_service


def _uuid7(value: str) -> UUID:
    try:
        parsed = UUID(value)
    except ValueError as error:
        raise AppError("validation_error", "Product id must be a UUIDv7", 400) from error
    if parsed.version != 7:
        raise AppError("validation_error", "Product id must be a UUIDv7", 400)
    return parsed


async def enforce_rate_limit(request: Request) -> None:
    settings = request.app.state.settings
    cache = request.app.state.product_cache
    client_ip = request.client.host if request.client else "unknown"
    try:
        allowed, _count = await asyncio.wait_for(
            cache.rate_limit(
                client_ip,
                limit=settings.rate_limit_requests,
                window_seconds=settings.rate_limit_window_seconds,
            ),
            settings.redis_timeout_seconds,
        )
    except Exception:  # noqa: BLE001 -- rate limiting is deliberately fail-open
        RATE_LIMIT_RESULTS.labels("fail_open").inc()
        DEPENDENCY_ERRORS.labels("redis", "rate_limit").inc()
        return
    if not allowed:
        RATE_LIMIT_RESULTS.labels("rejected").inc()
        raise HTTPException(
            status_code=429,
            detail="Too many requests",
            headers={"Retry-After": str(settings.rate_limit_window_seconds)},
        )
    RATE_LIMIT_RESULTS.labels("allowed").inc()


@router.get(
    "/products/{product_id}",
    response_model=ProductView,
    dependencies=[Depends(enforce_rate_limit)],
)
async def public_product_detail(
    product_id: str,
    service: Annotated[PublicProductService, Depends(get_public_service)],
) -> ProductView:
    started = time.monotonic()
    try:
        result = await service.detail(_uuid7(product_id))
        PUBLIC_REQUESTS.labels("ok").inc()
        return result
    except AppError as error:
        PUBLIC_REQUESTS.labels(str(error.status_code)).inc()
        raise
    finally:
        PUBLIC_LATENCY.observe(time.monotonic() - started)
