from fastapi import APIRouter, FastAPI

from .api import auth, health, me, stores
from .config import get_settings
from .errors import install_error_handlers


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="OmborAI API",
        version="0.1.0",
        docs_url=None if settings.is_prod else "/docs",
        redoc_url=None,
        openapi_url=None if settings.is_prod else "/openapi.json",
    )
    install_error_handlers(app)
    app.include_router(health.router)

    v1 = APIRouter(prefix="/v1")
    v1.include_router(auth.router)
    v1.include_router(me.router)
    v1.include_router(stores.router)
    app.include_router(v1)
    return app


app = create_app()
