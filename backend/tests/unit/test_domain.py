import pytest
from pydantic import ValidationError

from app.catalog.domain import ProductStatus, assert_transition
from app.catalog.schemas import (
    ProductBatchStatusUpdate,
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
    with pytest.raises(ValueError, match="illegal product status transition"):
        assert_transition(ProductStatus.PENALIZED, ProductStatus.OFF_SHELF)


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


def test_batch_status_requires_items_and_forbids_penalized() -> None:
    with pytest.raises(ValidationError):
        ProductBatchStatusUpdate(product_ids=[], target_status="on_shelf")
    with pytest.raises(ValidationError, match="target_status"):
        ProductBatchStatusUpdate(
            product_ids=[
                {"product_id": "123e4567-e89b-12d3-a456-426614174000", "version": 1}
            ],
            target_status="penalized",
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
