from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from auth.router import router as auth_router
from config import settings
from database import create_db_and_tables
from food.router import router as food_router
from home.router import router as home_router


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    create_db_and_tables()
    yield


app = FastAPI(lifespan=lifespan)

# Allow the browser frontend to make credentialed requests (it must send the
# refresh-token cookie). Credentialed CORS forbids a "*" origin, so exactly one
# trusted origin is named.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(home_router)
app.include_router(food_router)
