"""Speech-to-text adapters used for call recordings."""

from __future__ import annotations

import logging
from abc import abstractmethod
from pathlib import Path

import httpx

from app.integrations.base import AdapterResult, BaseAdapter
from app.utils.dates import now

logger = logging.getLogger(__name__)
TIMEOUT = 120.0


class TranscriberAdapter(BaseAdapter):
    """Convert an audio recording into text."""

    @abstractmethod
    def transcribe(self, audio_path: str, language: str = "uz") -> AdapterResult:
        """Return ``data['text']`` with the transcription."""


class MockTranscriber(TranscriberAdapter):
    """Offline transcriber: returns text already attached to the demo call."""

    provider = "demo_stt"
    title = "Demo transkripsiya"
    is_demo = True

    def __init__(self) -> None:
        super().__init__()
        self._canned: dict[str, str] = {}

    def register(self, audio_path: str, text: str) -> None:
        """Attach a scripted transcript to a (virtual) audio file."""
        self._canned[audio_path] = text

    def test_connection(self) -> AdapterResult:
        """Always available."""
        return AdapterResult.success("Demo transkriber faol")

    def transcribe(self, audio_path: str, language: str = "uz") -> AdapterResult:
        """Return the registered transcript, or a neutral placeholder."""
        self.last_sync_at = now()
        text = self._canned.get(audio_path, "")
        if not text:
            return AdapterResult.success(
                "Demo transkripsiya",
                text="Qo'ng'iroq yozuvi mavjud emas — demo rejimda transkript yaratilmadi.",
                confidence=0.0,
            )
        return AdapterResult.success("Demo transkripsiya", text=text, confidence=0.95)


class OpenAICompatibleTranscriber(TranscriberAdapter):
    """``/v1/audio/transcriptions`` client (Whisper-compatible)."""

    provider = "openai_stt"
    title = "OpenAI-compatible STT"

    def is_configured(self) -> bool:
        """Requires an API key."""
        return self.credentials.has("api_key")

    def test_connection(self) -> AdapterResult:
        """Validate the key by listing models."""
        if not self.is_configured():
            return AdapterResult.failure("API key kiritilmagan", "not_configured")
        base = (self.credentials.get("base_url", "https://api.openai.com/v1")).rstrip("/")
        try:
            response = httpx.get(
                f"{base}/models",
                headers={"Authorization": f"Bearer {self.credentials.get('api_key')}"},
                timeout=30.0,
            )
        except Exception as exc:
            self.last_error = type(exc).__name__
            return AdapterResult.failure(f"Ulanib bo'lmadi: {type(exc).__name__}", "network")
        if response.status_code >= 400:
            self.last_error = f"HTTP {response.status_code}"
            return AdapterResult.failure(self.last_error, "api")
        self.last_error = ""
        self.last_sync_at = now()
        return AdapterResult.success("STT ulandi")

    def transcribe(self, audio_path: str, language: str = "uz") -> AdapterResult:
        """Upload the audio file and return the transcription."""
        if not self.is_configured():
            return AdapterResult.failure("STT sozlanmagan", "not_configured")
        path = Path(audio_path)
        if not path.exists():
            return AdapterResult.failure("Audio fayl topilmadi", "missing_file")
        base = (self.credentials.get("base_url", "https://api.openai.com/v1")).rstrip("/")
        model = self.credentials.get("model", "whisper-1") or "whisper-1"
        try:
            with path.open("rb") as handle:
                response = httpx.post(
                    f"{base}/audio/transcriptions",
                    headers={"Authorization": f"Bearer {self.credentials.get('api_key')}"},
                    data={"model": model, "language": language},
                    files={"file": (path.name, handle)},
                    timeout=TIMEOUT,
                )
            payload = response.json()
        except Exception as exc:
            self.last_error = type(exc).__name__
            return AdapterResult.failure(f"Transkripsiya xatosi: {type(exc).__name__}", "network")
        if response.status_code >= 400:
            self.last_error = str(payload.get("error", {}).get("message", ""))
            return AdapterResult.failure(self.last_error, "api")
        self.last_sync_at = now()
        return AdapterResult.success(
            "Transkripsiya tayyor", text=payload.get("text", ""), confidence=0.9
        )
