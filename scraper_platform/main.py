# -*- coding: utf-8 -*-
"""
main.py
=======
Universal Web Scraping Platform — kirish nuqtasi.

Foydalanish:
    GUI rejimi (standart):
        python main.py

    CLI rejimi (bitta URL'ni tez scrape qilish):
        python main.py --cli https://example.com --engine auto --export json
        python main.py --cli https://example.com --crawl --export csv

    Proxy'larni tekshirish:
        python main.py --check-proxies
"""

from __future__ import annotations

import argparse
import sys

from logs.logger import get_logger

log = get_logger("main")


def run_gui() -> int:
    """PyQt6 GUI ni ishga tushiradi."""
    try:
        from PyQt6.QtWidgets import QApplication
    except ImportError:
        print("PyQt6 o'rnatilmagan. O'rnatish: pip install PyQt6")
        return 1

    from gui.main_window import MainWindow

    app = QApplication(sys.argv)
    app.setApplicationName("Universal Web Scraping Platform")
    window = MainWindow()
    window.show()
    log.info("GUI ishga tushdi")
    return app.exec()


def run_cli(args: argparse.Namespace) -> int:
    """CLI rejimida bitta scraping vazifasini bajaradi."""
    from scraper.task_runner import ScrapeTask, TaskOptions

    options = TaskOptions(
        url=args.cli,
        engine=args.engine,
        crawl=args.crawl,
        infinite_scroll=args.scroll,
        export_format=args.export or "",
    )

    def _progress(p) -> None:
        print(f"\r  Sahifa: {p.pages_done} | Yozuv: {p.items_found} | {p.current_url[:50]}",
              end="", flush=True)

    task = ScrapeTask(options, on_progress=_progress)
    result = task.run()
    print()  # yangi qator
    print("=" * 50)
    print(f"Holat: {result['status']}")
    print(f"Sahifalar: {result['pages_done']} (muvaffaqiyatli: {result['pages_ok']})")
    print(f"Yozuvlar: {result['items_found']}")
    if result.get("export_path"):
        print(f"Eksport: {result['export_path']}")
    print("=" * 50)
    return 0


def check_proxies() -> int:
    """Barcha proxy'larni tekshiradi."""
    from proxy.proxy_manager import PROXY_MANAGER
    print(f"Proxy'lar soni: {PROXY_MANAGER.count}")
    stats = PROXY_MANAGER.health_check()
    print(f"Ishlaydi: {stats['alive']}, o'chirildi: {stats['dead']}")
    return 0


def main() -> int:
    """Argumentlarni tahlil qiladi va tegishli rejimni ishga tushiradi."""
    parser = argparse.ArgumentParser(
        description="Universal Web Scraping Platform")
    parser.add_argument("--cli", metavar="URL", help="CLI rejimida URL'ni scrape qilish")
    parser.add_argument("--engine", default="auto",
                        choices=["auto", "requests", "playwright", "cloudscraper"],
                        help="Scraping dvigateli")
    parser.add_argument("--crawl", action="store_true", help="Saytni aylanib chiqish")
    parser.add_argument("--scroll", action="store_true", help="Infinite scroll")
    parser.add_argument("--export", choices=["csv", "xlsx", "json", "sqlite"],
                        help="Eksport formati")
    parser.add_argument("--check-proxies", action="store_true",
                        help="Proxy'larni tekshirish")
    args = parser.parse_args()

    if args.check_proxies:
        return check_proxies()
    if args.cli:
        return run_cli(args)
    return run_gui()


if __name__ == "__main__":
    sys.exit(main())
