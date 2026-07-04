import secrets
from datetime import datetime, timedelta, timezone

from sqlmodel import Session, select

from auth.models import RefreshToken, User
from auth.schemas import UserCreate
from auth.utils import hash_password, now_timestamp, verify_password
from config import settings

_DUMMY_HASH = hash_password("dummypassword")


def _dummy_verify() -> None:
    # Equalizes response time when a username is not found, preventing timing attacks.
    _ = verify_password("dummypassword", _DUMMY_HASH)


def _generate_refresh_token() -> str:
    return secrets.token_urlsafe(32)


def get_user_by_username(session: Session, username: str) -> User | None:
    return session.exec(select(User).where(User.username == username)).first()


def create_user(session: Session, user_in: UserCreate) -> User:
    user = User(
        username=user_in.username, hashed_password=hash_password(user_in.password)
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def authenticate_user(session: Session, username: str, password: str) -> User | None:
    user = get_user_by_username(session, username)
    if not user:
        _dummy_verify()
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def _store_refresh_token(session: Session, user: User) -> str:
    assert user.id is not None
    token = _generate_refresh_token()
    expires_at = int(
        (
            datetime.now(timezone.utc)
            + timedelta(days=settings.refresh_token_expire_days)
        ).timestamp()
    )
    session.add(RefreshToken(token=token, user_id=user.id, expires_at=expires_at))
    return token


def create_refresh_token(session: Session, user: User) -> str:
    token = _store_refresh_token(session, user)
    session.commit()
    return token


def use_refresh_token(session: Session, token: str) -> tuple[User, str] | None:
    db_token = session.exec(
        select(RefreshToken).where(RefreshToken.token == token)
    ).first()
    if not db_token:
        return None
    if db_token.expires_at < now_timestamp():
        session.delete(db_token)
        session.commit()
        return None
    user = session.get(User, db_token.user_id)
    if user is None or user.disabled:
        return None
    session.delete(db_token)
    new_token = _store_refresh_token(session, user)
    session.commit()
    return user, new_token


def revoke_refresh_token(
    session: Session, token: str, *, all_devices: bool = False
) -> None:
    db_token = session.exec(
        select(RefreshToken).where(RefreshToken.token == token)
    ).first()
    if not db_token:
        return
    if all_devices:
        # Revoke every refresh token belonging to the presented token's owner.
        for user_token in session.exec(
            select(RefreshToken).where(RefreshToken.user_id == db_token.user_id)
        ).all():
            session.delete(user_token)
    else:
        session.delete(db_token)
    session.commit()
