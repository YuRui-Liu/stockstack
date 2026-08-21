from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.catalog.domain import ProductStatus, ProductType
from app.catalog.models import ProductFieldSchemaModel, ProductImageModel, ProductModel
from app.catalog.repository import (
    BatchUpdateError,
    ProductRepository,
    SchemaConflict,
    VersionConflict,
)


def product_values(title: str = "Demo product") -> dict:
    return {
        "title": title,
        "short_title": "Demo",
        "description_html": "<p>Demo</p>",
        "price_amount": Decimal("19.90"),
        "stock": 3,
        "product_type": ProductType.PHYSICAL,
        "status": ProductStatus.OFF_SHELF,
        "delivery_method": "ems",
        "return_rule": "seven_days",
        "attributes": {"weight_kg": 1},
        "schema_version": 1,
    }


def image_values() -> list[dict]:
    return [
        {
            "kind": "main",
            "url": "https://assets.example/main.webp",
            "sort_order": 0,
            "size_bytes": 1024,
            "mime_type": "image/webp",
        }
    ]


@pytest.mark.asyncio
async def test_product_list_searches_title_and_id_by_contained_fragment(db_session):
    repository = ProductRepository(db_session)
    first = await repository.create_with_images(
        product_values("红色保暖外套"), image_values()
    )
    await repository.create_with_images(product_values("夏季短袖"), image_values())
    await db_session.commit()

    title_items, title_total = await repository.list(query="保暖")
    id_items, id_total = await repository.list(query=str(first.id)[9:17])

    assert title_total == 1
    assert [item.id for item in title_items] == [first.id]
    assert id_total == 1
    assert [item.id for item in id_items] == [first.id]


@pytest.mark.asyncio
async def test_optimistic_update_rejects_a_reused_version(db_session):
    repository = ProductRepository(db_session)
    product = await repository.create_with_images(product_values(), image_values())
    await db_session.commit()

    updated = await repository.update(
        product.id, expected_version=1, values={"title": "First edit"}
    )
    await db_session.commit()
    assert updated.version == 2

    with pytest.raises(VersionConflict):
        await repository.update(
            product.id, expected_version=1, values={"title": "Stale edit"}
        )


@pytest.mark.asyncio
async def test_schema_version_and_active_template_are_unique(db_session):
    repository = ProductRepository(db_session)
    await repository.create_schema(ProductType.PHYSICAL, 1, {"type": "object"})
    await db_session.commit()

    with pytest.raises(SchemaConflict):
        await repository.create_schema(
            ProductType.PHYSICAL, 1, {"type": "object"}, active=False
        )
    await db_session.rollback()

    db_session.add(
        ProductFieldSchemaModel(
            product_type=ProductType.PHYSICAL.value,
            version=2,
            schema={"type": "object"},
            active=True,
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.commit()


@pytest.mark.asyncio
async def test_product_and_images_are_rolled_back_together(db_session):
    repository = ProductRepository(db_session)
    invalid_images = image_values() + [
        {
            "kind": "gallery",
            "url": "https://assets.example/broken.webp",
            "sort_order": 1,
            "size_bytes": 0,
            "mime_type": "image/webp",
        }
    ]

    with pytest.raises(IntegrityError):
        async with db_session.begin():
            await repository.create_with_images(product_values(), invalid_images)

    count = await db_session.scalar(select(func.count()).select_from(ProductModel))
    assert count == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["version_conflict", "illegal_transition"])
async def test_batch_status_update_is_all_or_nothing(db_session, failure):
    repository = ProductRepository(db_session)
    first_values = product_values("First")
    if failure == "illegal_transition":
        first_values["status"] = ProductStatus.PENALIZED
    first = await repository.create_with_images(first_values, image_values())
    second = await repository.create_with_images(
        product_values("Second"), image_values()
    )
    await db_session.commit()

    versions = [(first.id, 1), (second.id, 99 if failure == "version_conflict" else 1)]
    with pytest.raises(BatchUpdateError) as captured:
        async with db_session.begin():
            await repository.batch_update_status(versions, ProductStatus.ON_SHELF)
    failed_id = second.id if failure == "version_conflict" else first.id
    assert captured.value.failures == {failed_id: failure}

    statuses = (
        (
            await db_session.execute(
                select(ProductModel.status).order_by(ProductModel.title)
            )
        )
        .scalars()
        .all()
    )
    expected_statuses = (
        [ProductStatus.PENALIZED.value, ProductStatus.OFF_SHELF.value]
        if failure == "illegal_transition"
        else [ProductStatus.OFF_SHELF.value] * 2
    )
    assert statuses == expected_statuses
    assert (
        await db_session.scalar(select(func.count()).select_from(ProductImageModel))
        == 2
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("duplicate_version", [1, 2])
async def test_batch_status_update_rejects_duplicate_product_ids(
    db_session, duplicate_version
):
    repository = ProductRepository(db_session)
    product = await repository.create_with_images(product_values(), image_values())
    await db_session.commit()

    with pytest.raises(BatchUpdateError) as captured:
        async with db_session.begin():
            await repository.batch_update_status(
                [(product.id, 1), (product.id, duplicate_version)],
                ProductStatus.ON_SHELF,
            )
    assert captured.value.failures == {product.id: "duplicate_product_id"}

    await db_session.refresh(product)
    assert product.status == ProductStatus.OFF_SHELF.value
    assert product.version == 1


@pytest.mark.asyncio
async def test_product_attributes_in_place_change_is_persisted(db_session):
    repository = ProductRepository(db_session)
    product = await repository.create_with_images(product_values(), image_values())
    await db_session.commit()

    product.attributes["weight_kg"] = 2
    await db_session.commit()
    product_id = product.id
    db_session.expunge_all()

    reloaded = await db_session.get(ProductModel, product_id)
    assert reloaded is not None
    assert reloaded.attributes == {"weight_kg": 2}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status,visible",
    [
        (ProductStatus.ON_SHELF, True),
        (ProductStatus.OFF_SHELF, False),
        (ProductStatus.PENALIZED, False),
    ],
)
async def test_get_public_only_returns_on_shelf_products(db_session, status, visible):
    repository = ProductRepository(db_session)
    values = product_values()
    values["status"] = status
    product = await repository.create_with_images(values, image_values())
    await db_session.commit()

    found = await repository.get_public(product.id)

    assert (found is not None) is visible
