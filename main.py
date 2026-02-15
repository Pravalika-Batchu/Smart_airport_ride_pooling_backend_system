from contextlib import asynccontextmanager
from fastapi import FastAPI
from database import engine, Base
from routers import rides

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield

app = FastAPI(title="Smart Airport Ride Pooling", lifespan=lifespan)

app.include_router(rides.router)

@app.get("/")
def read_root():
    return {"message": "Welcome to Smart Airport Ride Pooling System"}
