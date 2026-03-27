"""SGMC Brain - FastAPI application."""

from contextlib import asynccontextmanager

from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import alerts, auth, compliance, events, evidence, health, policies, risks, staff
from app.core.auth import CloudflareAccessMiddleware
from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Run migrations on startup
    try:
        alembic_cfg = Config("alembic.ini")
        command.upgrade(alembic_cfg, "head")
    except Exception as e:
        print(f"Migration warning: {e}")
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

# Middleware (bottom-to-top execution order)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(CloudflareAccessMiddleware)

# Routes
app.include_router(health.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(policies.router, prefix="/api")
app.include_router(events.router, prefix="/api")
app.include_router(risks.router, prefix="/api")
app.include_router(compliance.router, prefix="/api")
app.include_router(alerts.router, prefix="/api")
app.include_router(evidence.router, prefix="/api")
app.include_router(staff.router, prefix="/api")
