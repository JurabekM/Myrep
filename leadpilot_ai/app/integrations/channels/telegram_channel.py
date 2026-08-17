"""Telegram Bot API channel adapter."""

from __future__ import annotations

import logging

import httpx

from app.integrations.base import AdapterCredentials, AdapterResult, IncomingMessage
from app.integrations.channels.base_channel import ChannelAdapter
from app.models.enums import Channel
from app.utils.dates import now
from app.utils.formatting import normalize_phone

logger = logging.getLogger(__name__)

API_ROOT = "https://api.telegram.org"
TIMEOUT = 15.0


class TelegramAdapter(ChannelAdapter):
    """Long-polling Telegram bot integration (``getUpdates`` / ``sendMessage``)."""

    provider = "telegram"
    title = "Telegram Bot API"
    channel = Channel.TELEGRAM

    def __init__(self, credentials: AdapterCredentials | None = None) -> None:
        super().__init__(credentials)
        self._offset: int = int(self.credentials.settings.get("offset", 0) or 0)

    # ------------------------------------------------------------------ #
    def is_configured(self) -> bool:
        """A bot token is the only mandatory credential."""
        return self.credentials.has("bot_token")

    def _url(self, method: str) -> str:
        """Build a Bot API endpoint URL."""
        return f"{API_ROOT}/bot{self.credentials.get('bot_token')}/{method}"

    def test_connection(self) -> AdapterResult:
        """Call ``getMe`` to validate the token."""
        if not self.is_configured():
            return AdapterResult.failure("Bot token kiritilmagan", "not_configured")
        try:
            response = httpx.get(self._url("getMe"), timeout=TIMEOUT)
            payload = response.json()
        except Exception as exc:
            self.last_error = type(exc).__name__
            return AdapterResult.failure(f"Ulanib bo'lmadi: {type(exc).__name__}", "network")
        if not payload.get("ok"):
            self.last_error = str(payload.get("description", "unknown"))
            return AdapterResult.failure(self.last_error, "api")
        self.last_error = ""
        self.last_sync_at = now()
        bot = payload.get("result", {})
        return AdapterResult.success(
            f"@{bot.get('username', '?')} ulandi", username=bot.get("username", "")
        )

    def send_message(
        self, chat_id: str, text: str, attachments: list[str] | None = None
    ) -> AdapterResult:
        """Send a text message; attachments are uploaded one by one."""
        if not self.is_configured():
            return AdapterResult.failure("Bot token kiritilmagan", "not_configured")
        try:
            response = httpx.post(
                self._url("sendMessage"),
                json={"chat_id": chat_id, "text": text, "disable_web_page_preview": True},
                timeout=TIMEOUT,
            )
            payload = response.json()
        except Exception as exc:
            self.last_error = type(exc).__name__
            return AdapterResult.failure(f"Yuborilmadi: {type(exc).__name__}", "network")
        if not payload.get("ok"):
            self.last_error = str(payload.get("description", ""))
            return AdapterResult.failure(self.last_error, "api")
        self.last_sync_at = now()
        message_id = payload.get("result", {}).get("message_id", "")
        for path in attachments or []:
            self._send_document(chat_id, path)
        return AdapterResult.success("Yuborildi", external_id=str(message_id))

    def _send_document(self, chat_id: str, path: str) -> None:
        """Upload one file, logging but swallowing failures."""
        try:
            with open(path, "rb") as handle:
                httpx.post(
                    self._url("sendDocument"),
                    data={"chat_id": chat_id},
                    files={"document": handle},
                    timeout=60.0,
                )
        except Exception as exc:  # pragma: no cover - network path
            logger.warning("Telegram document upload failed: %s", type(exc).__name__)

    def poll(self) -> list[IncomingMessage]:
        """Fetch new updates via long polling."""
        if not self.is_configured():
            return []
        try:
            response = httpx.get(
                self._url("getUpdates"),
                params={"offset": self._offset + 1, "timeout": 0, "limit": 50},
                timeout=TIMEOUT,
            )
            payload = response.json()
        except Exception as exc:
            self.last_error = type(exc).__name__
            return []
        if not payload.get("ok"):
            self.last_error = str(payload.get("description", ""))
            return []
        self.last_error = ""
        self.last_sync_at = now()
        messages: list[IncomingMessage] = []
        for update in payload.get("result", []):
            self._offset = max(self._offset, int(update.get("update_id", 0)))
            raw = update.get("message") or update.get("edited_message")
            if not raw:
                continue
            chat = raw.get("chat", {})
            sender = raw.get("from", {})
            contact = raw.get("contact", {})
            messages.append(
                IncomingMessage(
                    channel=Channel.TELEGRAM,
                    external_chat_id=str(chat.get("id", "")),
                    text=raw.get("text", "") or raw.get("caption", ""),
                    sender_name=" ".join(
                        x for x in [sender.get("first_name"), sender.get("last_name")] if x
                    ),
                    sender_username=sender.get("username", "") or "",
                    phone=normalize_phone(contact.get("phone_number")),
                    external_message_id=str(raw.get("message_id", "")),
                )
            )
        return messages
