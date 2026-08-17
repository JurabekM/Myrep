"""REST API routes registered on NiceGUI's underlying FastAPI application.

Auth flow: POST /api/token with username/password -> signed HMAC bearer token;
all data endpoints require ``Authorization: Bearer <token>``.
"""
from __future__ import annotations

import logging
from dataclasses import asdict

from fastapi import Depends, Header, HTTPException
from pydantic import BaseModel

from config import settings
from core.security import (
    api_limiter, create_token, login_limiter, verify_password, verify_token,
)
from database.engine import read_df, session_scope
from database.models import User

log = logging.getLogger(__name__)


class TokenRequest(BaseModel):
    username: str
    password: str


def _require_token(authorization: str = Header(default="")) -> dict:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Bearer token talab qilinadi")
    payload = verify_token(authorization.removeprefix("Bearer ").strip())
    if payload is None:
        raise HTTPException(status_code=401, detail="Token yaroqsiz yoki muddati o'tgan")
    if api_limiter.is_locked(payload["sub"]):
        raise HTTPException(status_code=429, detail="So'rovlar chegarasi oshib ketdi")
    api_limiter.register_failure(payload["sub"])  # counts requests per minute
    return payload


def register_api() -> None:
    """Attach every /api/* route to the running FastAPI app."""
    from nicegui import app

    @app.get("/api/health")
    def health() -> dict:
        from database.engine import db_stats

        return {"status": "ok", "app": settings.APP_NAME,
                "version": settings.APP_VERSION, "tables": db_stats()}

    @app.post("/api/token")
    def token(request: TokenRequest) -> dict:
        if login_limiter.is_locked(request.username):
            raise HTTPException(status_code=429,
                                detail="Juda ko'p urinish — keyinroq qayta urining")
        with session_scope() as session:
            user = session.query(User).filter_by(
                username=request.username, active=True).first()
        if user is None or not verify_password(request.password, user.password_hash):
            login_limiter.register_failure(request.username)
            raise HTTPException(status_code=401, detail="Login yoki parol noto'g'ri")
        login_limiter.register_success(request.username)
        return {"access_token": create_token(user.username, user.role),
                "token_type": "bearer", "role": user.role}

    @app.get("/api/kpi")
    def kpi(year: int | None = None, _payload: dict = Depends(_require_token)) -> dict:
        from analytics.kpi import compute_kpi

        return asdict(compute_kpi(year))

    @app.get("/api/regions")
    def regions(_payload: dict = Depends(_require_token)) -> list[dict]:
        return read_df(
            "SELECT id, name, lat, lon FROM regions ORDER BY name"
        ).to_dict(orient="records")

    @app.get("/api/yields")
    def yields(year: int | None = None,
               _payload: dict = Depends(_require_token)) -> list[dict]:
        from analytics.kpi import latest_year, yield_by_region

        return yield_by_region(year or latest_year()).to_dict(orient="records")

    @app.get("/api/prices/{crop_id}")
    def prices(crop_id: int, days: int = 365,
               _payload: dict = Depends(_require_token)) -> list[dict]:
        from market.service import price_history

        df = price_history(crop_id, days)
        df["date"] = df["date"].astype(str)
        return df.to_dict(orient="records")

    @app.get("/api/weather/{district_id}")
    def weather(district_id: int, days: int = 90,
                _payload: dict = Depends(_require_token)) -> list[dict]:
        from weather.service import history_frame

        df = history_frame(district_id, days)
        df["date"] = df["date"].astype(str)
        return df.to_dict(orient="records")

    @app.post("/api/ai/ask")
    def ai_ask(question: dict, payload: dict = Depends(_require_token)) -> dict:
        from ai.engine import assistant

        result = assistant.ask(str(question.get("question", "")))
        table = result.get("table")
        return {
            "answer": result["answer"],
            "table": table.to_dict(orient="records") if table is not None else None,
            "asked_by": payload["sub"],
        }

    log.info("REST API marshrutlari ro'yxatdan o'tdi (/api/*).")
