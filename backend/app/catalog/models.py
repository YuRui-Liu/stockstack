from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from uuid6 import uuid7


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class ProductModel(TimestampMixin, Base):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint("price_amount >= 0", name="ck_products_price_nonnegative"),
        CheckConstraint("stock >= 0", name="ck_products_stock_nonnegative"),
        CheckConstraint("version >= 1", name="ck_products_version_positive"),
        Index(
            "ix_products_listing",
            "status",
            "product_type",
            text("updated_at DESC"),
            text("id DESC"),
        ),
        Index(
            "ix_products_title_search",
            text("to_tsvector('simple', title)"),
            postgresql_using="gin",
        ),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid7)
    title: Mapped[str] = mapped_column(String(60), nullable=False)
    short_title: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    description_html: Mapped[str] = mapped_column(Text, nullable=False, default="")
    price_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    stock: Mapped[int] = mapped_column(Integer, nullable=False)
    product_type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    delivery_method: Mapped[str] = mapped_column(String(32), nullable=False)
    return_rule: Mapped[str] = mapped_column(String(32), nullable=False)
    # MutableDict tracks top-level changes; replace nested containers after editing them.
    attributes: Mapped[dict[str, Any]] = mapped_column(
        MutableDict.as_mutable(JSONB), nullable=False
    )
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    images: Mapped[list["ProductImageModel"]] = relationship(
        back_populates="product", cascade="all, delete-orphan", lazy="selectin"
    )


class ProductFieldSchemaModel(TimestampMixin, Base):
    __tablename__ = "product_field_schemas"
    __table_args__ = (
        UniqueConstraint("product_type", "version", name="uq_field_schema_type_version"),
        CheckConstraint("version >= 1", name="ck_field_schema_version_positive"),
        Index(
            "uq_field_schema_active_type",
            "product_type",
            unique=True,
            postgresql_where=text("active"),
        ),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid7)
    product_type: Mapped[str] = mapped_column(String(32), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    # MutableDict tracks top-level changes; replace nested containers after editing them.
    schema: Mapped[dict[str, Any]] = mapped_column(
        MutableDict.as_mutable(JSONB), nullable=False
    )
    active: Mapped[bool] = mapped_column(nullable=False, default=True, server_default="true")


class ProductImageModel(TimestampMixin, Base):
    __tablename__ = "product_images"
    __table_args__ = (
        CheckConstraint("kind IN ('main', 'gallery')", name="ck_product_images_kind"),
        CheckConstraint("sort_order >= 0", name="ck_product_images_sort_nonnegative"),
        CheckConstraint(
            "size_bytes > 0 AND size_bytes <= 2097152", name="ck_product_images_size"
        ),
        Index(
            "uq_product_images_one_main",
            "product_id",
            unique=True,
            postgresql_where=text("kind = 'main'"),
        ),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid7)
    product_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(64), nullable=False)
    product: Mapped[ProductModel] = relationship(back_populates="images")
