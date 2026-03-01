# backend/app/middleware/cors.py

from fastapi.middleware.cors import CORSMiddleware
from config.settings import settings


def add_cors_middleware(app) -> None:
    """
    Call this in app/main.py during app setup.
    Origins come from settings.allowed_origins_list
    so they're configurable per environment.
    """
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins_list,
        allow_credentials=True,         # needed for Bearer token flow
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Run-ID"],    # lets frontend read run ID from response headers
    )
