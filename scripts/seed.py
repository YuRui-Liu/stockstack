"""Idempotently install demo schemas and products for the local environment."""

import asyncio
import base64
import os
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from app.catalog.models import ProductFieldSchemaModel, ProductImageModel, ProductModel
from app.core.config import get_settings
from app.db.session import create_engine_and_session_factory
from sqlalchemy import select

LOAD_TEST_PRODUCT_ID = UUID("0198c8bc-1234-7abc-8def-0123456789ab")
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)

SCHEMAS = {
    "physical": {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "properties": {
            "weight_kg": {"type": "number", "minimum": 0},
            "specification": {"type": "string", "maxLength": 100},
            "shipping_template": {"enum": ["standard", "cold_chain"]},
        },
        "required": ["weight_kg", "specification", "shipping_template"],
        "additionalProperties": False,
    },
    "virtual": {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "properties": {
            "validity_days": {"type": "integer", "minimum": 1},
            "verification_method": {"enum": ["code", "qr", "manual"]},
            "redemption_instructions": {"type": "string", "maxLength": 500},
        },
        "required": ["validity_days", "verification_method", "redemption_instructions"],
        "additionalProperties": False,
    },
    "creative": {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "properties": {
            "asset_type": {"enum": ["image", "video", "html"]},
            "dimensions": {"type": "string", "pattern": "^[1-9][0-9]*x[1-9][0-9]*$"},
            "file_url": {"type": "string", "format": "http-url"},
        },
        "required": ["asset_type", "dimensions", "file_url"],
        "additionalProperties": False,
    },
}

SAMPLES = {
    "physical": ("演示实物商品", {"weight_kg": 1.2, "specification": "标准盒装", "shipping_template": "standard"}),
    "virtual": ("演示虚拟商品", {"validity_days": 30, "verification_method": "code", "redemption_instructions": "下单后输入兑换码"}),
    "creative": ("演示创意商品", {"asset_type": "image", "dimensions": "1200x800", "file_url": "https://assets.example/demo.png"}),
}


def ensure_demo_image() -> None:
    path = Path(os.getenv("UPLOAD_ROOT", "/tmp/stockstack-uploads")) / "seed-main.png"
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if not path.exists():
        path.write_bytes(PNG)


def product(product_id: UUID, product_type: str, title: str, attributes: dict) -> ProductModel:
    return ProductModel(
        id=product_id,
        title=title,
        short_title=title,
        description_html="<p>StockStack 本地演示数据</p>",
        price_amount=Decimal("19.90"),
        stock=100,
        product_type=product_type,
        status="off_shelf",
        delivery_method="ems" if product_type == "physical" else "voucher",
        return_rule="seven_days",
        attributes=attributes,
        schema_version=1,
        images=[ProductImageModel(kind="main", url="/uploads/seed-main.png", sort_order=0, size_bytes=len(PNG), mime_type="image/png")],
    )


async def seed() -> None:
    settings = get_settings()
    engine, session_factory = create_engine_and_session_factory(settings.database_url)
    try:
        ensure_demo_image()
        async with session_factory() as session:
            for product_type, schema in SCHEMAS.items():
                existing = await session.scalar(select(ProductFieldSchemaModel).where(ProductFieldSchemaModel.product_type == product_type, ProductFieldSchemaModel.version == 1))
                if existing is None:
                    session.add(ProductFieldSchemaModel(product_type=product_type, version=1, schema=schema, active=True))

            ids = {
                "physical": LOAD_TEST_PRODUCT_ID,
                "virtual": UUID("0198c8bc-1234-7abc-8def-0123456789ac"),
                "creative": UUID("0198c8bc-1234-7abc-8def-0123456789ad"),
            }
            for product_type, (title, attributes) in SAMPLES.items():
                if await session.get(ProductModel, ids[product_type]) is None:
                    session.add(product(ids[product_type], product_type, title, attributes))
            await session.commit()
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
