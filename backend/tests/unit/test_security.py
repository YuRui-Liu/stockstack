from datetime import timedelta

import pytest

from app.core.errors import AppError
from app.core.security import create_access_token, decode_access_token, verify_password


def test_password_hash_verification() -> None:
    from pwdlib import PasswordHash

    password_hash = PasswordHash.recommended().hash("correct-password")

    assert verify_password("correct-password", password_hash) is True
    assert verify_password("wrong-password", password_hash) is False


def test_jwt_encode_decode_and_expiry() -> None:
    secret = "a-test-secret-that-is-at-least-32-bytes-long"
    wrong_secret = "another-test-secret-at-least-32-bytes-long"
    token = create_access_token("admin", secret, timedelta(minutes=5))

    assert decode_access_token(token, secret) == "admin"

    expired = create_access_token("admin", secret, timedelta(seconds=-1))
    with pytest.raises(AppError, match="Invalid authentication credentials"):
        decode_access_token(expired, secret)
    with pytest.raises(AppError, match="Invalid authentication credentials"):
        decode_access_token(token, wrong_secret)
