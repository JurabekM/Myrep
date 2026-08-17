"""Ovoz servisi — oflayn Text-to-Speech (pyttsx3).

Speech-to-Text ixtiyoriy va platformaga bog'liq (SAPI/Whisper), shuning uchun
bu yerda faqat oflayn TTS taqdim etiladi; kutubxona bo'lmasa, ``is_available``
False qaytaradi va UI tegishli tugmani yashiradi.
"""

from __future__ import annotations

import threading

from app.core.logging_setup import get_logger

logger = get_logger(__name__)


class VoiceService:
    def __init__(self) -> None:
        self._lock = threading.Lock()

    def is_available(self) -> bool:
        try:
            import pyttsx3  # noqa: F401
        except ImportError:
            return False
        return True

    def speak(self, text: str) -> None:
        """Matnni ovozga aylantiradi (bloklovchi — fon workerida chaqiring)."""
        try:
            import pyttsx3
        except ImportError:
            logger.info("pyttsx3 o'rnatilmagan — TTS o'tkazib yuborildi")
            return
        # pyttsx3 driver'i thread-safe emas; bitta vaqtda bitta nutq.
        with self._lock:
            engine = pyttsx3.init()
            engine.say(text)
            engine.runAndWait()
            engine.stop()
