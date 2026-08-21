from datetime import timedelta
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from app.catalog.domain import ProductType
from app.catalog.repository import ProductRepository
from app.core.config import Settings
from app.core.security import create_access_token
from app.db.session import get_session
from app.main import create_app


def _image(url: str = "/uploads/main.png") -> list[dict]:
    return [
        {
            "kind": "main",
            "url": url,
            "sort_order": 0,
            "size_bytes": 16,
            "mime_type": "image/png",
        }
    ]


def _product(product_type: str, schema_version: int = 1, title: str = "Product") -> dict:
    attributes = {
        "physical": {
            "weight_kg": 1,
            "specification": "boxed",
            "shipping_template": "standard",
        },
        "virtual": {
            "validity_days": 30,
            "verification_method": "code",
            "redemption_instructions": "Enter the code",
        },
        "creative": {
            "asset_type": "image",
            "dimensions": "1200x800",
            "file_url": "https://assets.example/design.png",
        },
    }[product_type]
    delivery = "ems" if product_type == "physical" else "voucher"
    return {
        "title": title,
        "short_title": title,
        "description_html": '<p>Hello</p><script>alert("x")</script>',
        "price_amount": "19.90",
        "stock": 5,
        "product_type": product_type,
        "status": "off_shelf",
        "delivery_method": delivery,
        "return_rule": "seven_days",
        "attributes": attributes,
        "schema_version": schema_version,
        "images": _image(),
    }


@pytest.fixture
async def api(db_session, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    settings = Settings(
        jwt_secret="test-only-secret-with-enough-entropy",
        admin_username="test-admin",
        admin_password_hash="unused-in-this-test",
        upload_root=str(tmp_path / "uploads"),
    )
    application = create_app(settings=settings)

    async def session_override():
        yield db_session

    application.dependency_overrides[get_session] = session_override
    token = create_access_token(
        settings.admin_username, settings.jwt_secret, timedelta(minutes=5)
    )
    async with AsyncClient(
        transport=ASGITransport(app=application),
        base_url="http://test",
        headers={"Authorization": f"Bearer {token}"},
    ) as test_client:
        yield test_client, application


async def _install_schemas(db_session, physical_schema, virtual_schema, creative_schema):
    repository = ProductRepository(db_session)
    for product_type, schema in (
        (ProductType.PHYSICAL, physical_schema),
        (ProductType.VIRTUAL, virtual_schema),
        (ProductType.CREATIVE, creative_schema),
    ):
        await repository.create_schema(product_type, 1, schema)
    await db_session.commit()


@pytest.mark.asyncio
async def test_publish_three_types_and_reject_inactive_schema_version(
    api, db_session, physical_schema, virtual_schema, creative_schema
):
    client, _ = api
    await _install_schemas(db_session, physical_schema, virtual_schema, creative_schema)

    for product_type in ("physical", "virtual", "creative"):
        schema_response = await client.get(
            f"/api/v1/product-schemas/{product_type}/active"
        )
        assert schema_response.status_code == 200
        assert schema_response.json()["version"] == 1
        assert schema_response.json()["schema"]["type"] == "object"
        response = await client.post("/api/v1/products", json=_product(product_type))
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["product_type"] == product_type
        assert body["price_amount"] == "19.90"
        assert "script" not in body["description_html"]
        assert body["images"][0]["kind"] == "main"

    conflict = await client.post(
        "/api/v1/products", json=_product("physical", schema_version=2)
    )
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "schema_version_conflict"


@pytest.mark.asyncio
async def test_list_detail_edit_and_stale_version(
    api, db_session, physical_schema, virtual_schema, creative_schema
):
    client, _ = api
    await _install_schemas(db_session, physical_schema, virtual_schema, creative_schema)
    first = (
        await client.post(
            "/api/v1/products", json=_product("physical", title="Search Alpha")
        )
    ).json()
    await client.post(
        "/api/v1/products", json=_product("virtual", title="Search Beta")
    )

    page = await client.get(
        "/api/v1/products",
        params={
            "query": "Search",
            "product_type": "physical",
            "status": "off_shelf",
            "page": 1,
            "page_size": 1,
        },
    )
    assert page.status_code == 200
    assert page.json()["total"] == 1
    assert [item["id"] for item in page.json()["items"]] == [first["id"]]
    detail = await client.get(f"/api/v1/products/{first['id']}")
    assert detail.status_code == 200
    assert detail.json()["schema_version"] == 1

    edited_payload = _product("physical", title="Edited")
    edited_payload.pop("product_type")
    edited_payload["version"] = 1
    edited = await client.put(f"/api/v1/products/{first['id']}", json=edited_payload)
    assert edited.status_code == 200, edited.text
    assert edited.json()["version"] == 2
    assert edited.json()["title"] == "Edited"

    stale = await client.put(f"/api/v1/products/{first['id']}", json=edited_payload)
    assert stale.status_code == 409
    assert stale.json()["code"] == "version_conflict"


@pytest.mark.asyncio
async def test_status_transitions_and_failed_batch_roll_back(
    api, db_session, physical_schema, virtual_schema, creative_schema
):
    client, _ = api
    await _install_schemas(db_session, physical_schema, virtual_schema, creative_schema)
    first = (
        await client.post("/api/v1/products", json=_product("physical", title="One"))
    ).json()
    second = (
        await client.post("/api/v1/products", json=_product("physical", title="Two"))
    ).json()

    on_shelf = await client.patch(
        f"/api/v1/products/{first['id']}/status",
        json={"target_status": "on_shelf", "version": 1},
    )
    assert on_shelf.status_code == 200
    penalized = await client.patch(
        f"/api/v1/products/{first['id']}/status",
        json={"target_status": "penalized", "version": 2},
    )
    assert penalized.status_code == 200
    restore = await client.patch(
        f"/api/v1/products/{first['id']}/status",
        json={"target_status": "on_shelf", "version": 3},
    )
    assert restore.status_code == 409

    batch_success = await client.post(
        "/api/v1/products/batch-status",
        json={
            "product_ids": [{"product_id": second["id"], "version": 1}],
            "target_status": "on_shelf",
        },
    )
    assert batch_success.status_code == 200
    assert batch_success.json()[0]["status"] == "on_shelf"

    back_off = await client.patch(
        f"/api/v1/products/{second['id']}/status",
        json={"target_status": "off_shelf", "version": 2},
    )
    assert back_off.status_code == 200

    failed = await client.post(
        "/api/v1/products/batch-status",
        json={
            "product_ids": [
                {"product_id": first["id"], "version": 3},
                {"product_id": second["id"], "version": 99},
            ],
            "target_status": "on_shelf",
        },
    )
    assert failed.status_code == 409
    unchanged = await client.get(f"/api/v1/products/{second['id']}")
    assert unchanged.json()["status"] == "off_shelf"
    assert unchanged.json()["version"] == 3


@pytest.mark.asyncio
async def test_upload_returns_product_image_metadata_and_rejects_disguised_file(api):
    client, _ = api
    success = await client.post(
        "/api/v1/uploads/images",
        files={"file": ("photo.png", b"\x89PNG\r\n\x1a\npixels", "image/png")},
    )
    assert success.status_code == 201, success.text
    assert success.json()["url"].startswith("/uploads/")
    assert success.json()["size_bytes"] == 14
    assert success.json()["mime_type"] == "image/png"
    stored = await client.get(success.json()["url"])
    assert stored.status_code == 200
    assert stored.content == b"\x89PNG\r\n\x1a\npixels"

    disguised = await client.post(
        "/api/v1/uploads/images",
        files={"file": ("photo.png", b"#!/bin/sh", "image/png")},
    )
    assert disguised.status_code == 415
    assert disguised.json()["code"] == "invalid_image_signature"

    oversized = await client.post(
        "/api/v1/uploads/images",
        files={
            "file": (
                "photo.png",
                b"\x89PNG\r\n\x1a\n" + b"x" * (2 * 1024 * 1024),
                "image/png",
            )
        },
    )
    assert oversized.status_code == 413
    assert oversized.json()["code"] == "image_too_large"


@pytest.mark.asyncio
async def test_management_endpoints_require_authentication(api):
    client, _application = api
    response = await client.get("/api/v1/products", headers={"Authorization": ""})
    assert response.status_code == 401
    assert response.json()["code"] == "authentication_failed"
