from uuid import UUID

from app.catalog.public_router import get_public_service
from app.core.errors import AppError

PRODUCT_ID = UUID("018f3f4e-7b2c-7abc-8def-123456789abc")


class MissingService:
    async def detail(self, _product_id):
        raise AppError("product_not_found", "Product not found", 404)


class DenyingCache:
    async def rate_limit(self, *_args, **_kwargs):
        return False, 100


def test_public_product_requires_uuid7_and_does_not_require_admin(client):
    client.app.dependency_overrides[get_public_service] = lambda: MissingService()

    invalid = client.get("/api/v1/public/products/018f3f4e-7b2c-4abc-8def-123456789abc")
    missing = client.get(f"/api/v1/public/products/{PRODUCT_ID}")

    assert invalid.status_code == 400
    assert missing.status_code == 404
    assert missing.json()["code"] == "product_not_found"


def test_public_rate_limit_returns_retry_after(client):
    client.app.state.product_cache = DenyingCache()
    response = client.get(f"/api/v1/public/products/{PRODUCT_ID}")
    assert response.status_code == 429
    assert response.headers["retry-after"] == str(
        client.app.state.settings.rate_limit_window_seconds
    )
