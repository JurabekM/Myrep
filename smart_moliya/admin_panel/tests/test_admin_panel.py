from datetime import datetime

from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.repository import AdminRepository, get_repository


class FakeAdminRepository(AdminRepository):
    def __init__(self):
        self.users = [
            {
                "id": "u-1",
                "phone": "+998901112233",
                "email": None,
                "full_name": "Test User",
                "auth_provider": "PHONE",
                "is_active": True,
                "created_at": datetime(2026, 7, 1),
            }
        ]
        self.sent_notifications: list[tuple] = []
        self.toggled: list[tuple] = []

    async def get_dashboard_stats(self):
        return {
            "users_total": 1,
            "users_active": 1,
            "transactions_total": 5,
            "expense_volume": 350000.0,
            "monthly_active_users": 1,
        }

    async def list_users(self, limit: int = 100):
        return self.users

    async def set_user_active(self, user_id: str, is_active: bool):
        self.toggled.append((user_id, is_active))

    async def list_transactions(self, limit: int = 100):
        return [
            {
                "id": "t-1",
                "user_id": "u-1",
                "phone": "+998901112233",
                "type": "EXPENSE",
                "amount": 50000,
                "currency": "UZS",
                "note": "Test",
                "occurred_at": datetime(2026, 7, 10, 12, 0),
            }
        ]

    async def find_suspicious_transactions(self, limit: int = 50):
        return [
            {
                "id": "t-9",
                "user_id": "u-1",
                "phone": "+998901112233",
                "amount": 5000000,
                "currency": "UZS",
                "note": "Katta xarajat",
                "occurred_at": datetime(2026, 7, 11, 9, 0),
                "z_score": 4.2,
            }
        ]

    async def get_daily_active_users(self, days: int = 14):
        return [{"day": "2026-07-10", "active_users": 3}, {"day": "2026-07-11", "active_users": 5}]

    async def send_notification(self, user_id, title, body):
        self.sent_notifications.append((user_id, title, body))
        return 1 if user_id else 42


fake_repo = FakeAdminRepository()
app.dependency_overrides[get_repository] = lambda: fake_repo

client = TestClient(app)


def _login(test_client: TestClient) -> None:
    test_client.post(
        "/login",
        data={"username": settings.ADMIN_USERNAME, "password": settings.ADMIN_PASSWORD},
    )


def test_unauthenticated_dashboard_redirects_to_login():
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_login_with_wrong_password_shows_error():
    response = client.post("/login", data={"username": "admin", "password": "wrong"})
    assert response.status_code == 401
    # Jinja apostrofni HTML-escape qiladi, shuning uchun apostrofsiz qismini tekshiramiz
    assert "Login yoki parol" in response.text


def test_login_sets_session_cookie_and_opens_dashboard():
    with TestClient(app) as c:
        _login(c)
        response = c.get("/")
        assert response.status_code == 200
        assert "Dashboard" in response.text
        assert "350,000" in response.text  # expense_volume formatlangan


def test_users_page_lists_users_and_toggle_works():
    with TestClient(app) as c:
        _login(c)
        response = c.get("/users")
        assert response.status_code == 200
        assert "+998901112233" in response.text

        c.post("/users/u-1/toggle")
        assert fake_repo.toggled[-1] == ("u-1", False)  # faol edi -> bloklash


def test_fraud_page_shows_suspicious_transactions():
    with TestClient(app) as c:
        _login(c)
        response = c.get("/fraud")
        assert response.status_code == 200
        assert "4.2" in response.text


def test_analytics_page_renders_dau():
    with TestClient(app) as c:
        _login(c)
        response = c.get("/analytics")
        assert response.status_code == 200
        assert "2026-07-11" in response.text


def test_broadcast_notification_reports_count():
    with TestClient(app) as c:
        _login(c)
        response = c.post(
            "/notifications", data={"user_id": "", "title": "Yangilik", "body": "Yangi versiya chiqdi"}
        )
        assert response.status_code == 200
        assert "42 ta foydalanuvchiga" in response.text
        assert fake_repo.sent_notifications[-1] == (None, "Yangilik", "Yangi versiya chiqdi")


def test_logout_clears_session():
    with TestClient(app) as c:
        _login(c)
        c.get("/logout")
        response = c.get("/", follow_redirects=False)
        assert response.status_code == 303
