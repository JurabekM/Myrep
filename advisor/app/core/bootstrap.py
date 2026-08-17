"""Ishga tushirish tekshiruvlari: bog'liqliklar, papkalar, baza.

``main.py`` ishga tushishida birinchi bo'lib chaqiriladi. Maqsad — foydalanuvchi
uchun tushunarli holat: nima o'rnatilgan, nima ixtiyoriy, AI qaysi rejimda
ishlaydi.
"""

from __future__ import annotations

import importlib.util
from dataclasses import dataclass

from app.core.config import AppConfig
from app.core.logging_setup import get_logger

logger = get_logger(__name__)

# (import nomi, pip nomi, majburiymi)
_REQUIRED = [
    ("PyQt6", "PyQt6", True),
    ("httpx", "httpx", True),
    ("bs4", "beautifulsoup4", True),
    ("sklearn", "scikit-learn", True),
    ("numpy", "numpy", True),
    ("matplotlib", "matplotlib", True),
]
_OPTIONAL = [
    ("pypdf", "pypdf", "PDF o'qish"),
    ("docx", "python-docx", "Word o'qish"),
    ("openpyxl", "openpyxl", "Excel o'qish"),
    ("PIL", "Pillow", "Rasm bilan ishlash"),
    ("pytesseract", "pytesseract", "Rasmdan matn (OCR)"),
    ("llama_cpp", "llama-cpp-python", "Oflayn lokal AI model"),
    ("pyttsx3", "pyttsx3", "Ovozli javob (TTS)"),
]


def _is_installed(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


@dataclass
class EnvironmentReport:
    missing_required: list[str]
    missing_optional: list[tuple[str, str]]  # (pip nomi, tavsif)
    cloud_ai_available: bool
    local_ai_available: bool

    @property
    def ok(self) -> bool:
        return not self.missing_required

    @property
    def ai_mode(self) -> str:
        if self.cloud_ai_available and self.local_ai_available:
            return "gibrid (bepul API + oflayn model)"
        if self.cloud_ai_available:
            return "bepul API"
        if self.local_ai_available:
            return "faqat oflayn lokal model"
        return "sozlanmagan"


def check_environment(config: AppConfig) -> EnvironmentReport:
    missing_required = [
        pip for mod, pip, _ in _REQUIRED if not _is_installed(mod)
    ]
    missing_optional = [
        (pip, desc) for mod, pip, desc in _OPTIONAL if not _is_installed(mod)
    ]
    local_ai = _is_installed("llama_cpp") and _has_local_model(config)
    report = EnvironmentReport(
        missing_required=missing_required,
        missing_optional=missing_optional,
        cloud_ai_available=config.has_any_cloud_key(),
        local_ai_available=local_ai,
    )
    logger.info("Muhit tekshiruvi: AI rejimi = %s", report.ai_mode)
    if missing_required:
        logger.error("Majburiy paketlar yetishmaydi: %s", ", ".join(missing_required))
    return report


def _has_local_model(config: AppConfig) -> bool:
    models_dir = config.paths.models_dir
    if config.ai.local_model_filename:
        return (models_dir / config.ai.local_model_filename).exists()
    return any(models_dir.glob("*.gguf"))
