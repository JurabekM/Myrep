# -*- coding: utf-8 -*-
"""
config/settings.py
==================
Platformaning markaziy konfiguratsiya moduli.

Bu modul barcha global sozlamalarni bir joyda saqlaydi. Sozlamalar
`config/config.json` faylidan yuklanadi; agar fayl bo'lmasa, standart
qiymatlar ishlatiladi va yangi fayl yaratiladi.

Maxfiy ma'lumotlar (proxy parollari, DB kredensiallari) `SecureStore`
orqali shifrlangan holda saqlanadi (config/secure.py).
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any


# Loyihaning ildiz papkasi (config/ dan bir daraja yuqori)
BASE_DIR: Path = Path(__file__).resolve().parent.parent

# Asosiy papkalar
CONFIG_DIR: Path = BASE_DIR / "config"
LOGS_DIR: Path = BASE_DIR / "logs"
DATA_DIR: Path = BASE_DIR / "data"
PLUGINS_DIR: Path = BASE_DIR / "plugins"
DOWNLOADS_DIR: Path = DATA_DIR / "downloads"

# Kerakli papkalarni yaratib qo'yamiz
for _d in (LOGS_DIR, DATA_DIR, DOWNLOADS_DIR, PLUGINS_DIR):
    _d.mkdir(parents=True, exist_ok=True)

CONFIG_FILE: Path = CONFIG_DIR / "config.json"


@dataclass
class ScraperConfig:
    """Scraping dvigateliga oid sozlamalar."""

    timeout: int = 30                     # So'rov timeout (sekund)
    max_retries: int = 3                  # Qayta urinishlar soni
    retry_backoff: float = 1.5            # Retry orasidagi kechikish koeffitsienti
    concurrency: int = 50                 # Async bir vaqtdagi so'rovlar soni
    request_delay: float = 0.0            # So'rovlar orasidagi kechikish (sekund)
    verify_ssl: bool = True               # SSL sertifikatni tekshirish
    follow_redirects: bool = True
    default_engine: str = "auto"          # auto | requests | httpx | playwright | cloudscraper
    respect_robots: bool = True           # robots.txt ga rioya qilish
    render_wait: float = 3.0              # JS render kutish vaqti (Playwright)
    scroll_pause: float = 1.0             # Infinite scroll orasidagi pauza
    max_scroll: int = 20                  # Maksimal scroll soni


@dataclass
class CrawlerConfig:
    """Crawler (rekursiv aylanib chiqish) sozlamalari."""

    strategy: str = "bfs"                 # bfs | dfs
    max_depth: int = 2                    # Maksimal chuqurlik
    max_pages: int = 100                  # Maksimal sahifalar soni
    same_domain_only: bool = True         # Faqat bitta domen ichida
    use_sitemap: bool = True              # sitemap.xml dan foydalanish


@dataclass
class DatabaseConfig:
    """Ma'lumotlar bazasi sozlamalari."""

    engine: str = "sqlite"                # sqlite | postgresql
    sqlite_path: str = str(DATA_DIR / "scraper.db")
    # PostgreSQL uchun (maxfiy qism SecureStore dan olinadi)
    pg_host: str = "localhost"
    pg_port: int = 5432
    pg_database: str = "scraper"
    pg_user: str = "postgres"

    def url(self, password: str = "") -> str:
        """SQLAlchemy uchun ulanish URL manzilini qaytaradi."""
        if self.engine == "postgresql":
            return (
                f"postgresql+psycopg2://{self.pg_user}:{password}"
                f"@{self.pg_host}:{self.pg_port}/{self.pg_database}"
            )
        return f"sqlite:///{self.sqlite_path}"


@dataclass
class ProxyConfig:
    """Proxy menejeri sozlamalari."""

    enabled: bool = False
    rotate: bool = True                   # Har so'rovda proxy almashtirish
    health_check: bool = True             # Proxy ishlashini tekshirish
    check_url: str = "http://httpbin.org/ip"
    check_timeout: int = 10
    # Proxy ro'yxati config faylida yoki proxy/proxies.txt da saqlanadi
    proxies: list[str] = field(default_factory=list)


@dataclass
class AppConfig:
    """Barcha sozlamalarni jamlovchi asosiy konfiguratsiya."""

    scraper: ScraperConfig = field(default_factory=ScraperConfig)
    crawler: CrawlerConfig = field(default_factory=CrawlerConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    proxy: ProxyConfig = field(default_factory=ProxyConfig)

    log_level: str = "INFO"               # DEBUG | INFO | WARNING | ERROR
    theme: str = "dark"                   # GUI mavzusi

    # -------------------------------------------------------------
    # Yuklash / saqlash
    # -------------------------------------------------------------
    @classmethod
    def load(cls, path: Path = CONFIG_FILE) -> "AppConfig":
        """Konfiguratsiyani JSON fayldan yuklaydi (bo'lmasa yaratadi)."""
        if not path.exists():
            cfg = cls()
            cfg.save(path)
            return cfg

        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            # Buzilgan fayl bo'lsa standart qiymatlarga qaytamiz
            return cls()

        return cls(
            scraper=ScraperConfig(**raw.get("scraper", {})),
            crawler=CrawlerConfig(**raw.get("crawler", {})),
            database=DatabaseConfig(**raw.get("database", {})),
            proxy=ProxyConfig(**raw.get("proxy", {})),
            log_level=raw.get("log_level", "INFO"),
            theme=raw.get("theme", "dark"),
        )

    def save(self, path: Path = CONFIG_FILE) -> None:
        """Konfiguratsiyani JSON faylga saqlaydi."""
        path.parent.mkdir(parents=True, exist_ok=True)
        data: dict[str, Any] = {
            "scraper": asdict(self.scraper),
            "crawler": asdict(self.crawler),
            "database": asdict(self.database),
            "proxy": asdict(self.proxy),
            "log_level": self.log_level,
            "theme": self.theme,
        }
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


# Global singleton konfiguratsiya obyekti
CONFIG: AppConfig = AppConfig.load()
