from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from app.auth.service import authenticate_admin
from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.core.security import create_access_token, decode_access_token

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
bearer_scheme = HTTPBearer(auto_error=False)


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int


def require_admin(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(bearer_scheme)
    ],
    settings: Annotated[Settings, Depends(get_settings)],
) -> str:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AppError(
            "authentication_failed", "Invalid authentication credentials", 401
        )
    subject = decode_access_token(credentials.credentials, settings.jwt_secret)
    if subject != settings.admin_username:
        raise AppError(
            "authentication_failed", "Invalid authentication credentials", 401
        )
    return subject


@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest, settings: Annotated[Settings, Depends(get_settings)]
) -> TokenResponse:
    if not authenticate_admin(payload.username, payload.password, settings):
        raise AppError(
            "authentication_failed", "Invalid authentication credentials", 401
        )
    expires_in = settings.access_token_expire_minutes * 60
    return TokenResponse(
        access_token=create_access_token(
            settings.admin_username,
            settings.jwt_secret,
            timedelta(minutes=settings.access_token_expire_minutes),
        ),
        token_type="bearer",
        expires_in=expires_in,
    )


@router.get("/me")
def me(username: Annotated[str, Depends(require_admin)]) -> dict[str, str]:
    return {"username": username}
