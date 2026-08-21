from fastapi.testclient import TestClient

EXPECTED_ERROR_KEYS = {"code", "message", "field_errors", "request_id"}


def assert_error_contract(response, *, status: int, code: str) -> None:
    assert response.status_code == status
    body = response.json()
    assert set(body) == EXPECTED_ERROR_KEYS
    assert body["code"] == code
    assert isinstance(body["message"], str)
    assert isinstance(body["field_errors"], dict)
    assert body["request_id"] == response.headers["X-Request-ID"]


def test_admin_login_returns_bearer_token(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "test-admin", "password": "correct-password"},
    )

    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    assert response.json()["access_token"]
    assert response.json()["expires_in"] == 300


def test_bad_credentials_have_same_unauthorized_response(client: TestClient) -> None:
    wrong_password = client.post(
        "/api/v1/auth/login",
        json={"username": "test-admin", "password": "wrong-password"},
    )
    unknown_user = client.post(
        "/api/v1/auth/login",
        json={"username": "unknown", "password": "wrong-password"},
    )

    assert_error_contract(wrong_password, status=401, code="authentication_failed")
    assert_error_contract(unknown_user, status=401, code="authentication_failed")
    assert wrong_password.json()["message"] == unknown_user.json()["message"]


def test_protected_route_rejects_missing_and_invalid_tokens(client: TestClient) -> None:
    missing = client.get("/api/v1/auth/me")
    invalid = client.get(
        "/api/v1/auth/me", headers={"Authorization": "Bearer invalid-token"}
    )

    assert_error_contract(missing, status=401, code="authentication_failed")
    assert_error_contract(invalid, status=401, code="authentication_failed")


def test_validation_error_uses_error_contract_and_request_id(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "test-admin"},
        headers={"X-Request-ID": "test-request-123"},
    )

    assert_error_contract(response, status=400, code="validation_error")
    assert response.json()["request_id"] == "test-request-123"
    assert "password" in response.json()["field_errors"]
