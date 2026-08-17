"""Stress test - Smart Moliya Core Backend.

Ishga tushirish (server ishlab turgan bo'lishi kerak, masalan `uvicorn app.main:app`):

    pip install -r requirements-dev.txt
    locust -f locustfile.py --host http://localhost:8000

So'ng brauzerda http://localhost:8089 ochib, virtual foydalanuvchilar sonini
va spawn rate'ni belgilab, "Start swarming" bosing.
"""

import random
import uuid

from locust import HttpUser, between, task


class SmartMoliyaUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        self.phone = f"+99890{random.randint(1000000, 9999999)}"
        self.password = "StressTest123"
        self.device_id = str(uuid.uuid4())

        self.client.post(
            "/api/v1/auth/register",
            json={"phone": self.phone, "password": self.password, "full_name": "Load Test"},
        )
        response = self.client.post(
            "/api/v1/auth/login",
            json={"phone": self.phone, "password": self.password, "device_id": self.device_id},
        )
        token = response.json().get("access_token") if response.status_code == 200 else None
        self.headers = {"Authorization": f"Bearer {token}"} if token else {}
        self.wallet_id = None

        wallet_response = self.client.post(
            "/api/v1/wallets",
            json={"name": "Asosiy", "currency": "UZS"},
            headers=self.headers,
        )
        if wallet_response.status_code == 201:
            self.wallet_id = wallet_response.json()["id"]

    @task(3)
    def create_transaction(self):
        if not self.wallet_id:
            return
        self.client.post(
            "/api/v1/transactions",
            json={
                "wallet_id": self.wallet_id,
                "type": "expense",
                "amount": random.randint(5000, 200000),
                "note": "Load test xarajat",
                "occurred_at": "2026-07-12T10:00:00",
            },
            headers=self.headers,
        )

    @task(2)
    def list_transactions(self):
        self.client.get("/api/v1/transactions", headers=self.headers)

    @task(1)
    def get_dashboard_data(self):
        self.client.get("/api/v1/wallets", headers=self.headers)
        self.client.get("/api/v1/gamification/me", headers=self.headers)

    @task(1)
    def health_check(self):
        self.client.get("/health")
