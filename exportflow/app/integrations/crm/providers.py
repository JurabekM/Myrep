"""Outbound CRM adapters (Bitrix24, amoCRM, generic webhook)."""

from __future__ import annotations

from abc import abstractmethod

from app.integrations.base import BaseProvider, ProviderResult
from app.utils.logging_setup import get_logger

log = get_logger(__name__)


class CRMProvider(BaseProvider):
    """Pushes buyers and deals to an external CRM."""

    kind = "crm"

    @abstractmethod
    def push_lead(self, payload: dict) -> ProviderResult:
        """Send one lead/deal to the remote system."""


class WebhookAdapter(CRMProvider):
    """Posts a JSON payload to an arbitrary HTTPS endpoint."""

    code = "webhook"
    label = "Generic webhook"
    fields = (("url", "Webhook URL", False), ("token", "Bearer token", True))

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        token = self.secrets.get("token")
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    def test_connection(self) -> ProviderResult:
        """Send a ping payload to the webhook."""
        url = self.settings.get("url") or ""
        if not url:
            return ProviderResult.failure("Webhook URL is not configured")
        try:
            import httpx

            with httpx.Client(timeout=15) as client:
                response = client.post(url, headers=self._headers(), json={"event": "ping"})
            if response.status_code >= 400:
                return ProviderResult.failure(f"HTTP {response.status_code}")
            return ProviderResult.success("Webhook reachable")
        except Exception as exc:
            log.warning("Webhook test failed: %s", type(exc).__name__)
            return ProviderResult.failure(f"{type(exc).__name__}: {exc}")

    def push_lead(self, payload: dict) -> ProviderResult:
        """Deliver a lead payload to the webhook."""
        url = self.settings.get("url") or ""
        if not url:
            return ProviderResult.failure("Webhook URL is not configured")
        try:
            import httpx

            with httpx.Client(timeout=20) as client:
                response = client.post(
                    url, headers=self._headers(), json={"event": "lead", "data": payload}
                )
            if response.status_code >= 400:
                return ProviderResult.failure(f"HTTP {response.status_code}")
            return ProviderResult.success("Lead delivered")
        except Exception as exc:
            log.warning("Webhook push failed: %s", type(exc).__name__)
            return ProviderResult.failure(f"{type(exc).__name__}: {exc}")


class Bitrix24Adapter(CRMProvider):
    """Creates leads through a Bitrix24 inbound webhook."""

    code = "bitrix24"
    label = "Bitrix24"
    fields = (("webhook_url", "Inbound webhook URL", True),)

    def _url(self, method: str) -> str:
        base = (self.secrets.get("webhook_url") or "").rstrip("/")
        if not base:
            raise ValueError("Bitrix24 webhook URL is not configured")
        return f"{base}/{method}.json"

    def test_connection(self) -> ProviderResult:
        """Call ``profile`` to verify the webhook."""
        try:
            import httpx

            with httpx.Client(timeout=15) as client:
                response = client.get(self._url("profile"))
            if response.status_code >= 400:
                return ProviderResult.failure(f"HTTP {response.status_code}")
            return ProviderResult.success("Bitrix24 webhook is valid")
        except Exception as exc:
            return ProviderResult.failure(f"{type(exc).__name__}: {exc}")

    def push_lead(self, payload: dict) -> ProviderResult:
        """Create a CRM lead in Bitrix24."""
        try:
            import httpx

            body = {
                "fields": {
                    "TITLE": payload.get("title", "ExportFlow lead"),
                    "NAME": payload.get("contact_person", ""),
                    "COMPANY_TITLE": payload.get("company_name", ""),
                    "COMMENTS": payload.get("message", ""),
                    "OPPORTUNITY": payload.get("expected_value", 0),
                    "CURRENCY_ID": payload.get("currency", "USD"),
                }
            }
            with httpx.Client(timeout=20) as client:
                response = client.post(self._url("crm.lead.add"), json=body)
            if response.status_code >= 400:
                return ProviderResult.failure(f"HTTP {response.status_code}")
            return ProviderResult.success("Lead created in Bitrix24", data=response.json())
        except Exception as exc:
            return ProviderResult.failure(f"{type(exc).__name__}: {exc}")


class AmoCRMAdapter(CRMProvider):
    """Creates leads through the amoCRM REST API."""

    code = "amocrm"
    label = "amoCRM"
    fields = (("base_url", "Account URL", False), ("access_token", "Access token", True))

    def _headers(self) -> dict[str, str]:
        token = self.secrets.get("access_token") or ""
        if not token:
            raise ValueError("amoCRM access token is not configured")
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    def test_connection(self) -> ProviderResult:
        """Read the account profile to verify the token."""
        base = (self.settings.get("base_url") or "").rstrip("/")
        if not base:
            return ProviderResult.failure("Account URL is not configured")
        try:
            import httpx

            with httpx.Client(timeout=15) as client:
                response = client.get(f"{base}/api/v4/account", headers=self._headers())
            if response.status_code >= 400:
                return ProviderResult.failure(f"HTTP {response.status_code}")
            return ProviderResult.success("amoCRM connection successful")
        except Exception as exc:
            return ProviderResult.failure(f"{type(exc).__name__}: {exc}")

    def push_lead(self, payload: dict) -> ProviderResult:
        """Create a lead in amoCRM."""
        base = (self.settings.get("base_url") or "").rstrip("/")
        try:
            import httpx

            body = [
                {
                    "name": payload.get("title", "ExportFlow lead"),
                    "price": int(payload.get("expected_value") or 0),
                }
            ]
            with httpx.Client(timeout=20) as client:
                response = client.post(f"{base}/api/v4/leads", headers=self._headers(), json=body)
            if response.status_code >= 400:
                return ProviderResult.failure(f"HTTP {response.status_code}")
            return ProviderResult.success("Lead created in amoCRM")
        except Exception as exc:
            return ProviderResult.failure(f"{type(exc).__name__}: {exc}")
