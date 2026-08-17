from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.core.config import settings
from app.core.security import (
    SESSION_COOKIE_NAME,
    create_session_token,
    require_admin,
    verify_credentials,
)
from app.repository import AdminRepository, get_repository

app = FastAPI(title=settings.APP_NAME, version="0.1.0", docs_url=None, redoc_url=None)

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

RepoDep = Annotated[AdminRepository, Depends(get_repository)]


def render(request: Request, template: str, **context) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request, name=template, context={"authenticated": True, **context}
    )


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.APP_NAME}


# --- Auth ---

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(
        request=request, name="login.html", context={"authenticated": False}
    )


@app.post("/login")
async def login_submit(request: Request, username: Annotated[str, Form()], password: Annotated[str, Form()]):
    if not verify_credentials(username, password):
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={"authenticated": False, "error": "Login yoki parol noto'g'ri"},
            status_code=401,
        )

    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie(
        SESSION_COOKIE_NAME,
        create_session_token(),
        httponly=True,
        samesite="lax",
        max_age=settings.SESSION_EXPIRE_HOURS * 3600,
    )
    return response


@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie(SESSION_COOKIE_NAME)
    return response


# --- Sahifalar (barchasi sessiya talab qiladi) ---

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, repo: RepoDep):
    if redirect := require_admin(request):
        return redirect
    stats = await repo.get_dashboard_stats()
    transactions = await repo.list_transactions(limit=10)
    return render(request, "dashboard.html", stats=stats, transactions=transactions)


@app.get("/users", response_class=HTMLResponse)
async def users_page(request: Request, repo: RepoDep):
    if redirect := require_admin(request):
        return redirect
    users = await repo.list_users()
    return render(request, "users.html", users=users)


@app.post("/users/{user_id}/toggle")
async def toggle_user(request: Request, user_id: str, repo: RepoDep):
    if redirect := require_admin(request):
        return redirect
    users = await repo.list_users()
    current = next((u for u in users if str(u["id"]) == user_id), None)
    if current is not None:
        await repo.set_user_active(user_id, not current["is_active"])
    return RedirectResponse(url="/users", status_code=303)


@app.get("/transactions", response_class=HTMLResponse)
async def transactions_page(request: Request, repo: RepoDep):
    if redirect := require_admin(request):
        return redirect
    transactions = await repo.list_transactions()
    return render(request, "transactions.html", transactions=transactions)


@app.get("/fraud", response_class=HTMLResponse)
async def fraud_page(request: Request, repo: RepoDep):
    if redirect := require_admin(request):
        return redirect
    suspicious = await repo.find_suspicious_transactions()
    return render(request, "fraud.html", suspicious=suspicious)


@app.get("/analytics", response_class=HTMLResponse)
async def analytics_page(request: Request, repo: RepoDep):
    if redirect := require_admin(request):
        return redirect
    dau = await repo.get_daily_active_users()
    max_dau = max((d["active_users"] for d in dau), default=1) or 1
    return render(request, "analytics.html", dau=dau, max_dau=max_dau)


@app.get("/notifications", response_class=HTMLResponse)
async def notifications_page(request: Request, repo: RepoDep):
    if redirect := require_admin(request):
        return redirect
    users = await repo.list_users()
    return render(request, "notifications.html", users=users)


@app.post("/notifications")
async def send_notification(
    request: Request,
    repo: RepoDep,
    title: Annotated[str, Form()],
    body: Annotated[str, Form()],
    user_id: Annotated[str, Form()] = "",
):
    if redirect := require_admin(request):
        return redirect
    sent_count = await repo.send_notification(user_id or None, title, body)
    users = await repo.list_users()
    return render(
        request,
        "notifications.html",
        users=users,
        flash=f"Xabar {sent_count} ta foydalanuvchiga yuborildi",
    )
