from __future__ import annotations

import asyncio
from collections.abc import Iterable
from typing import Any
from uuid import UUID

import nh3
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.catalog.domain import (
    IllegalProductStatusTransition,
    ProductStatus,
    ProductType,
)
from app.catalog.field_schema import validate_attributes
from app.catalog.models import ProductFieldSchemaModel, ProductModel
from app.catalog.repository import (
    BatchUpdateError,
    DuplicateProductId,
    InvalidImages,
    NotFound,
    ProductRepository,
    SchemaConflict,
    VersionConflict,
)
from app.catalog.schemas import (
    ProductBatchStatusUpdate,
    ProductCreate,
    ProductPage,
    ProductUpdate,
    ProductView,
)
from app.core.errors import AppError
from app.core.metrics import DEPENDENCY_ERRORS

_INVALIDATION_TASKS: set[asyncio.Task[None]] = set()

_SERVICE_ERRORS = (
    BatchUpdateError,
    DuplicateProductId,
    IllegalProductStatusTransition,
    IntegrityError,
    InvalidImages,
    NotFound,
    SchemaConflict,
    VersionConflict,
)


def _field_errors(errors: Iterable[Any]) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for error in errors:
        path = ".".join(map(str, error.path)) or "attributes"
        result.setdefault(path, []).append(error.message)
    return result


def _view(product: ProductModel) -> ProductView:
    product.images.sort(key=lambda image: (image.sort_order, str(image.id)))
    return ProductView.model_validate(product)


def _raise_repository_error(error: Exception) -> None:
    if isinstance(error, NotFound):
        raise AppError("product_not_found", "Product not found", 404) from error
    if isinstance(error, VersionConflict):
        raise AppError("version_conflict", "Product version conflict", 409) from error
    if isinstance(error, (IllegalProductStatusTransition, DuplicateProductId)):
        raise AppError("status_conflict", "Product status operation conflicts", 409) from error
    if isinstance(error, BatchUpdateError):
        raise AppError("status_conflict", "Product status operation conflicts", 409) from error
    if isinstance(error, (SchemaConflict, InvalidImages, IntegrityError)):
        raise AppError("product_conflict", "Product data conflicts", 409) from error
    raise error


class ProductService:
    def __init__(self, session: AsyncSession, cache: Any | None = None) -> None:
        self.session = session
        self.repository = ProductRepository(session)
        self.cache = cache

    async def _invalidate(self, *product_ids: UUID) -> None:
        if self.cache is None:
            return
        for product_id in product_ids:
            try:
                await asyncio.wait_for(self.cache.delete(product_id), 0.2)
            except Exception:  # noqa: BLE001 -- writes remain committed if Redis fails
                DEPENDENCY_ERRORS.labels("redis", "cache_invalidate").inc()
                task = asyncio.create_task(self._retry_invalidation(product_id))
                _INVALIDATION_TASKS.add(task)
                task.add_done_callback(_INVALIDATION_TASKS.discard)

    async def _retry_invalidation(self, product_id: UUID) -> None:
        for _attempt in range(2):
            await asyncio.sleep(0.05)
            try:
                await asyncio.wait_for(self.cache.delete(product_id), 0.2)
                return
            except Exception:  # noqa: BLE001 -- bounded best-effort retry
                DEPENDENCY_ERRORS.labels("redis", "cache_invalidate_retry").inc()

    async def active_schema(self, product_type: ProductType) -> ProductFieldSchemaModel:
        schema = await self.repository.get_active_schema(product_type)
        if schema is None:
            raise AppError("schema_not_found", "Active product schema not found", 404)
        return schema

    async def schema_version(
        self, product_type: ProductType, version: int
    ) -> ProductFieldSchemaModel:
        schema = await self.repository.get_schema_version(product_type, version)
        if schema is None:
            raise AppError("schema_not_found", "Product schema version not found", 404)
        return schema

    async def create(self, payload: ProductCreate) -> ProductView:
        active_schema = await self.repository.get_active_schema(payload.product_type)
        if active_schema is None or active_schema.version != payload.schema_version:
            raise AppError(
                "schema_version_conflict", "Active schema version does not match", 409
            )
        errors = validate_attributes(active_schema.schema, payload.attributes)
        if errors:
            raise AppError(
                "invalid_product_attributes",
                "Product attributes are invalid",
                400,
                _field_errors(errors),
            )
        values = payload.model_dump(exclude={"images"})
        values["description_html"] = nh3.clean(payload.description_html)
        try:
            product = await self.repository.create_with_images(
                values, [image.model_dump() for image in payload.images]
            )
            await self.session.commit()
            await self._invalidate(product.id)
            return _view(product)
        except _SERVICE_ERRORS as error:
            await self.session.rollback()
            _raise_repository_error(error)

    async def list(
        self,
        *,
        query: str | None,
        product_type: ProductType | None,
        status: ProductStatus | None,
        page: int,
        page_size: int,
    ) -> ProductPage:
        items, total = await self.repository.list(
            query=query,
            product_type=product_type,
            status=status,
            page=page,
            page_size=page_size,
        )
        return ProductPage(
            items=[_view(item) for item in items],
            total=total,
            page=page,
            page_size=page_size,
        )

    async def detail(self, product_id: UUID) -> ProductView:
        product = await self.repository.get_detail(product_id)
        if product is None:
            raise AppError("product_not_found", "Product not found", 404)
        return _view(product)

    async def update(self, product_id: UUID, payload: ProductUpdate) -> ProductView:
        existing = await self.repository.get_detail(product_id)
        if existing is None:
            raise AppError("product_not_found", "Product not found", 404)
        schema = await self.repository.get_schema_version(
            ProductType(existing.product_type), existing.schema_version
        )
        if schema is None or payload.schema_version != existing.schema_version:
            raise AppError(
                "schema_version_conflict", "Product schema version does not match", 409
            )
        errors = validate_attributes(schema.schema, payload.attributes)
        if errors:
            raise AppError(
                "invalid_product_attributes",
                "Product attributes are invalid",
                400,
                _field_errors(errors),
            )
        values = payload.model_dump(
            exclude={"version", "images", "schema_version", "status"}
        )
        values["description_html"] = nh3.clean(payload.description_html)
        try:
            product = await self.repository.update(
                product_id, expected_version=payload.version, values=values
            )
            await self.repository.replace_images(
                product, [image.model_dump() for image in payload.images]
            )
            await self.session.commit()
            await self._invalidate(product_id)
            return _view(product)
        except _SERVICE_ERRORS as error:
            await self.session.rollback()
            _raise_repository_error(error)

    async def update_status(
        self, product_id: UUID, version: int, target_status: ProductStatus
    ) -> ProductView:
        try:
            products = await self.repository.batch_update_status(
                [(product_id, version)], target_status
            )
            await self.session.commit()
            await self._invalidate(product_id)
            product = await self.repository.get_detail(products[0].id)
            assert product is not None
            return _view(product)
        except _SERVICE_ERRORS as error:
            await self.session.rollback()
            _raise_repository_error(error)

    async def batch_status(self, payload: ProductBatchStatusUpdate) -> list[ProductView]:
        try:
            products = await self.repository.batch_update_status(
                [(item.product_id, item.version) for item in payload.product_ids],
                ProductStatus(payload.target_status),
            )
            await self.session.commit()
            await self._invalidate(*(product.id for product in products))
            detailed = [await self.repository.get_detail(product.id) for product in products]
            return [_view(product) for product in detailed if product is not None]
        except BatchUpdateError as error:
            await self.session.rollback()
            raise AppError(
                "batch_status_conflict",
                "Batch status update conflicts",
                409,
                {
                    str(product_id): [reason]
                    for product_id, reason in error.failures.items()
                },
            ) from error
        except _SERVICE_ERRORS as error:
            await self.session.rollback()
            _raise_repository_error(error)
