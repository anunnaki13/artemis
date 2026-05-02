import asyncio
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app

from app.config import get_settings
from app.core.logging import configure_logging
from app.routers import ai_analyst, auth, backtest, dashboard, edge, execution, health, market_data, notifications, recovery, reports, risk, strategies
from app.routers import settings as settings_router

logger = logging.getLogger(__name__)


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
    app.include_router(ai_analyst.router, prefix="/api")
    app.include_router(auth.router, prefix="/api")
    app.include_router(backtest.router, prefix="/api")
    app.include_router(dashboard.router, prefix="/api")
    app.include_router(edge.router, prefix="/api")
    app.include_router(execution.router, prefix="/api")
    app.include_router(market_data.router, prefix="/api")
    app.include_router(notifications.router, prefix="/api")
    app.include_router(recovery.router, prefix="/api")
    app.include_router(reports.router, prefix="/api")
    app.include_router(risk.router, prefix="/api")
    app.include_router(settings_router.router, prefix="/api")
    app.include_router(strategies.router, prefix="/api")
    if settings.prometheus_enabled:
        app.mount("/metrics", make_asgi_app())

    @app.on_event("startup")
    async def startup_background_services() -> None:
        await reports.digest_service.start()
        await recovery.recovery_monitor_service.start()
        async def maintain_market_stream() -> None:
            while True:
                try:
                    await market_data.ensure_market_stream_running(force=True)
                except Exception as exc:
                    logger.warning("Market stream maintainer failed: %s", exc)
                await asyncio.sleep(15)

        await market_data.ensure_market_stream_running(force=True)
        app.state.market_stream_maintainer_task = asyncio.create_task(maintain_market_stream())

    @app.on_event("shutdown")
    async def shutdown_market_stream() -> None:
        maintainer_task = getattr(app.state, "market_stream_maintainer_task", None)
        if maintainer_task is not None:
            maintainer_task.cancel()
            try:
                await maintainer_task
            except asyncio.CancelledError:
                pass
        await market_data.stream_service.stop()
        await execution.user_stream_service.stop()
        await reports.digest_service.stop()
        await recovery.recovery_monitor_service.stop()

    return app


app = create_app()
