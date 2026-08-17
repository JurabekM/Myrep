# -*- coding: utf-8 -*-
"""
scraper/task_runner.py
======================
Yuqori darajali orchestrator. Barcha modullarni bir joyga bog'laydi:

    Crawler -> ScraperEngine -> Extractor -> AI -> Plugins -> Database -> Export

`ScrapeTask` bitta to'liq scraping vazifasini ifodalaydi va uni bir
qatorda ishga tushirish imkonini beradi. GUI progress callback'lari
orqali real-time yangilanishlarni qo'llab-quvvatlaydi.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from config.settings import CONFIG
from scraper.engine import ScraperEngine, ScrapeResult
from scraper.crawler import Crawler
from parsers.extractor import Extractor
from ai.analyzer import ContentAnalyzer, DuplicateDetector
from plugins.plugin_manager import PLUGIN_MANAGER
from database.db_manager import DB
from exporters.exporter import Exporter
from logs.logger import get_logger

log = get_logger(__name__)


@dataclass
class TaskOptions:
    """Bitta scraping vazifasining sozlamalari."""
    url: str
    name: str = ""
    engine: str = "auto"                    # auto|requests|playwright|cloudscraper
    crawl: bool = False                     # True bo'lsa saytni aylanib chiqadi
    infinite_scroll: bool = False
    # Maxsus ajratib olish
    css_selectors: dict[str, str] = field(default_factory=dict)  # {maydon: selector}
    xpath_selectors: dict[str, str] = field(default_factory=dict)
    regex_patterns: dict[str, str] = field(default_factory=dict)
    # AI va pluginlar
    use_ai: bool = True
    use_plugins: bool = True
    deduplicate: bool = True
    # Eksport
    export_format: str = ""                 # csv|xlsx|json|sqlite yoki bo'sh
    export_path: str = ""


@dataclass
class TaskProgress:
    """Vazifa jarayoni holati (GUI uchun)."""
    pages_done: int = 0
    pages_ok: int = 0
    items_found: int = 0
    current_url: str = ""


class ScrapeTask:
    """Bitta to'liq scraping vazifasini ijro etuvchi klass."""

    def __init__(self, options: TaskOptions,
                 on_progress: Callable[[TaskProgress], None] | None = None,
                 stop_flag: Callable[[], bool] | None = None) -> None:
        self.opt = options
        self.on_progress = on_progress
        self.stop_flag = stop_flag or (lambda: False)
        self.progress = TaskProgress()
        self.engine = ScraperEngine(engine=options.engine)
        self.dedup = DuplicateDetector()
        self.session_id: int | None = None
        self._collected: list[dict[str, Any]] = []

    # -----------------------------------------------------------------
    def _emit(self) -> None:
        """GUI'ga progress yuboradi."""
        if self.on_progress:
            self.on_progress(self.progress)

    def _process_page(self, result: ScrapeResult, depth: int = 0) -> None:
        """Bitta sahifani qayta ishlaydi: ekstrakt + AI + plugin + saqlash."""
        self.progress.pages_done += 1
        self.progress.current_url = result.url

        # Sahifani bazaga yozamiz
        DB.record_page(
            session_id=self.session_id, url=result.url,
            status_code=result.status_code,
            status="ok" if result.ok else "error",
            engine_used=result.engine_used, depth=depth,
            content_type=result.content_type,
            response_time=result.response_time, error=result.error,
        )

        if not result.ok or not result.html:
            self._emit()
            return
        self.progress.pages_ok += 1

        items = self._extract_items(result)

        # Dublikatlarni filtrlaymiz (matn o'xshashligi bo'yicha)
        if self.opt.deduplicate and items:
            filtered = []
            for item in items:
                text_repr = " ".join(str(v) for v in item.values())
                if not self.dedup.is_duplicate(id(item), text_repr):
                    filtered.append(item)
            items = filtered

        if items:
            saved = DB.save_items(
                session_id=self.session_id, items=items,
                source_url=result.url, deduplicate=self.opt.deduplicate,
            )
            self.progress.items_found += saved
            self._collected.extend(items)

        self._emit()

    def _extract_items(self, result: ScrapeResult) -> list[dict[str, Any]]:
        """Sahifadan barcha kerakli ma'lumotlarni ajratadi."""
        ext: Extractor = result.extractor()
        items: list[dict[str, Any]] = []

        # 1) Maxsus selektorlar berilgan bo'lsa faqat ularni ishlatamiz
        if self.opt.css_selectors or self.opt.xpath_selectors or self.opt.regex_patterns:
            record: dict[str, Any] = {"source_url": result.url}
            for field_name, selector in self.opt.css_selectors.items():
                record[field_name] = ext.select_css(selector)
            for field_name, xpath in self.opt.xpath_selectors.items():
                record[field_name] = ext.select_xpath(xpath)
            for field_name, pattern in self.opt.regex_patterns.items():
                record[field_name] = ext.select_regex(pattern)
            items.append(record)
        else:
            # 2) Aks holda barcha standart ma'lumotlarni yig'amiz
            data = ext.extract_all()
            data["source_url"] = result.url
            items.append(data)

        # 3) AI tahlili
        if self.opt.use_ai:
            try:
                analysis = ContentAnalyzer(result.html, result.url).analyze()
                for item in items:
                    item["_ai"] = analysis
            except Exception as exc:  # noqa: BLE001
                log.debug("AI tahlil xatoligi: {}", exc)

        # 4) Pluginlar
        if self.opt.use_plugins:
            plugin_items = PLUGIN_MANAGER.apply(result.url, result.html)
            items.extend(plugin_items)

        return items

    # -----------------------------------------------------------------
    def run(self) -> dict[str, Any]:
        """
        Vazifani ishga tushiradi.

        Returns:
            Yakuniy statistika lug'ati.
        """
        log.info("Vazifa boshlandi: {}", self.opt.url)
        self.session_id = DB.create_session(
            name=self.opt.name, start_url=self.opt.url,
            engine=self.opt.engine,
            config_snapshot={"crawl": self.opt.crawl},
        )

        try:
            if self.opt.crawl:
                # Saytni aylanib chiqamiz
                crawler = Crawler(engine=self.engine, stop_flag=self.stop_flag)
                for result in crawler.crawl(self.opt.url):
                    if self.stop_flag():
                        break
                    self._process_page(result, depth=0)
            else:
                # Faqat bitta sahifa
                result = self.engine.scrape(
                    self.opt.url, infinite_scroll=self.opt.infinite_scroll
                )
                self._process_page(result)

            status = "stopped" if self.stop_flag() else "done"
        except Exception as exc:  # noqa: BLE001
            log.exception("Vazifa xatoligi: {}", exc)
            status = "failed"
        finally:
            DB.finish_session(self.session_id, status=status)
            self.engine.close()

        # Eksport
        export_path = None
        if self.opt.export_format and self._collected:
            exporter = Exporter(self._collected)
            path = self.opt.export_path or None
            export_path = exporter.export(self.opt.export_format, path)

        log.info("Vazifa yakunlandi: {} sahifa, {} yozuv",
                 self.progress.pages_done, self.progress.items_found)
        return {
            "session_id": self.session_id,
            "status": status,
            "pages_done": self.progress.pages_done,
            "pages_ok": self.progress.pages_ok,
            "items_found": self.progress.items_found,
            "export_path": str(export_path) if export_path else "",
        }
