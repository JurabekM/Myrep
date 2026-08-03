import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import get_settings
from app.db import init_db
from app.logging_config import configure_logging
from app.rate_limit import limiter
from app.routers import auth, diagnosis, market, weather
from app.schemas import ErrorOut

settings = get_settings()
configure_logging()
logger = logging.getLogger("dehqon.app")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    db_kind = "sqlite" if settings.is_sqlite else "postgresql"
    logger.info("startup environment=%s database=%s", settings.environment, db_kind)
    yield


app = FastAPI(
    title="Dehqon Ko'makchi API",
    description=(
        "Backend for the Dehqon Ko'makchi Android app: phone-OTP auth, weather proxy, "
        "optional server-side crop diagnosis, and the shared Bozor marketplace "
        "(listings/groups/reports). All third-party integrations run against mock "
        "providers by default -- see app/providers/."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # Safe, uniform error response: never echoes raw internals to the client.
    logger.info("validation_error path=%s errors=%s", request.url.path, exc.errors())
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorOut(error="validation_error", detail="Invalid request payload").model_dump(),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("unhandled_error path=%s", request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorOut(error="internal_error", detail="Something went wrong").model_dump(),
    )


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}


app.include_router(auth.router)
app.include_router(weather.router)
app.include_router(diagnosis.router)
app.include_router(market.router)
