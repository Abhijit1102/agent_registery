from contextlib import asynccontextmanager

from fastapi import FastAPI

from database.session import engine
from database.orm_models import Base
from routes import agents, usage


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Agent Registry & Usage Tracking Platform",
    description="Register agents, track usage, and aggregate metrics.",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(agents.router)
app.include_router(usage.router)


@app.get("/", tags=["Health"])
def health_check():
    return {"status": "ok", "message": "Agent Registry is running"}
