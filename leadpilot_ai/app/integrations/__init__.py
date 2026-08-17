"""External service adapters. The UI never imports these directly."""

from app.integrations.base import (
    AdapterCredentials,
    AdapterResult,
    BaseAdapter,
    IncomingMessage,
)

__all__ = ["BaseAdapter", "AdapterResult", "AdapterCredentials", "IncomingMessage"]
