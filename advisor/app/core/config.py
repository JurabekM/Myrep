"""Application configuration.

Standalone tizim uchun barcha sozlamalar foydalanuvchi papkasidagi bitta
JSON faylda saqlanadi (``~/.ai_advisor/config.json``). API kalitlar shu
yerda yoki muhit o'zgaruvchilarida bo'lishi mumkin — hech biri majburiy emas
(kalitsiz tizim lokal model bilan ishlaydi).
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path

APP_DIR_NAME = ".ai_advisor"


def _app_home() -> Path:
    home = Path(os.environ.get("AI_ADVISOR_HOME", Path.home() / APP_DIR_NAME))
    home.mkdir(parents=True, exist_ok=True)
    return home


@dataclass
class Paths:
    home: Path = field(default_factory=_app_home)

    @property
    def config_file(self) -> Path:
        return self.home / "config.json"

    @property
    def database_file(self) -> Path:
        return self.home / "advisor.db"

    @property
    def log_file(self) -> Path:
        return self.home / "advisor.log"

    @property
    def models_dir(self) -> Path:
        d = self.home / "models"
        d.mkdir(parents=True, exist_ok=True)
        return d

    @property
    def uploads_dir(self) -> Path:
        d = self.home / "uploads"
        d.mkdir(parents=True, exist_ok=True)
        return d


@dataclass
class AIConfig:
    """Bepul provayderlar kalitlari (ixtiyoriy) va lokal model sozlamasi."""

    groq_api_key: str = ""
    gemini_api_key: str = ""
    openrouter_api_key: str = ""

    groq_model: str = "llama-3.3-70b-versatile"
    gemini_model: str = "gemini-2.0-flash"
    openrouter_model: str = "meta-llama/llama-3.3-70b-instruct:free"

    # Lokal GGUF model fayli nomi (models_dir ichida). Bo'sh bo'lsa avtomatik
    # aniqlanadi (papkadagi birinchi .gguf fayl).
    local_model_filename: str = ""
    local_context_size: int = 4096

    # Provayderlarni sinash tartibi.
    provider_order: list[str] = field(
        default_factory=lambda: ["groq", "gemini", "openrouter", "local"]
    )

    temperature: float = 0.4
    max_tokens: int = 2048


@dataclass
class BusinessProfile:
    """Foydalanuvchi biznes profili — AI javoblarini shaxsiylashtirish uchun."""

    industry: str = ""
    business_type: str = ""  # ytt / mchj / microfirm / startup / freelancer
    location: str = ""
    employees: int = 0
    goals: str = ""


@dataclass
class AppConfig:
    ai: AIConfig = field(default_factory=AIConfig)
    profile: BusinessProfile = field(default_factory=BusinessProfile)
    locale: str = "uz"
    paths: Paths = field(default_factory=Paths)

    # ---------------------------------------------------------------- persist

    @classmethod
    def load(cls) -> AppConfig:
        paths = Paths()
        config = cls(paths=paths)
        if paths.config_file.exists():
            try:
                data = json.loads(paths.config_file.read_text(encoding="utf-8"))
                config.ai = AIConfig(**{**asdict(config.ai), **data.get("ai", {})})
                config.profile = BusinessProfile(
                    **{**asdict(config.profile), **data.get("profile", {})}
                )
                config.locale = data.get("locale", config.locale)
            except (json.JSONDecodeError, TypeError):
                # Buzilgan konfig — standart qiymatlar bilan davom etamiz.
                pass
        config._apply_env_overrides()
        return config

    def save(self) -> None:
        data = {
            "ai": asdict(self.ai),
            "profile": asdict(self.profile),
            "locale": self.locale,
        }
        self.paths.config_file.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def _apply_env_overrides(self) -> None:
        env_map = {
            "GROQ_API_KEY": "groq_api_key",
            "GEMINI_API_KEY": "gemini_api_key",
            "OPENROUTER_API_KEY": "openrouter_api_key",
        }
        for env_name, attr in env_map.items():
            value = os.environ.get(env_name)
            if value:
                setattr(self.ai, attr, value)

    def has_any_cloud_key(self) -> bool:
        return bool(
            self.ai.groq_api_key or self.ai.gemini_api_key or self.ai.openrouter_api_key
        )
