"""StudySphere AI: FastAPI application."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import inspect

from app.api import auth
from app.database import engine

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")
logger = logging.getLogger("studysphere")


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    if not inspect(engine).has_table("alembic_version"):
        logger.warning("The database has no migration history. From the backend folder, run: alembic upgrade head")
    yield


app = FastAPI(title="StudySphere AI", version="0.1.0", lifespan=lifespan)
app.include_router(auth.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}