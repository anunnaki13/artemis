from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app

from app.config import get_settings
from app.core.logging import configure_logging
from app.routers import auth, dashboard, edge, execution, health, market_data, notifications, reports, risk, strategies
from app.routers import settings as settings_router


def create_app() -> FastAPI:
    configure_logging()
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router)
    app.include_router(auth.router, prefix="/api")
    app.include_router(dashboard.router, prefix="/api")
    app.include_router(edge.router, prefix="/api")
    app.include_router(execution.router, prefix="/api")
    app.include_router(market_data.router, prefix="/api")
    app.include_router(notifications.router, prefix="/api")
    app.include_router(reports.router, prefix="/api")
    app.include_router(risk.router, prefix="/api")
    app.include_router(settings_router.router, prefix="/api")
    app.include_router(strategies.router, prefix="/api")
    if settings.prometheus_enabled:
        app.mount("/metrics", make_asgi_app())

    @app.on_event("startup")
    async def startup_background_services() -> None:
        await reports.digest_service.start()
        if not market_data.stream_service.status().running:
            symbols = [
                symbol.strip().upper()
                for symbol in settings.market_stream_autostart_symbols.split(",")
                if symbol.strip()
            ]
            if symbols:
                try:
                    await market_data.stream_service.start(symbols, settings.market_stream_autostart_interval)
                except Exception:
                    pass

    @app.on_event("shutdown")
    async def shutdown_market_stream() -> None:
        await market_data.stream_service.stop()
        await execution.user_stream_service.stop()
        await reports.digest_service.stop()

    return app


app = create_app()
