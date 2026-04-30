from fastapi import FastAPI
from prometheus_client import make_asgi_app

from app.config import get_settings
from app.core.logging import configure_logging
from app.routers import auth, dashboard, health, risk


def create_app() -> FastAPI:
    configure_logging()
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version="0.1.0")
    app.include_router(health.router)
    app.include_router(auth.router, prefix="/api")
    app.include_router(dashboard.router, prefix="/api")
    app.include_router(risk.router, prefix="/api")
    if settings.prometheus_enabled:
        app.mount("/metrics", make_asgi_app())
    return app


app = create_app()

