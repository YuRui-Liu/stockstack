from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_serializer, model_validator

from app.catalog.domain import DeliveryMethod, ProductStatus, ProductType, ReturnRule

Money = Annotated[Decimal, Field(ge=0)]


class StrictRequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ProductImageInput(StrictRequestModel):
    kind: Literal["main", "gallery"]
    url: str = Field(min_length=1)
    size_bytes: int = Field(ge=1, le=2 * 1024 * 1024)
    mime_type: Literal["image/jpeg", "image/png", "image/webp"]


def _assert_image_collection(images: list[ProductImageInput]) -> None:
    main_count = sum(image.kind == "main" for image in images)
    gallery_count = sum(image.kind == "gallery" for image in images)
    if main_count != 1:
        raise ValueError("images must contain exactly one main image")
    if gallery_count > 5:
        raise ValueError("images must contain at most five gallery images")


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
    images: list[ProductImageInput]

    @model_validator(mode="after")
    def validate_images(self) -> "ProductCreate":
        _assert_image_collection(self.images)
        return self


class ProductUpdate(StrictRequestModel):
    version: int = Field(ge=1)
    title: str = Field(min_length=1, max_length=60)
    short_title: str = Field(max_length=120)
    description_html: str = Field(max_length=2000)
    price_amount: Money
    stock: int = Field(ge=0)
    status: ProductStatus
    delivery_method: DeliveryMethod
    return_rule: ReturnRule
    attributes: dict[str, Any]
    schema_version: int = Field(ge=1)
    images: list[ProductImageInput]

    @model_validator(mode="after")
    def validate_images(self) -> "ProductUpdate":
        _assert_image_collection(self.images)
        return self


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
