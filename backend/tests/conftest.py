import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.catalog.models import Base
from app.main import create_app


@pytest.fixture
async def db_engine():
    database_url = os.getenv("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("TEST_DATABASE_URL must point to a real PostgreSQL database")
    engine = create_async_engine(database_url, pool_pre_ping=True)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def db_session(db_engine) -> AsyncSession:
    factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with factory() as session:
        yield session
        await session.rollback()
    async with db_engine.begin() as connection:
        await connection.execute(
            text(
                "TRUNCATE product_images, products, product_field_schemas "
                "RESTART IDENTITY CASCADE"
            )
        )


@pytest.fixture
def client() -> TestClient:
    with TestClient(create_app()) as test_client:
        yield test_client


@pytest.fixture
def physical_schema() -> dict:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "properties": {
            "weight_kg": {"type": "number", "minimum": 0},
            "specification": {"type": "string", "maxLength": 100},
            "shipping_template": {"enum": ["standard", "cold_chain"]},
        },
        "required": ["weight_kg", "specification", "shipping_template"],
        "additionalProperties": False,
    }


@pytest.fixture
def virtual_schema() -> dict:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "properties": {
            "validity_days": {"type": "integer", "minimum": 1},
            "verification_method": {"enum": ["code", "qr", "manual"]},
            "redemption_instructions": {"type": "string", "maxLength": 500},
        },
        "required": [
            "validity_days",
            "verification_method",
            "redemption_instructions",
        ],
        "additionalProperties": False,
    }


@pytest.fixture
def creative_schema() -> dict:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "properties": {
            "asset_type": {"enum": ["image", "video", "html"]},
            "dimensions": {
                "type": "string",
                "pattern": "^[1-9][0-9]*x[1-9][0-9]*$",
            },
            "file_url": {"type": "string", "format": "http-url"},
        },
        "required": ["asset_type", "dimensions", "file_url"],
        "additionalProperties": False,
    }
