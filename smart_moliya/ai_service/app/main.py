from fastapi import FastAPI

from app.api.v1 import api_router
from app.core.config import settings

app = FastAPI(title=settings.APP_NAME, version="0.1.0")
app.include_router(api_router)


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.APP_NAME}
