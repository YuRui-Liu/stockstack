from datetime import UTC, datetime, timedelta

import jwt
from pwdlib import PasswordHash

from app.core.errors import AppError

PASSWORD_HASH = PasswordHash.recommended()


def verify_password(password: str, password_hash: str) -> bool:
    return PASSWORD_HASH.verify(password, password_hash)


def create_access_token(subject: str, secret: str, expires_delta: timedelta) -> str:
    issued_at = datetime.now(UTC)
    return jwt.encode(
        {"sub": subject, "iat": issued_at, "exp": issued_at + expires_delta},
        secret,
        algorithm="HS256",
    )


def decode_access_token(token: str, secret: str) -> str:
    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"])
        subject = payload.get("sub")
        if not isinstance(subject, str) or not subject:
            raise jwt.InvalidTokenError
        return subject
    except jwt.PyJWTError as error:
        raise AppError(
            "authentication_failed", "Invalid authentication credentials", 401
        ) from error
