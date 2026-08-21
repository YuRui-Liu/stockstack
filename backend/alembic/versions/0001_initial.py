"""Create products, versioned field schemas, and product images."""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    ]


def upgrade() -> None:
    op.create_table(
        "products",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=60), nullable=False),
        sa.Column("short_title", sa.String(length=120), nullable=False),
        sa.Column("description_html", sa.Text(), nullable=False),
        sa.Column("price_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("stock", sa.Integer(), nullable=False),
        sa.Column("product_type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("delivery_method", sa.String(length=32), nullable=False),
        sa.Column("return_rule", sa.String(length=32), nullable=False),
        sa.Column("attributes", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("schema_version", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        *_timestamps(),
        sa.CheckConstraint("price_amount >= 0", name="ck_products_price_nonnegative"),
        sa.CheckConstraint("stock >= 0", name="ck_products_stock_nonnegative"),
        sa.CheckConstraint("version >= 1", name="ck_products_version_positive"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_products_listing",
        "products",
        ["status", "product_type", sa.text("updated_at DESC"), sa.text("id DESC")],
    )
    op.create_index(
        "ix_products_title_search",
        "products",
        [sa.text("to_tsvector('simple', title)")],
        postgresql_using="gin",
    )
    op.create_table(
        "product_field_schemas",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_type", sa.String(length=32), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("schema", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("active", sa.Boolean(), server_default="true", nullable=False),
        *_timestamps(),
        sa.CheckConstraint("version >= 1", name="ck_field_schema_version_positive"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("product_type", "version", name="uq_field_schema_type_version"),
    )
    op.create_index(
        "uq_field_schema_active_type",
        "product_field_schemas",
        ["product_type"],
        unique=True,
        postgresql_where=sa.text("active"),
    )
    op.create_table(
        "product_images",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("mime_type", sa.String(length=64), nullable=False),
        *_timestamps(),
        sa.CheckConstraint("kind IN ('main', 'gallery')", name="ck_product_images_kind"),
        sa.CheckConstraint("sort_order >= 0", name="ck_product_images_sort_nonnegative"),
        sa.CheckConstraint(
            "size_bytes > 0 AND size_bytes <= 2097152", name="ck_product_images_size"
        ),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_product_images_one_main",
        "product_images",
        ["product_id"],
        unique=True,
        postgresql_where=sa.text("kind = 'main'"),
    )


def downgrade() -> None:
    op.drop_index("uq_product_images_one_main", table_name="product_images")
    op.drop_table("product_images")
    op.drop_index("uq_field_schema_active_type", table_name="product_field_schemas")
    op.drop_table("product_field_schemas")
    op.drop_index("ix_products_title_search", table_name="products", postgresql_using="gin")
    op.drop_index("ix_products_listing", table_name="products")
    op.drop_table("products")
