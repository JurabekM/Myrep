"""WhatsApp Cloud API, Instagram Graph API and website-chat adapters.

All three share the same shape: a REST endpoint plus a webhook receiver.  The
desktop application has no public HTTP endpoint, therefore inbound traffic is
pulled from an optional relay URL configured by the customer.  When no relay is
configured, ``poll`` returns an empty list and the demo adapter takes over.
"""

from __future__ import annotations

import logging

import httpx

from app.integrations.base import AdapterCredentials, AdapterResult, IncomingMessage
from app.integrations.channels.base_channel import ChannelAdapter
from app.models.enums import Channel
from app.utils.dates import now
from app.utils.formatting import normalize_phone

logger = logging.getLogger(__name__)
TIMEOUT = 15.0


class _RelayPollingMixin:
    """Pull normalised inbound events from an optional webhook relay."""

    credentials: AdapterCredentials
    channel: str
    last_error: str
    last_sync_at: object

    def _poll_relay(self) -> list[IncomingMessage]:
        """Fetch pending events from ``relay_url`` (JSON list of events)."""
        relay = self.credentials.get("relay_url")
        if not relay:
            return []
        try:
            headers = {}
            token = self.credentials.get("relay_token")
            if token:
                headers["Authorization"] = f"Bearer {token}"
            response = httpx.get(relay, headers=headers, timeout=TIMEOUT)
            events = response.json()
        except Exception as exc:
            self.last_error = type(exc).__name__
            return []
        self.last_error = ""
        self.last_sync_at = now()
        messages: list[IncomingMessage] = []
        for event in events if isinstance(events, list) else []:
            messages.append(
                IncomingMessage(
                    channel=self.channel,
                    external_chat_id=str(event.get("chat_id", "")),
                    text=str(event.get("text", "")),
                    sender_name=str(event.get("name", "")),
                    sender_username=str(event.get("username", "")),
                    phone=normalize_phone(event.get("phone")),
                    external_message_id=str(event.get("message_id", "")),
                    utm={k: str(v) for k, v in (event.get("utm") or {}).items()},
                )
            )
        return messages


class WhatsAppAdapter(_RelayPollingMixin, ChannelAdapter):
    """WhatsApp Cloud API (Meta) adapter."""

    provider = "whatsapp"
    title = "WhatsApp Cloud API"
    channel = Channel.WHATSAPP

    def is_configured(self) -> bool:
        """Requires a phone number id and a permanent access token."""
        return self.credentials.has("phone_number_id", "access_token")

    def _endpoint(self) -> str:
        """Graph API messages endpoint."""
        version = self.credentials.get("api_version", "v20.0")
        return (
            f"https://graph.facebook.com/{version}/"
            f"{self.credentials.get('phone_number_id')}/messages"
        )

    def test_connection(self) -> AdapterResult:
        """Read the phone number object to validate the token."""
        if not self.is_configured():
            return AdapterResult.failure("Phone number ID va token kerak", "not_configured")
        version = self.credentials.get("api_version", "v20.0")
        url = f"https://graph.facebook.com/{version}/{self.credentials.get('phone_number_id')}"
        try:
            response = httpx.get(
                url,
                headers={"Authorization": f"Bearer {self.credentials.get('access_token')}"},
                timeout=TIMEOUT,
            )
            payload = response.json()
        except Exception as exc:
            self.last_error = type(exc).__name__
            return AdapterResult.failure(f"Ulanib bo'lmadi: {type(exc).__name__}", "network")
        if "error" in payload:
            self.last_error = str(payload["error"].get("message", ""))
            return AdapterResult.failure(self.last_error, "api")
        self.last_error = ""
        self.last_sync_at = now()
        return AdapterResult.success(payload.get("display_phone_number", "ulandi"))

    def send_message(
        self, chat_id: str, text: str, attachments: list[str] | None = None
    ) -> AdapterResult:
        """Send a WhatsApp text message."""
        if not self.is_configured():
            return AdapterResult.failure("WhatsApp sozlanmagan", "not_configured")
        try:
            response = httpx.post(
                self._endpoint(),
                headers={"Authorization": f"Bearer {self.credentials.get('access_token')}"},
                json={
                    "messaging_product": "whatsapp",
                    "to": chat_id,
                    "type": "text",
                    "text": {"body": text},
                },
                timeout=TIMEOUT,
            )
            payload = response.json()
        except Exception as exc:
            self.last_error = type(exc).__name__
            return AdapterResult.failure(f"Yuborilmadi: {type(exc).__name__}", "network")
        if "error" in payload:
            self.last_error = str(payload["error"].get("message", ""))
            return AdapterResult.failure(self.last_error, "api")
        ids = payload.get("messages", [{}])
        return AdapterResult.success("Yuborildi", external_id=ids[0].get("id", ""))

    def poll(self) -> list[IncomingMessage]:
        """Inbound traffic arrives through the configured relay."""
        return self._poll_relay()


class InstagramAdapter(_RelayPollingMixin, ChannelAdapter):
    """Instagram Messaging (Graph API) adapter."""

    provider = "instagram"
    title = "Instagram Graph API"
    channel = Channel.INSTAGRAM

    def is_configured(self) -> bool:
        """Requires an IG business account id and a page access token."""
        return self.credentials.has("ig_account_id", "access_token")

    def test_connection(self) -> AdapterResult:
        """Read the IG account object."""
        if not self.is_configured():
            return AdapterResult.failure("Instagram akkaunt ID va token kerak", "not_configured")
        version = self.credentials.get("api_version", "v20.0")
        url = f"https://graph.facebook.com/{version}/{self.credentials.get('ig_account_id')}"
        try:
            response = httpx.get(
                url,
                params={"fields": "username"},
                headers={"Authorization": f"Bearer {self.credentials.get('access_token')}"},
                timeout=TIMEOUT,
            )
            payload = response.json()
        except Exception as exc:
            self.last_error = type(exc).__name__
            return AdapterResult.failure(f"Ulanib bo'lmadi: {type(exc).__name__}", "network")
        if "error" in payload:
            self.last_error = str(payload["error"].get("message", ""))
            return AdapterResult.failure(self.last_error, "api")
        self.last_error = ""
        self.last_sync_at = now()
        return AdapterResult.success(f"@{payload.get('username', '')} ulandi")

    def send_message(
        self, chat_id: str, text: str, attachments: list[str] | None = None
    ) -> AdapterResult:
        """Send an Instagram direct message."""
        if not self.is_configured():
            return AdapterResult.failure("Instagram sozlanmagan", "not_configured")
        version = self.credentials.get("api_version", "v20.0")
        url = (
            f"https://graph.facebook.com/{version}/{self.credentials.get('ig_account_id')}/messages"
        )
        try:
            response = httpx.post(
                url,
                headers={"Authorization": f"Bearer {self.credentials.get('access_token')}"},
                json={"recipient": {"id": chat_id}, "message": {"text": text}},
                timeout=TIMEOUT,
            )
            payload = response.json()
        except Exception as exc:
            self.last_error = type(exc).__name__
            return AdapterResult.failure(f"Yuborilmadi: {type(exc).__name__}", "network")
        if "error" in payload:
            self.last_error = str(payload["error"].get("message", ""))
            return AdapterResult.failure(self.last_error, "api")
        return AdapterResult.success("Yuborildi", external_id=payload.get("message_id", ""))

    def poll(self) -> list[IncomingMessage]:
        """Inbound traffic arrives through the configured relay."""
        return self._poll_relay()


class WebsiteChatAdapter(_RelayPollingMixin, ChannelAdapter):
    """Website widget adapter that speaks to the customer's own chat backend."""

    provider = "website"
    title = "Website chat"
    channel = Channel.WEBSITE

    def is_configured(self) -> bool:
        """Requires the relay/base URL of the site chat backend."""
        return self.credentials.has("relay_url")

    def test_connection(self) -> AdapterResult:
        """GET the relay URL and expect a JSON array."""
        if not self.is_configured():
            return AdapterResult.failure("Website chat URL kiritilmagan", "not_configured")
        try:
            response = httpx.get(self.credentials.get("relay_url"), timeout=TIMEOUT)
            response.raise_for_status()
        except Exception as exc:
            self.last_error = type(exc).__name__
            return AdapterResult.failure(f"Ulanib bo'lmadi: {type(exc).__name__}", "network")
        self.last_error = ""
        self.last_sync_at = now()
        return AdapterResult.success("Website chat ulandi")

    def send_message(
        self, chat_id: str, text: str, attachments: list[str] | None = None
    ) -> AdapterResult:
        """POST the reply back to the website chat backend."""
        send_url = self.credentials.get("send_url") or self.credentials.get("relay_url")
        if not send_url:
            return AdapterResult.failure("Website chat sozlanmagan", "not_configured")
        try:
            response = httpx.post(
                send_url, json={"chat_id": chat_id, "text": text}, timeout=TIMEOUT
            )
            response.raise_for_status()
        except Exception as exc:
            self.last_error = type(exc).__name__
            return AdapterResult.failure(f"Yuborilmadi: {type(exc).__name__}", "network")
        return AdapterResult.success("Yuborildi")

    def poll(self) -> list[IncomingMessage]:
        """Pull queued website chat messages."""
        return self._poll_relay()
