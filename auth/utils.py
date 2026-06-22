from datetime import datetime, timedelta, timezone
from typing import TypedDict

import jwt
from pwdlib import PasswordHash

from config import settings

_password_hash = PasswordHash.recommended()


class JWTPayload(TypedDict):
    sub: str
    exp: int


def now_timestamp() -> int:
    return int(datetime.now(timezone.utc).timestamp())


def hash_password(password: str) -> str:
    return _password_hash.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return _password_hash.verify(plain, hashed)


def create_access_token(username: str, expires_delta: timedelta | None = None) -> str:
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    payload: JWTPayload = {"sub": username, "exp": int(expire.timestamp())}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_token(token: str) -> JWTPayload:
    return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
