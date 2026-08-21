from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any
from uuid import UUID

from sqlalchemy import String, cast, delete, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.catalog.domain import (
    IllegalProductStatusTransition,
    ProductStatus,
    ProductType,
    assert_transition,
)
from app.catalog.models import ProductFieldSchemaModel, ProductImageModel, ProductModel


class RepositoryError(Exception):
    pass


class NotFound(RepositoryError):
    pass


class VersionConflict(RepositoryError):
    pass


class SchemaConflict(RepositoryError):
    pass


class DuplicateProductId(RepositoryError):
    pass


class BatchUpdateError(RepositoryError):
    def __init__(self, failures: Mapping[UUID, str]) -> None:
        super().__init__("batch status update validation failed")
        self.failures = dict(failures)


class InvalidImages(RepositoryError):
    pass


def _stable_value(value: Any) -> Any:
    return value.value if hasattr(value, "value") else value


class ProductRepository:
    """Persistence operations; callers own commit/rollback transaction boundaries."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_active_schema(
        self, product_type: ProductType
    ) -> ProductFieldSchemaModel | None:
        return await self.session.scalar(
            select(ProductFieldSchemaModel).where(
                ProductFieldSchemaModel.product_type == product_type.value,
                ProductFieldSchemaModel.active.is_(True),
            )
        )

    async def get_schema_version(
        self, product_type: ProductType, version: int
    ) -> ProductFieldSchemaModel | None:
        return await self.session.scalar(
            select(ProductFieldSchemaModel).where(
                ProductFieldSchemaModel.product_type == product_type.value,
                ProductFieldSchemaModel.version == version,
            )
        )

    async def get_detail(self, product_id: UUID) -> ProductModel | None:
        return await self.session.scalar(
            select(ProductModel)
            .where(ProductModel.id == product_id)
            .options(selectinload(ProductModel.images))
        )

    async def get_public(self, product_id: UUID) -> ProductModel | None:
        return await self.session.scalar(
            select(ProductModel)
            .where(
                ProductModel.id == product_id,
                ProductModel.status == ProductStatus.ON_SHELF.value,
            )
            .options(selectinload(ProductModel.images))
        )

    async def list(
        self,
        *,
        query: str | None = None,
        product_type: ProductType | None = None,
        status: ProductStatus | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[ProductModel], int]:
        filters = []
        normalized_query = query.strip() if query else ""
        if normalized_query:
            filters.append(
                or_(
                    ProductModel.title.icontains(normalized_query, autoescape=True),
                    ProductModel.short_title.icontains(normalized_query, autoescape=True),
                    cast(ProductModel.id, String).icontains(normalized_query, autoescape=True),
                )
            )
        if product_type is not None:
            filters.append(ProductModel.product_type == product_type.value)
        if status is not None:
            filters.append(ProductModel.status == status.value)

        total = await self.session.scalar(
            select(func.count()).select_from(ProductModel).where(*filters)
        )
        items = (
            (
                await self.session.execute(
                    select(ProductModel)
                    .where(*filters)
                    .options(selectinload(ProductModel.images))
                    .order_by(ProductModel.updated_at.desc(), ProductModel.id.desc())
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                )
            )
            .scalars()
            .all()
        )
        return list(items), int(total or 0)

    async def create_schema(
        self,
        product_type: ProductType,
        version: int,
        schema: dict[str, Any],
        *,
        active: bool = True,
    ) -> ProductFieldSchemaModel:
        model = ProductFieldSchemaModel(
            product_type=product_type.value,
            version=version,
            schema=schema,
            active=active,
        )
        try:
            async with self.session.begin_nested():
                self.session.add(model)
                await self.session.flush()
        except IntegrityError as error:
            raise SchemaConflict(
                f"schema conflicts for {product_type.value} version {version}"
            ) from error
        return model

    async def create_with_images(
        self, product_values: Mapping[str, Any], images: Iterable[Mapping[str, Any]]
    ) -> ProductModel:
        image_values = list(images)
        main_count = sum(_stable_value(image["kind"]) == "main" for image in image_values)
        gallery_count = sum(
            _stable_value(image["kind"]) == "gallery" for image in image_values
        )
        if main_count != 1 or gallery_count > 5:
            raise InvalidImages("exactly one main and at most five gallery images required")
        normalized = {key: _stable_value(value) for key, value in product_values.items()}
        product = ProductModel(**normalized)
        self.session.add(product)
        await self.session.flush()
        for image in image_values:
            self.session.add(
                ProductImageModel(
                    product_id=product.id,
                    **{key: _stable_value(value) for key, value in image.items()},
                )
            )
        await self.session.flush()
        await self.session.refresh(product, attribute_names=["images"])
        return product

    async def update(
        self, product_id: UUID, *, expected_version: int, values: Mapping[str, Any]
    ) -> ProductModel:
        normalized = {key: _stable_value(value) for key, value in values.items()}
        statement = (
            update(ProductModel)
            .where(ProductModel.id == product_id, ProductModel.version == expected_version)
            .values(**normalized, version=ProductModel.version + 1)
            .returning(ProductModel)
        )
        product = (await self.session.execute(statement)).scalar_one_or_none()
        if product is not None:
            return product
        exists = await self.session.scalar(
            select(ProductModel.id).where(ProductModel.id == product_id)
        )
        if exists is None:
            raise NotFound(f"product {product_id} not found")
        raise VersionConflict(f"product {product_id} version is no longer {expected_version}")

    async def replace_images(
        self, product: ProductModel, images: Iterable[Mapping[str, Any]]
    ) -> ProductModel:
        image_values = list(images)
        main_count = sum(_stable_value(image["kind"]) == "main" for image in image_values)
        gallery_count = sum(
            _stable_value(image["kind"]) == "gallery" for image in image_values
        )
        if main_count != 1 or gallery_count > 5:
            raise InvalidImages("exactly one main and at most five gallery images required")
        await self.session.execute(
            delete(ProductImageModel).where(ProductImageModel.product_id == product.id)
        )
        for image in image_values:
            self.session.add(
                ProductImageModel(
                    product_id=product.id,
                    **{key: _stable_value(value) for key, value in image.items()},
                )
            )
        await self.session.flush()
        await self.session.refresh(product, attribute_names=["images"])
        return product

    async def batch_update_status(
        self,
        product_versions: Iterable[tuple[UUID, int]],
        target_status: ProductStatus,
    ) -> list[ProductModel]:
        materialized = list(product_versions)
        seen: set[UUID] = set()
        failures: dict[UUID, str] = {}
        for product_id, _version in materialized:
            if product_id in seen:
                failures[product_id] = "duplicate_product_id"
            seen.add(product_id)
        expected = dict(materialized)
        rows = (
            await self.session.execute(
                select(ProductModel)
                .where(ProductModel.id.in_(expected))
                .order_by(ProductModel.id)
                .with_for_update()
            )
        ).scalars().all()
        found = {row.id for row in rows}
        missing = set(expected) - found
        for product_id in missing:
            failures.setdefault(product_id, "not_found")
        for row in rows:
            if row.id in failures:
                continue
            if row.version != expected[row.id]:
                failures[row.id] = "version_conflict"
                continue
            try:
                assert_transition(ProductStatus(row.status), target_status)
            except IllegalProductStatusTransition:
                failures[row.id] = "illegal_transition"
        if failures:
            raise BatchUpdateError(failures)
        for row in rows:
            row.status = target_status.value
            row.version += 1
        await self.session.flush()
        return rows
