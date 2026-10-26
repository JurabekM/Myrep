"""FastAPI ilovasi. 7-fazada auth, RBAC, sync va /v/{qr_token} qo'shiladi."""

from __future__ import annotations

from fastapi import FastAPI

from zanjir_server import __version__


def create_app() -> FastAPI:
    app = FastAPI(title="ZANJIR", version=__version__, docs_url=None, redoc_url=None)

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        # Jarayon tirikligi; bazaga murojaat qilmaydi.
        return {"status": "ok"}

    return app


app = create_app()
