"""Messaging channel adapters."""

from app.integrations.channels.base_channel import ChannelAdapter
from app.integrations.channels.demo_channel import DemoChannelAdapter
from app.integrations.channels.meta_channels import (
    InstagramAdapter,
    WebsiteChatAdapter,
    WhatsAppAdapter,
)
from app.integrations.channels.telegram_channel import TelegramAdapter

__all__ = [
    "ChannelAdapter",
    "DemoChannelAdapter",
    "TelegramAdapter",
    "WhatsAppAdapter",
    "InstagramAdapter",
    "WebsiteChatAdapter",
]
