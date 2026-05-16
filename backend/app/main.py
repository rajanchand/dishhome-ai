from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.observability import install as install_observability
from app.routers import (
    admin,
    auth,
    calls,
    campaigns,
    faqs,
    health,
    huawei,
    inbox,
    integrations,
    metrics,
    telephony,
    voice,
)

app = FastAPI(
    title="DishHome AI Call Center",
    version="0.3.0",
    description="AI core service for the DishHome ISP call center.",
)

# Observability first so request IDs propagate to CORS / errors.
install_observability(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["authorization", "content-type", "x-request-id"],
    expose_headers=["x-request-id", "x-process-time-ms"],
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(calls.router)
app.include_router(voice.router)
app.include_router(integrations.router)
app.include_router(metrics.router)
app.include_router(huawei.router)
app.include_router(faqs.router)
app.include_router(campaigns.router)
app.include_router(inbox.router)
app.include_router(admin.router)
app.include_router(telephony.router)
