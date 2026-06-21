from sqlmodel import Session, select

from auth.models import User, UserCreate
from auth.utils import hash_password, verify_password

_DUMMY_HASH = hash_password("dummypassword")


def _dummy_verify() -> None:
    # Equalizes response time when a username is not found, preventing timing attacks.
    verify_password("dummypassword", _DUMMY_HASH)


def get_user_by_username(session: Session, username: str) -> User | None:
    return session.exec(select(User).where(User.username == username)).first()


def create_user(session: Session, user_in: UserCreate) -> User:
    user = User(username=user_in.username, hashed_password=hash_password(user_in.password))
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
