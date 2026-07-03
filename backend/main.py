from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app
from starlette.middleware.wsgi import WSGIMiddleware

from backend.routes import (
    upload,
    review,
    regenerate,
    export,
    pricing,
    dashboard,
    health,
)


from backend.database import Base, engine
import backend.models

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="SmartRFP API",
    version="1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router)
app.include_router(review.router)
app.include_router(regenerate.router)
app.include_router(export.router)
app.include_router(pricing.router)
app.include_router(dashboard.router)
app.include_router(health.router)

metrics_app = make_asgi_app()
app.mount("/metrics/", metrics_app)