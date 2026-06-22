from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session

from auth.schemas import RefreshRequest, TokenPair, UserCreate, UserRead
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


@router.post("/token", response_model=TokenPair)
def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: Annotated[Session, Depends(get_session)],
) -> TokenPair:
    user = authenticate_user(session, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return TokenPair(
        access_token=create_access_token(user.username),
        refresh_token=create_refresh_token(session, user),
    )


@router.post("/refresh", response_model=TokenPair)
def refresh(
    body: RefreshRequest,
    session: Annotated[Session, Depends(get_session)],
) -> TokenPair:
    result = use_refresh_token(session, body.refresh_token)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )
    user, new_refresh_token = result
    return TokenPair(
        access_token=create_access_token(user.username),
        refresh_token=new_refresh_token,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    body: RefreshRequest,
    session: Annotated[Session, Depends(get_session)],
) -> None:
    revoke_refresh_token(session, body.refresh_token)


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
    return create_user(session, user_in)
