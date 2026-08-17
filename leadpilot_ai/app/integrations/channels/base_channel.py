"""Channel adapter contract (Telegram, WhatsApp, Instagram, website chat, demo)."""

from __future__ import annotations

from abc import abstractmethod

from app.integrations.base import AdapterResult, BaseAdapter, IncomingMessage


class ChannelAdapter(BaseAdapter):
    """Send and receive text messages on one messaging channel."""

    #: Value of :class:`~app.models.enums.Channel` served by this adapter.
    channel: str = "demo"

    @abstractmethod
    def send_message(
        self, chat_id: str, text: str, attachments: list[str] | None = None
    ) -> AdapterResult:
        """Deliver an outbound message to the customer."""

    @abstractmethod
    def poll(self) -> list[IncomingMessage]:
        """Return messages that arrived since the previous call."""

    def supports_attachments(self) -> bool:
        """Whether files can be attached to outbound messages."""
        return True
