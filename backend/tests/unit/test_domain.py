from copy import deepcopy
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.catalog.domain import ProductStatus, assert_transition
from app.catalog.schemas import (
    ProductBatchStatusUpdate,
    ProductCreate,
    ProductImageInput,
    ProductStatusUpdate,
    ProductUpdate,
    ProductView,
)


@pytest.mark.parametrize(
    "source,target",
    [
        (ProductStatus.OFF_SHELF, ProductStatus.ON_SHELF),
        (ProductStatus.ON_SHELF, ProductStatus.OFF_SHELF),
        (ProductStatus.ON_SHELF, ProductStatus.PENALIZED),
        (ProductStatus.OFF_SHELF, ProductStatus.PENALIZED),
    ],
)
def test_allowed_transitions(source, target) -> None:
    assert_transition(source, target)


def test_penalized_product_cannot_transition() -> None:
    for target in (ProductStatus.OFF_SHELF, ProductStatus.ON_SHELF):
        with pytest.raises(ValueError, match="illegal product status transition"):
            assert_transition(ProductStatus.PENALIZED, target)


@pytest.mark.parametrize("status", list(ProductStatus))
def test_same_status_transition_is_illegal(status: ProductStatus) -> None:
    with pytest.raises(ValueError, match="illegal product status transition"):
        assert_transition(status, status)


def test_request_schema_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        ProductStatusUpdate(target_status=ProductStatus.ON_SHELF, version=1, typo=True)


def test_product_update_requires_version_and_forbids_product_type() -> None:
    with pytest.raises(ValidationError):
        ProductUpdate(title="新标题")
    with pytest.raises(ValidationError, match="product_type"):
        ProductUpdate(version=1, product_type="virtual")


def valid_product_create() -> dict:
    return {
        "title": "背包",
        "short_title": "30L 背包",
        "description_html": "<p>黑色</p>",
        "price_amount": Decimal("199.90"),
        "stock": 10,
        "product_type": "physical",
        "status": "off_shelf",
        "delivery_method": "logistics",
        "return_rule": "seven_days",
        "attributes": {"weight_kg": 1.2},
        "schema_version": 1,
        "images": [
            {
                "kind": "main",
                "url": "https://cdn.example.com/main.webp",
                "size_bytes": 2 * 1024 * 1024,
                "mime_type": "image/webp",
            }
        ],
    }


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("title", "x"),
        ("title", "x" * 60),
        ("short_title", "x" * 120),
        ("description_html", "x" * 2000),
        ("price_amount", Decimal(0)),
        ("stock", 0),
        ("schema_version", 1),
    ],
)
def test_product_create_accepts_public_field_boundaries(field: str, value: object) -> None:
    payload = valid_product_create()
    payload[field] = value

    ProductCreate.model_validate(payload)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("title", ""),
        ("title", "x" * 61),
        ("short_title", "x" * 121),
        ("description_html", "x" * 2001),
        ("price_amount", Decimal("-0.01")),
        ("stock", -1),
        ("stock", 1.5),
        ("product_type", "service"),
        ("status", "draft"),
        ("delivery_method", "teleport"),
        ("return_rule", "always"),
        ("schema_version", 0),
    ],
)
def test_product_create_rejects_invalid_public_fields(field: str, value: object) -> None:
    payload = valid_product_create()
    payload[field] = value

    with pytest.raises(ValidationError):
        ProductCreate.model_validate(payload)


@pytest.mark.parametrize(
    "field",
    [
        "title",
        "price_amount",
        "stock",
        "product_type",
        "status",
        "delivery_method",
        "return_rule",
        "attributes",
        "schema_version",
        "images",
    ],
)
def test_product_create_rejects_missing_required_fields(field: str) -> None:
    missing = valid_product_create()
    missing.pop(field)
    with pytest.raises(ValidationError, match=field):
        ProductCreate.model_validate(missing)


def test_product_create_rejects_extra_fields() -> None:
    extra = valid_product_create()
    extra["typo"] = True
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        ProductCreate.model_validate(extra)


def test_product_image_input_enforces_metadata_boundaries() -> None:
    ProductImageInput(
        kind="gallery", url="https://cdn.example.com/a.jpg", size_bytes=1, mime_type="image/jpeg"
    )
    for patch in (
        {"kind": "thumbnail"},
        {"url": ""},
        {"size_bytes": 0},
        {"size_bytes": 2 * 1024 * 1024 + 1},
        {"mime_type": "image/gif"},
        {"unexpected": True},
    ):
        image = {
            "kind": "main",
            "url": "https://cdn.example.com/a.png",
            "size_bytes": 1,
            "mime_type": "image/png",
        }
        image.update(patch)
        with pytest.raises(ValidationError):
            ProductImageInput.model_validate(image)


@pytest.mark.parametrize(
    "images",
    [
        [],
        [{"kind": "gallery", "url": "x", "size_bytes": 1, "mime_type": "image/png"}],
        [
            {"kind": "main", "url": "x", "size_bytes": 1, "mime_type": "image/png"},
            {"kind": "main", "url": "y", "size_bytes": 1, "mime_type": "image/png"},
        ],
        [
            {"kind": "main", "url": "main", "size_bytes": 1, "mime_type": "image/png"},
            *[
                {"kind": "gallery", "url": str(index), "size_bytes": 1, "mime_type": "image/png"}
                for index in range(6)
            ],
        ],
    ],
)
def test_product_create_rejects_invalid_image_collections(images: list[dict]) -> None:
    payload = valid_product_create()
    payload["images"] = images
    with pytest.raises(ValidationError, match="images"):
        ProductCreate.model_validate(payload)


def test_product_create_accepts_five_gallery_images() -> None:
    payload = valid_product_create()
    payload["images"].extend(
        {
            "kind": "gallery",
            "url": f"https://cdn.example.com/{index}.png",
            "size_bytes": 1,
            "mime_type": "image/png",
        }
        for index in range(5)
    )

    ProductCreate.model_validate(payload)


def test_product_update_requires_valid_complete_image_collection() -> None:
    payload = deepcopy(valid_product_create())
    payload.pop("product_type")
    payload["version"] = 1
    ProductUpdate.model_validate(payload)

    payload["images"] = []
    with pytest.raises(ValidationError, match="images"):
        ProductUpdate.model_validate(payload)


@pytest.mark.parametrize(
    "field",
    [
        "version",
        "title",
        "short_title",
        "description_html",
        "price_amount",
        "stock",
        "status",
        "delivery_method",
        "return_rule",
        "attributes",
        "schema_version",
        "images",
    ],
)
def test_product_update_requires_every_complete_edit_field(field: str) -> None:
    payload = deepcopy(valid_product_create())
    payload.pop("product_type")
    payload["version"] = 1
    payload.pop(field)

    with pytest.raises(ValidationError, match=field):
        ProductUpdate.model_validate(payload)


def test_batch_status_requires_items_and_forbids_penalized() -> None:
    valid_item = {
        "product_id": "123e4567-e89b-12d3-a456-426614174000",
        "version": 1,
    }
    ProductBatchStatusUpdate(product_ids=[valid_item], target_status="on_shelf")
    with pytest.raises(ValidationError):
        ProductBatchStatusUpdate(product_ids=[], target_status="on_shelf")
    with pytest.raises(ValidationError, match="target_status"):
        ProductBatchStatusUpdate(
            product_ids=[
                {"product_id": "123e4567-e89b-12d3-a456-426614174000", "version": 1}
            ],
            target_status="penalized",
        )
    with pytest.raises(ValidationError, match="version"):
        ProductBatchStatusUpdate(
            product_ids=[
                {"product_id": "123e4567-e89b-12d3-a456-426614174000"}
            ],
            target_status="on_shelf",
        )
    with pytest.raises(ValidationError, match="version"):
        ProductBatchStatusUpdate(
            product_ids=[{**valid_item, "version": 0}],
            target_status="off_shelf",
        )


def test_product_view_serializes_money_as_string() -> None:
    product = ProductView.model_validate(
        {
            "id": "123e4567-e89b-12d3-a456-426614174000",
            "title": "背包",
            "short_title": "30L 背包",
            "description_html": "<p>黑色</p>",
            "price_amount": "199.90",
            "stock": 10,
            "product_type": "physical",
            "status": "on_shelf",
            "delivery_method": "logistics",
            "return_rule": "seven_days",
            "attributes": {},
            "schema_version": 1,
            "version": 1,
            "created_at": "2026-08-21T00:00:00Z",
            "updated_at": "2026-08-21T00:00:00Z",
        }
    )

    assert product.model_dump(mode="json")["price_amount"] == "199.90"
