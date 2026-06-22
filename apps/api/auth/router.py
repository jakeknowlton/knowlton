from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session

from auth.cookies import COOKIE_NAME, clear_refresh_cookie, set_refresh_cookie
from auth.schemas import TokenResponse, UserCreate, UserRead
from auth.service import (
    authenticate_user,
    create_refresh_token,
    create_user,
    get_user_by_username,
    revoke_refresh_token,
    use_refresh_token,
)
from auth.utils import create_access_token
from database import get_session

router = APIRouter(prefix="/auth", tags=["auth"])

RefreshCookie = Annotated[str | None, Cookie(alias=COOKIE_NAME)]


@router.post("/token", response_model=TokenResponse)
def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: Annotated[Session, Depends(get_session)],
    response: Response,
) -> TokenResponse:
    user = authenticate_user(session, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    set_refresh_cookie(response, create_refresh_token(session, user))
    return TokenResponse(access_token=create_access_token(user.username))


@router.post("/refresh", response_model=TokenResponse)
def refresh(
    session: Annotated[Session, Depends(get_session)],
    response: Response,
    refresh_token: RefreshCookie = None,
) -> TokenResponse:
    result = use_refresh_token(session, refresh_token) if refresh_token else None
    if not result:
        # Clear a stale cookie so the browser stops presenting a dead token.
        clear_refresh_cookie(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )
    user, new_refresh_token = result
    set_refresh_cookie(response, new_refresh_token)
    return TokenResponse(access_token=create_access_token(user.username))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    session: Annotated[Session, Depends(get_session)],
    response: Response,
    refresh_token: RefreshCookie = None,
    all_devices: bool = False,
) -> None:
    if refresh_token:
        revoke_refresh_token(session, refresh_token, all_devices=all_devices)
    clear_refresh_cookie(response)


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(
    user_in: UserCreate,
    session: Annotated[Session, Depends(get_session)],
) -> UserRead:
    if get_user_by_username(session, user_in.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        )
    user = create_user(session, user_in)
    return UserRead.model_validate(user)
