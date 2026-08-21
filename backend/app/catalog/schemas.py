from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from app.catalog.domain import DeliveryMethod, ProductStatus, ProductType, ReturnRule

Money = Annotated[Decimal, Field(ge=0)]


class StrictRequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ProductImageInput(StrictRequestModel):
    url: str = Field(min_length=1)
    alt_text: str = Field(default="", max_length=200)
    sort_order: int = Field(default=0, ge=0)


class ProductCreate(StrictRequestModel):
    title: str = Field(min_length=1, max_length=60)
    short_title: str = Field(default="", max_length=120)
    description_html: str = Field(default="", max_length=2000)
    price_amount: Money
    stock: int = Field(ge=0)
    product_type: ProductType
    status: ProductStatus
    delivery_method: DeliveryMethod
    return_rule: ReturnRule
    attributes: dict[str, Any]
    schema_version: int = Field(ge=1)
    images: list[ProductImageInput] = Field(default_factory=list)


class ProductUpdate(StrictRequestModel):
    version: int = Field(ge=1)
    title: str | None = Field(default=None, min_length=1, max_length=60)
    short_title: str | None = Field(default=None, max_length=120)
    description_html: str | None = Field(default=None, max_length=2000)
    price_amount: Money | None = None
    stock: int | None = Field(default=None, ge=0)
    status: ProductStatus | None = None
    delivery_method: DeliveryMethod | None = None
    return_rule: ReturnRule | None = None
    attributes: dict[str, Any] | None = None
    schema_version: int | None = Field(default=None, ge=1)
    images: list[ProductImageInput] | None = None


class ProductStatusUpdate(StrictRequestModel):
    target_status: ProductStatus
    version: int = Field(ge=1)


class ProductVersionRef(StrictRequestModel):
    product_id: UUID
    version: int = Field(ge=1)


class ProductBatchStatusUpdate(StrictRequestModel):
    product_ids: Annotated[list[ProductVersionRef], Field(min_length=1)]
    target_status: Literal[ProductStatus.ON_SHELF, ProductStatus.OFF_SHELF]


class ProductView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    short_title: str
    description_html: str
    price_amount: Decimal
    stock: int
    product_type: ProductType
    status: ProductStatus
    delivery_method: DeliveryMethod
    return_rule: ReturnRule
    attributes: dict[str, Any]
    schema_version: int
    images: list[ProductImageInput] = Field(default_factory=list)
    version: int
    created_at: datetime
    updated_at: datetime

    @field_serializer("price_amount")
    def serialize_price_amount(self, value: Decimal) -> str:
        return str(value)


class ProductPage(BaseModel):
    items: list[ProductView]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)
