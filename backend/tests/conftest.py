import pytest
from fastapi.testclient import TestClient

from app.main import create_app


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
            "file_url": {"type": "string", "format": "uri"},
        },
        "required": ["asset_type", "dimensions", "file_url"],
        "additionalProperties": False,
    }
