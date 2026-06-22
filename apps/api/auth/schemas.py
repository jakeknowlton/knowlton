from pydantic import BaseModel, ConfigDict


class UserCreate(BaseModel):
    username: str
    password: str


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    username: str
    id: int
    disabled: bool


class TokenResponse(BaseModel):
    # Only the short-lived access token is returned in the body; the refresh
    # token travels in an HttpOnly cookie and is never exposed to JS.
    access_token: str
    token_type: str = "bearer"
