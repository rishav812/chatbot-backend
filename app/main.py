from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database.session import engine
from app.database.models import Base
from app.routes import ingest


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Database tables created successfully")
    yield
    await engine.dispose()


app = FastAPI(lifespan=lifespan)

# Include routers
app.include_router(ingest.router)
