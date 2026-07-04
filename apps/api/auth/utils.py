from datetime import datetime, timedelta, timezone
from typing import TypedDict, cast

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
    # `dict(payload)` widens the TypedDict to the `dict[str, Any]` that `encode`
    # accepts. PyJWT's encode/decode are flagged `reportUnknownMemberType` because
    # their signatures reference `cryptography` key-type aliases that basedpyright
    # resolves to Unknown — a library stub gap, not something we can annotate away.
    return jwt.encode(  # pyright: ignore[reportUnknownMemberType]
        dict(payload), settings.secret_key, algorithm=settings.algorithm
    )


def decode_token(token: str) -> JWTPayload:
    raw = jwt.decode(  # pyright: ignore[reportUnknownMemberType]
        token, settings.secret_key, algorithms=[settings.algorithm]
    )
    # `decode` returns `dict[str, Any]`; the cast through `object` re-narrows it to
    # our payload shape (a direct cast trips `reportInvalidCast` for non-overlap).
    return cast(JWTPayload, cast(object, raw))
