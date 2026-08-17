"""Email providers: an offline demo outbox and a real SMTP adapter."""

from __future__ import annotations

import json
import smtplib
from abc import abstractmethod
from dataclasses import dataclass, field
from email.message import EmailMessage as MimeMessage
from pathlib import Path

from app.config import PATHS
from app.integrations.base import BaseProvider, ProviderResult
from app.utils.formatting import now
from app.utils.logging_setup import get_logger

log = get_logger(__name__)


@dataclass
class OutgoingEmail:
    """A message handed to an email provider."""

    to_address: str
    subject: str
    body: str
    cc_address: str = ""
    attachments: list[str] = field(default_factory=list)


class EmailProvider(BaseProvider):
    """Sends outgoing email on behalf of the export team."""

    kind = "email"

    @abstractmethod
    def send(self, message: OutgoingEmail) -> ProviderResult:
        """Deliver a message; returns a failure result instead of raising."""


class DemoOutboxProvider(EmailProvider):
    """Writes every message to ``<data>/outbox`` as an ``.eml``-like text file."""

    code = "demo_outbox"
    label = "Demo outbox (offline)"
    is_demo = True

    def test_connection(self) -> ProviderResult:
        """The outbox folder is always writable."""
        PATHS.ensure()
        return ProviderResult.success(f"Outbox: {PATHS.outbox_dir}")

    def describe(self) -> str:
        return f"Messages are stored in {PATHS.outbox_dir}"

    def send(self, message: OutgoingEmail) -> ProviderResult:
        """Persist the message on disk instead of transmitting it."""
        PATHS.ensure()
        stamp = now().strftime("%Y%m%d-%H%M%S-%f")
        target = PATHS.outbox_dir / f"{stamp}.txt"
        content = (
            f"To: {message.to_address}\n"
            f"Cc: {message.cc_address}\n"
            f"Subject: {message.subject}\n"
            f"Attachments: {json.dumps(message.attachments)}\n"
            f"Date: {now().isoformat()}\n"
            f"{'-' * 60}\n"
            f"{message.body}\n"
        )
        target.write_text(content, encoding="utf-8")
        return ProviderResult.success("Saved to the demo outbox", data=str(target))


class SMTPProvider(EmailProvider):
    """Standard SMTP adapter (STARTTLS or implicit TLS)."""

    code = "smtp"
    label = "SMTP"
    fields = (
        ("host", "SMTP host", False),
        ("port", "Port", False),
        ("username", "Username", False),
        ("password", "Password", True),
        ("from_address", "From address", False),
        ("use_tls", "Use STARTTLS (1/0)", False),
        ("use_ssl", "Use SSL (1/0)", False),
    )

    def _connect(self) -> smtplib.SMTP:
        host = self.settings.get("host") or ""
        port = int(self.settings.get("port") or 587)
        if not host:
            raise ValueError("SMTP host is not configured")
        if str(self.settings.get("use_ssl") or "0") == "1":
            server: smtplib.SMTP = smtplib.SMTP_SSL(host, port, timeout=25)
        else:
            server = smtplib.SMTP(host, port, timeout=25)
            if str(self.settings.get("use_tls") or "1") == "1":
                server.starttls()
        username = self.settings.get("username") or ""
        password = self.secrets.get("password") or ""
        if username and password:
            server.login(username, password)
        return server

    def test_connection(self) -> ProviderResult:
        """Open an SMTP session and immediately close it."""
        try:
            server = self._connect()
            server.quit()
            return ProviderResult.success("SMTP connection successful")
        except Exception as exc:
            log.warning("SMTP test failed: %s", type(exc).__name__)
            return ProviderResult.failure(f"{type(exc).__name__}: {exc}")

    def send(self, message: OutgoingEmail) -> ProviderResult:
        """Transmit a message with optional file attachments."""
        try:
            mime = MimeMessage()
            mime["From"] = self.settings.get("from_address") or self.settings.get("username") or ""
            mime["To"] = message.to_address
            if message.cc_address:
                mime["Cc"] = message.cc_address
            mime["Subject"] = message.subject
            mime.set_content(message.body)
            for path_str in message.attachments:
                path = Path(path_str)
                if not path.exists():
                    continue
                mime.add_attachment(
                    path.read_bytes(),
                    maintype="application",
                    subtype="octet-stream",
                    filename=path.name,
                )
            server = self._connect()
            try:
                server.send_message(mime)
            finally:
                server.quit()
            return ProviderResult.success("Message sent")
        except Exception as exc:
            log.warning("SMTP send failed: %s", type(exc).__name__)
            return ProviderResult.failure(f"{type(exc).__name__}: {exc}")
