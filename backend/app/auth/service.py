from pwdlib import PasswordHash

from app.core.config import Settings
from app.core.security import verify_password

_DUMMY_PASSWORD_HASH = PasswordHash.recommended().hash("dummy-password")


def authenticate_admin(username: str, password: str, settings: Settings) -> bool:
    username_matches = username == settings.admin_username
    password_hash = (
        settings.admin_password_hash if username_matches else _DUMMY_PASSWORD_HASH
    )
    password_matches = verify_password(password, password_hash)
    return username_matches and password_matches
