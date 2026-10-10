"""Backend API klienti. Access token muddati tugasa, refresh token bilan bir marta yangilaydi."""

import threading
from typing import Any

import httpx


class ApiError(Exception):
    def __init__(self, status: int, title: str, detail: Any = None) -> None:
        super().__init__(f"{status} {title}")
        self.status = status
        self.title = title
        self.detail = detail

    @property
    def message(self) -> str:
        if isinstance(self.detail, str) and self.detail:
            return f"{self.title}: {self.detail}"
        return self.title


class ApiClient:
    def __init__(self, base_url: str, *, transport: httpx.BaseTransport | None = None) -> None:
        self._http = httpx.Client(base_url=base_url, timeout=10.0, transport=transport)
        self._access: str | None = None
        self._refresh: str | None = None
        self._lock = threading.Lock()

    def close(self) -> None:
        self._http.close()

    # --- autentifikatsiya -------------------------------------------------

    def login(self, email: str, password: str) -> None:
        data = self._send("POST", "/v1/auth/login", json={"email": email, "password": password}, auth=False)
        self._store_tokens(data)

    def _store_tokens(self, data: dict[str, Any]) -> None:
        self._access = data["access_token"]
        self._refresh = data["refresh_token"]

    def _try_refresh(self) -> bool:
        if not self._refresh:
            return False
        resp = self._http.post("/v1/auth/refresh", json={"refresh_token": self._refresh})
        if resp.status_code != 200:
            return False
        self._store_tokens(resp.json())
        return True

    # --- so'rovlar --------------------------------------------------------

    def _send(
        self,
        method: str,
        path: str,
        *,
        json: Any = None,
        params: dict[str, Any] | None = None,
        auth: bool = True,
    ) -> Any:
        resp = self._raw(method, path, json=json, params=params, auth=auth)
        if resp.status_code == 401 and auth:
            with self._lock:
                refreshed = self._try_refresh()
            if refreshed:
                resp = self._raw(method, path, json=json, params=params, auth=auth)

        if resp.status_code >= 400:
            raise _error_from(resp)
        if resp.status_code == 204 or not resp.content:
            return None
        return resp.json()

    def _raw(
        self, method: str, path: str, *, json: Any, params: dict[str, Any] | None, auth: bool
    ) -> httpx.Response:
        headers = {"Authorization": f"Bearer {self._access}"} if auth and self._access else {}
        return self._http.request(method, path, json=json, params=params, headers=headers)

    def me(self) -> dict[str, Any]:
        return self._send("GET", "/v1/me")

    def stores(self) -> list[dict[str, Any]]:
        return self._send("GET", "/v1/stores")

    def current_shift(self, store_id: str) -> dict[str, Any] | None:
        try:
            return self._send("GET", "/v1/shifts/current", params={"store_id": store_id})
        except ApiError as exc:
            if exc.status == 409:  # ochiq smena yo'q
                return None
            raise

    def open_shift(self, store_id: str, opening_cash: int) -> dict[str, Any]:
        return self._send("POST", "/v1/shifts", json={"store_id": store_id, "opening_cash": opening_cash})

    def close_shift(self, shift_id: str, closing_cash: int) -> dict[str, Any]:
        return self._send("POST", f"/v1/shifts/{shift_id}/close", json={"closing_cash": closing_cash})

    def product_by_barcode(self, code: str, store_id: str) -> dict[str, Any] | None:
        try:
            return self._send("GET", f"/v1/products/by-barcode/{code}", params={"store_id": store_id})
        except ApiError as exc:
            if exc.status == 404:
                return None
            raise

    def search_products(self, query: str, store_id: str, limit: int = 30) -> list[dict[str, Any]]:
        page = self._send("GET", "/v1/products", params={"q": query, "store_id": store_id, "limit": limit})
        return page["items"]

    def create_sale(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._send("POST", "/v1/sales", json=payload)

    def list_sales(self, store_id: str, limit: int = 30) -> list[dict[str, Any]]:
        return self._send("GET", "/v1/sales", params={"store_id": store_id, "limit": limit})

    def refund_sale(self, sale_id: str) -> dict[str, Any]:
        return self._send("POST", f"/v1/sales/{sale_id}/refund")


def _error_from(resp: httpx.Response) -> ApiError:
    try:
        body = resp.json()
        title = str(body.get("title", resp.reason_phrase))
        detail = body.get("detail")
    except ValueError:
        title, detail = resp.reason_phrase or "Xatolik", None
    return ApiError(resp.status_code, title, detail if isinstance(detail, str) else None)
