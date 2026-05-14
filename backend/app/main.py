from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import auth, calls, health, integrations, voice

app = FastAPI(
    title="DishHome AI Call Center",
    version="0.1.0",
    description="AI core service for the DishHome ISP call center.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(calls.router)
app.include_router(voice.router)
app.include_router(integrations.router)
