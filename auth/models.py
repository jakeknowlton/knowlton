from sqlmodel import Field, SQLModel


class UserBase(SQLModel):
    username: str = Field(unique=True, index=True)


class User(UserBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    hashed_password: str
    disabled: bool = False


class UserCreate(UserBase):
    password: str


class UserRead(UserBase):
    id: int
    disabled: bool
