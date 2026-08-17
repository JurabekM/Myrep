"""Butun ilova qurilishini tekshiruvchi smoke-test (offscreen).

QApplication offscreen rejimda ishga tushiriladi — real oyna ochilmaydi, ammo
Container, barcha sahifalar, tema va MainWindow haqiqatan quriladi. Bu import
xatolari, QSS xatolari va sahifa konstruktorlaridagi muammolarni ushlaydi.
"""

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def qapp():
    from PyQt6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def container(tmp_path, monkeypatch):
    monkeypatch.setenv("AI_ADVISOR_HOME", str(tmp_path))
    from app.container import Container
    from app.core.config import AppConfig
    from app.data.database import Database
    from app.data.schema import migrate

    config = AppConfig.load()
    database = Database(config.paths.database_file)
    migrate(database)
    c = Container(config, database)
    yield c
    c.shutdown()


def test_stylesheet_builds():
    from app.ui.theme.styles import build_stylesheet

    qss = build_stylesheet()
    assert "QPushButton" in qss
    assert "#Sidebar" in qss


def test_main_window_builds_all_pages(qapp, container):
    from app.ui.main_window import MainWindow

    window = MainWindow(container)
    # 9 ta navigatsiya sahifasi
    assert window._stack.count() == 9  # noqa: SLF001
    # Har sahifaga o'tib ko'ramiz (konstruktor + navigate xatosiz ishlashi kerak)
    for i in range(window._stack.count()):
        window._navigate(i)
        assert window._stack.currentIndex() == i
    window.close()


def test_markdown_rendering():
    from app.ui.widgets.markdown_view import markdown_to_html

    html = markdown_to_html("# Sarlavha\n\n- Punkt **qalin**\n\n| A | B |\n|---|---|\n| 1 | 2 |")
    assert "Sarlavha" in html
    assert "<b>qalin</b>" in html
    assert "<table" in html


def test_tax_page_deterministic_calc(qapp, container):
    """Soliq sahifasi AI'siz (deterministik) hisoblashi kerak."""
    from app.ui.pages.tax_page import TaxPage

    page = TaxPage(container)
    page._revenue.setText("500000000")  # noqa: SLF001
    page._expenses.setText("100000000")  # noqa: SLF001
    page._compare()  # noqa: SLF001
    assert "so'm" in page._result_label.text()  # noqa: SLF001
    page.close()
