"""Outbound CRM exporters (internal, Bitrix24, amoCRM, generic webhook)."""

from __future__ import annotations

import json
import logging
from abc import abstractmethod
from typing import Any

import httpx

from app.integrations.base import AdapterResult, BaseAdapter
from app.utils.dates import now

logger = logging.getLogger(__name__)
TIMEOUT = 20.0


class CRMExporter(BaseAdapter):
    """Push a lead (and its status changes) to an external CRM."""

    @abstractmethod
    def export_lead(self, payload: dict[str, Any]) -> AdapterResult:
        """Create or update the lead in the target system."""


class InternalCRMExporter(CRMExporter):
    """No-op exporter: LeadPilot itself is the CRM of record."""

    provider = "internal"
    title = "Ichki CRM"
    is_demo = True

    def test_connection(self) -> AdapterResult:
        """Always available."""
        return AdapterResult.success("Ichki CRM faol")

    def export_lead(self, payload: dict[str, Any]) -> AdapterResult:
        """Nothing to do — the lead already lives in the local database."""
        return AdapterResult.success("Lead ichki CRMda saqlangan", lead_id=payload.get("id"))


class WebhookAdapter(CRMExporter):
    """POST the lead as JSON to a customer-provided webhook URL."""

    provider = "webhook"
    title = "Webhook"

    def is_configured(self) -> bool:
        """Requires a target URL."""
        return self.credentials.has("webhook_url")

    def _headers(self) -> dict[str, str]:
        """Optional bearer token header."""
        headers = {"Content-Type": "application/json"}
        token = self.credentials.get("webhook_token")
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    def test_connection(self) -> AdapterResult:
        """Send a ping payload."""
        if not self.is_configured():
            return AdapterResult.failure("Webhook URL kiritilmagan", "not_configured")
        try:
            response = httpx.post(
                self.credentials.get("webhook_url"),
                headers=self._headers(),
                content=json.dumps({"event": "ping", "source": "LeadPilot AI"}),
                timeout=TIMEOUT,
            )
            response.raise_for_status()
        except Exception as exc:
            self.last_error = type(exc).__name__
            return AdapterResult.failure(f"Ulanib bo'lmadi: {type(exc).__name__}", "network")
        self.last_error = ""
        self.last_sync_at = now()
        return AdapterResult.success("Webhook javob berdi")

    def export_lead(self, payload: dict[str, Any]) -> AdapterResult:
        """POST the lead payload."""
        if not self.is_configured():
            return AdapterResult.failure("Webhook sozlanmagan", "not_configured")
        try:
            response = httpx.post(
                self.credentials.get("webhook_url"),
                headers=self._headers(),
                content=json.dumps(
                    {"event": "lead", "lead": payload}, ensure_ascii=False, default=str
                ),
                timeout=TIMEOUT,
            )
            response.raise_for_status()
        except Exception as exc:
            self.last_error = type(exc).__name__
            return AdapterResult.failure(f"Yuborilmadi: {type(exc).__name__}", "network")
        self.last_sync_at = now()
        return AdapterResult.success("Webhookga yuborildi")


class Bitrix24Adapter(CRMExporter):
    """Bitrix24 inbound webhook adapter (``crm.lead.add``)."""

    provider = "bitrix24"
    title = "Bitrix24"

    def is_configured(self) -> bool:
        """Requires the inbound webhook base URL."""
        return self.credentials.has("webhook_base")

    def _url(self, method: str) -> str:
        """Build a REST method URL."""
        return f"{self.credentials.get('webhook_base').rstrip('/')}/{method}.json"

    def test_connection(self) -> AdapterResult:
        """Call ``profile`` to validate the webhook."""
        if not self.is_configured():
            return AdapterResult.failure("Bitrix24 webhook URL kerak", "not_configured")
        try:
            response = httpx.get(self._url("profile"), timeout=TIMEOUT)
            payload = response.json()
        except Exception as exc:
            self.last_error = type(exc).__name__
            return AdapterResult.failure(f"Ulanib bo'lmadi: {type(exc).__name__}", "network")
        if "error" in payload:
            self.last_error = str(payload.get("error_description", payload["error"]))
            return AdapterResult.failure(self.last_error, "api")
        self.last_error = ""
        self.last_sync_at = now()
        return AdapterResult.success("Bitrix24 ulandi")

    def export_lead(self, payload: dict[str, Any]) -> AdapterResult:
        """Create a Bitrix24 lead."""
        if not self.is_configured():
            return AdapterResult.failure("Bitrix24 sozlanmagan", "not_configured")
        fields = {
            "TITLE": payload.get("title") or f"LeadPilot #{payload.get('id')}",
            "NAME": payload.get("full_name", ""),
            "COMMENTS": payload.get("notes", ""),
            "SOURCE_DESCRIPTION": payload.get("source", ""),
            "UTM_SOURCE": payload.get("utm_source", ""),
            "UTM_CAMPAIGN": payload.get("utm_campaign", ""),
        }
        if payload.get("phone"):
            fields["PHONE"] = [{"VALUE": payload["phone"], "VALUE_TYPE": "WORK"}]
        try:
            response = httpx.post(
                self._url("crm.lead.add"), json={"fields": fields}, timeout=TIMEOUT
            )
            data = response.json()
        except Exception as exc:
            self.last_error = type(exc).__name__
            return AdapterResult.failure(f"Yuborilmadi: {type(exc).__name__}", "network")
        if "error" in data:
            self.last_error = str(data.get("error_description", ""))
            return AdapterResult.failure(self.last_error, "api")
        self.last_sync_at = now()
        return AdapterResult.success(
            "Bitrix24ga eksport qilindi", external_id=str(data.get("result", ""))
        )


class AmoCRMAdapter(CRMExporter):
    """amoCRM API v4 adapter (long-lived access token)."""

    provider = "amocrm"
    title = "amoCRM"

    def is_configured(self) -> bool:
        """Requires the subdomain host and an access token."""
        return self.credentials.has("base_url", "access_token")

    def _headers(self) -> dict[str, str]:
        """Bearer auth headers."""
        return {
            "Authorization": f"Bearer {self.credentials.get('access_token')}",
            "Content-Type": "application/json",
        }

    def test_connection(self) -> AdapterResult:
        """Read the account resource."""
        if not self.is_configured():
            return AdapterResult.failure("amoCRM URL va token kerak", "not_configured")
        base = self.credentials.get("base_url").rstrip("/")
        try:
            response = httpx.get(f"{base}/api/v4/account", headers=self._headers(), timeout=TIMEOUT)
        except Exception as exc:
            self.last_error = type(exc).__name__
            return AdapterResult.failure(f"Ulanib bo'lmadi: {type(exc).__name__}", "network")
        if response.status_code >= 400:
            self.last_error = f"HTTP {response.status_code}"
            return AdapterResult.failure(self.last_error, "api")
        self.last_error = ""
        self.last_sync_at = now()
        return AdapterResult.success("amoCRM ulandi")

    def export_lead(self, payload: dict[str, Any]) -> AdapterResult:
        """Create an amoCRM lead."""
        if not self.is_configured():
            return AdapterResult.failure("amoCRM sozlanmagan", "not_configured")
        base = self.credentials.get("base_url").rstrip("/")
        body = [
            {
                "name": payload.get("title") or f"LeadPilot #{payload.get('id')}",
                "price": int(payload.get("revenue") or 0),
                "_embedded": {"tags": [{"name": t} for t in payload.get("tags", [])]},
            }
        ]
        try:
            response = httpx.post(
                f"{base}/api/v4/leads", headers=self._headers(), json=body, timeout=TIMEOUT
            )
        except Exception as exc:
            self.last_error = type(exc).__name__
            return AdapterResult.failure(f"Yuborilmadi: {type(exc).__name__}", "network")
        if response.status_code >= 400:
            self.last_error = f"HTTP {response.status_code}"
            return AdapterResult.failure(self.last_error, "api")
        self.last_sync_at = now()
        return AdapterResult.success("amoCRMga eksport qilindi")


__all__ = [
    "CRMExporter",
    "InternalCRMExporter",
    "WebhookAdapter",
    "Bitrix24Adapter",
    "AmoCRMAdapter",
]
