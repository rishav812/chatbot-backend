from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database.session import engine
from app.database.models import Base
from app.routes import ingest


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Tables are now automatically created by Docker via tables.sql
    print("🚀 App starting up... Database initialized via Docker.")
    yield
    # Cleanly close DB connection pool on shutdown
    await engine.dispose()


app = FastAPI(lifespan=lifespan)

# Include routers
app.include_router(ingest.router)
