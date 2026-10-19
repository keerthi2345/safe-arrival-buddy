from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session

from . import models  # noqa: F401  (registers tables with Base)
from .config import settings
from .database import Base, engine, get_db
from .routers import auth, buddies , trips, users          # add users to this import
import asyncio
from .scheduler import scheduler_loop

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)  # we'll switch to Alembic migrations later
    yield
    task = asyncio.create_task(scheduler_loop()) if settings.scheduler_enabled else None
    yield
    if task:
        task.cancel()


app = FastAPI(title=settings.app_name, version="0.6.0", lifespan=lifespan)
app.include_router(auth.router)
app.include_router(buddies.router) 
app.include_router(trips.router)
app.include_router(users.router)


@app.get("/health", tags=["system"])
def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok", "app": settings.app_name}