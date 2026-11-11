"""Shell GUI testlari: haqiqiy yadro jarayoni + `offscreen` rejimidagi haqiqiy oyna.

Har boshqaruv haqiqatan bosiladi (`click()`), natija esa yadrodan qaytgan
ma'lumot bo'yicha tekshiriladi.
"""

import json
import os
import subprocess
import sys
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass

import httpx
import pytest
from PyQt6.QtCore import QEventLoop, Qt, QTimer
from PyQt6.QtWidgets import QApplication, QCheckBox, QComboBox, QLineEdit

from conftest import free_port, write_plugin
from srv1_shell.app import apply_theme
from srv1_shell.config import ShellConfig
from srv1_shell.main_window import MainWindow
from srv1_shell.pages.logs_page import LogsPage
from srv1_shell.pages.memory_page import MemoryPage
from srv1_shell.pages.panel_page import PanelPage
from srv1_shell.pages.plugins_page import PluginsPage
from srv1_shell.pages.system_page import SystemPage

INVENTORY_PLUGIN = """
    from fastapi import APIRouter
    from pydantic import BaseModel
    from srv1_sdk.hookspec import hookimpl

    KINDS = ["passiv", "aktiv"]
    items = [{"name": "rezistor", "qty": 10, "kind": "passiv", "urgent": False}]

    class Item(BaseModel):
        name: str
        qty: int
        kind: str
        urgent: bool

    @hookimpl
    def srv1_router(ctx):
        router = APIRouter()

        @router.get("/items")
        async def list_items():
            return items

        @router.post("/items")
        async def add_item(item: Item):
            items.append(item.model_dump())
            return {"count": len(items)}

        return router

    @hookimpl
    def srv1_panel(ctx):
        return {
            "title": "Ombor",
            "widgets": [
                {
                    "type": "table",
                    "label": "Qismlar",
                    "source": "/items",
                    "refresh_s": 1,
                    "columns": [{"key": "name", "title": "Nom"}, {"key": "qty", "title": "Soni"}],
                },
                {
                    "type": "form",
                    "label": "Qism qo'shish",
                    "path": "/items",
                    "fields": [
                        {"name": "name", "label": "Nom"},
                        {"name": "qty", "label": "Soni", "kind": "number"},
                        {"name": "kind", "label": "Turi", "kind": "choice", "choices": KINDS},
                        {"name": "urgent", "label": "Shoshilinch", "kind": "bool"},
                    ],
                },
            ],
        }
"""


@dataclass(frozen=True)
class Core:
    port: int
    token: str

    @property
    def config(self) -> ShellConfig:
        return ShellConfig(language="uz", host="127.0.0.1", port=self.port)

    def get(self, path: str) -> httpx.Response:
        headers = {"Authorization": f"Bearer {self.token}"}
        return httpx.get(f"http://127.0.0.1:{self.port}{path}", headers=headers, timeout=5.0)


def wait(ms: int) -> None:
    """Qt hodisalar halqasini `ms` millisoniya aylantiradi."""
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


def pump(condition: Callable[[], bool], timeout_s: float = 8.0, what: str = "") -> None:
    """Qt hodisalarini haqiqiy vaqt bilan aylantiradi (taymerlar ham ishlaydi)."""
    deadline = time.monotonic() + timeout_s
    while not condition():
        if time.monotonic() > deadline:
            pytest.fail(f"kutilgan holat yuz bermadi: {what or condition}")
        wait(20)


@pytest.fixture(scope="module")
def qapp() -> QApplication:
    existing = QApplication.instance()
    app = existing if isinstance(existing, QApplication) else QApplication([])
    apply_theme(app)
    return app


@pytest.fixture(scope="module")
def core(tmp_path_factory: pytest.TempPathFactory) -> Iterator[Core]:
    data_dir = tmp_path_factory.mktemp("shell-core")
    plugin_root = tmp_path_factory.mktemp("shell-plugins")
    write_plugin(plugin_root, "inventory", INVENTORY_PLUGIN)
    port = free_port()
    env = {key: value for key, value in os.environ.items() if not key.startswith("SRV1_")}
    env |= {
        "SRV1_DATA_DIR": str(data_dir),
        "SRV1_SERVER__PORT": str(port),
        "SRV1_EVENTS__STATS_INTERVAL_S": "0.5",
        "SRV1_PLUGINS__DIRS": json.dumps([str(plugin_root)]),
    }
    process = subprocess.Popen(
        [sys.executable, "-m", "srv1_core"], env=env, stderr=subprocess.DEVNULL
    )
    try:
        deadline = time.monotonic() + 30
        while True:
            try:
                httpx.get(f"http://127.0.0.1:{port}/api/v1/health", timeout=1.0).raise_for_status()
                break
            except httpx.HTTPError:
                assert time.monotonic() < deadline, "yadro ishga tushmadi"
                assert process.poll() is None, "yadro o'ldi"
                time.sleep(0.1)
        token = (data_dir / "auth.token").read_text(encoding="ascii").strip()
        yield Core(port=port, token=token)
    finally:
        process.kill()
        process.wait(timeout=10)


@pytest.fixture
def window(qapp: QApplication, core: Core) -> Iterator[MainWindow]:
    main = MainWindow(core.config, core.token)
    main.show()
    pump(lambda: main.events.connected, what="WebSocket ulanishi")
    pump(
        lambda: "panel:hello" in main.page_keys() and "panel:inventory" in main.page_keys(),
        what="panellar",
    )
    yield main
    main.shutdown()
    main.close()
    main.deleteLater()
    wait(20)


def _nav_labels(main: MainWindow) -> list[str]:
    labels: list[str] = []
    for row in range(main.nav.count()):
        item = main.nav.item(row)
        assert item is not None
        labels.append(item.text())
    return labels


def _page[T](main: MainWindow, key: str, kind: type[T]) -> T:
    main.select(key)
    page = main.page(key)
    assert isinstance(page, kind)
    assert main.stack.currentWidget() is page
    return page


# --- ulanish va tizim sahifasi ---------------------------------------------------
def test_connects_and_shows_system(window: MainWindow) -> None:
    assert window.connection.objectName() == "ConnOk"
    assert "Ulangan" in window.connection.text()
    page = _page(window, "system", SystemPage)
    pump(lambda: page.cpu.value.text() != "—", what="tizim holati")
    assert page.memory.value.text().endswith("%")
    assert page.core.value.text().endswith("MB")
    assert "PID" in page.core.detail.text()
    assert page.error.text() == ""
    points = page.chart.point_count()
    pump(lambda: page.chart.point_count() >= points + 2, what="system.stats hodisalari")
    disk_labels = [detail.text() for _bar, detail in page._disk_rows.values()]  # pyright: ignore[reportPrivateUsage]
    assert disk_labels
    assert all("GB" in text for text in disk_labels)


def test_navigation_lists_fixed_pages_and_panels(window: MainWindow) -> None:
    assert _nav_labels(window) == ["Tizim", "Plaginlar", "Jurnal", "Xotira", "Salom", "Ombor"]
    assert window.windowTitle() == "SRV_1 boshqaruvi"


# --- plaginlar: yoqish/o'chirish tugmasi --------------------------------------------
def test_plugin_toggle_button(window: MainWindow, core: Core) -> None:
    page = _page(window, "plugins", PluginsPage)
    pump(lambda: page.table.rowCount() == 2, what="plaginlar ro'yxati")
    row = next(i for i, plugin in enumerate(page.plugins) if plugin["name"] == "hello")

    def status_text() -> str:
        item = page.table.item(row, 3)
        return item.text() if item is not None else ""

    assert status_text() == "Ishlayapti"
    assert page.buttons["hello"].text() == "Oʻchirish"

    page.buttons["hello"].click()
    pump(lambda: status_text() == "Toʻxtagan", what="plagin to'xtashi")
    assert core.get("/api/v1/plugins/hello").json()["status"] == "stopped"
    assert page.buttons["hello"].text() == "Yoqish"
    pump(lambda: "panel:hello" not in window.page_keys(), what="panel yopilishi")
    assert "Salom" not in _nav_labels(window)

    page.buttons["hello"].click()
    pump(lambda: status_text() == "Ishlayapti", what="plagin qayta yonishi")
    assert core.get("/api/v1/plugins/hello").json()["status"] == "running"
    pump(lambda: "panel:hello" in window.page_keys(), what="panel qayta ochilishi")


# --- plagin paneli: har vidjet turi ----------------------------------------------------
def test_hello_panel_values_button_chart_and_forms(
    window: MainWindow, core: Core, monkeypatch: pytest.MonkeyPatch
) -> None:
    page = _page(window, "panel:hello", PanelPage)
    ticks, notes = page.values["ticks"], page.values["notes"]
    pump(lambda: ticks.value.text() != "—", what="qiymat vidjeti")
    assert ticks.title.text() == "Ticklar"
    before = int(ticks.value.text())

    # tugma: POST /tick -> qiymat oshadi, hodisa grafikka tushadi
    page.buttons["POST /tick"].click()
    pump(lambda: int(ticks.value.text()) == before + 1, what="tick tugmasi")
    assert core.get("/api/v1/plugins/hello/api/stats").json()["ticks"] == before + 1
    pump(lambda: page.charts["tick"].last_value() == before + 1, what="grafikdagi hodisa")
    assert "Bajarildi" in page.result.text()

    # GET forma: ixtiyoriy maydon to'ldirilgan va bo'sh holda
    greet = page.forms["/greet"]
    name = greet.inputs["name"]
    assert isinstance(name, QLineEdit)
    name.setText("Ali")
    greet.submit.click()
    pump(lambda: "Salom, Ali!" in page.result.text(), what="salomlashish formasi")
    name.clear()
    greet.submit.click()
    pump(lambda: "Salom, dunyo!" in page.result.text(), what="bo'sh ixtiyoriy maydon")

    # POST forma: majburiy maydon bo'sh bo'lsa so'rov ketmaydi
    note_form = page.forms["/notes"]
    note_form.submit.click()
    assert page.result.text() == "«Matn» toʻldirilishi shart"
    assert page.result.objectName() == "ErrorText"
    text = note_form.inputs["text"]
    assert isinstance(text, QLineEdit)
    text.setText("skrinshot uchun eslatma")
    note_form.submit.click()
    pump(lambda: notes.value.text() == "1", what="eslatma qo'shish")

    # tasdiqli tugma: "Yo'q" — hech narsa o'zgarmaydi, "Ha" — o'chiriladi
    delete = page.buttons["DELETE /notes"]
    asked: list[str] = []

    def decline(action: str) -> bool:
        asked.append(action)
        return False

    monkeypatch.setattr(page, "confirm", decline)
    delete.click()
    wait(300)
    assert asked == ["Eslatmalarni o'chirish"]
    assert core.get("/api/v1/plugins/hello/api/stats").json()["notes"] == 1

    def accept(action: str) -> bool:
        return True

    monkeypatch.setattr(page, "confirm", accept)
    delete.click()
    pump(lambda: notes.value.text() == "0", what="eslatmalarni o'chirish")


def test_table_and_typed_form_fields(window: MainWindow, core: Core) -> None:
    page = _page(window, "panel:inventory", PanelPage)
    table = page.tables["/items"]
    pump(lambda: table.rowCount() >= 1, what="jadval vidjeti")
    first = table.item(0, 0)
    assert first is not None
    assert first.text() == "rezistor"
    rows = table.rowCount()

    form = page.forms["/items"]
    name, qty, kind, urgent = (form.inputs[key] for key in ("name", "qty", "kind", "urgent"))
    assert isinstance(name, QLineEdit)
    assert isinstance(qty, QLineEdit)
    assert isinstance(kind, QComboBox)
    assert isinstance(urgent, QCheckBox)
    name.setText("ESP32")
    qty.setText("olti")
    form.submit.click()
    assert page.result.text() == "«Soni» son boʻlishi kerak"
    qty.setText("6")
    kind.setCurrentText("aktiv")
    urgent.setChecked(True)
    form.submit.click()
    pump(lambda: table.rowCount() == rows + 1, what="yangi qator")
    assert core.get("/api/v1/plugins/inventory/api/items").json()[-1] == {
        "name": "ESP32",
        "qty": 6,
        "kind": "aktiv",
        "urgent": True,
    }


# --- jurnal ------------------------------------------------------------------------------
def test_logs_page_tail_live_and_filter(window: MainWindow) -> None:
    page = _page(window, "logs", LogsPage)
    pump(lambda: "core_started" in page.view.toPlainText(), what="oxirgi log yozuvlari")
    lines_before = page.view.blockCount()

    plugins = window.page("plugins")
    assert isinstance(plugins, PluginsPage)
    assert "target=inventory" not in page.view.toPlainText()
    plugins.toggle("inventory", "disable")
    pump(lambda: "target=inventory" in page.view.toPlainText(), what="jonli log")
    assert "action=plugin.disable" in page.view.toPlainText().splitlines()[-1]
    assert page.view.blockCount() > lines_before

    page.level.setCurrentIndex(page.level.findData("error"))
    assert "core_started" not in page.view.toPlainText()
    page.level.setCurrentIndex(0)
    assert "core_started" in page.view.toPlainText()

    page.pause.setChecked(True)
    shown = page.view.blockCount()
    plugins.toggle("inventory", "enable")
    pump(
        lambda: any(
            e.get("action") == "plugin.enable" and e.get("target") == "inventory"
            for e in page.entries
        ),
        what="log hodisasi",
    )
    assert page.view.blockCount() == shown, "pauza paytida ko'rinish o'zgarmasligi kerak"
    page.pause.setChecked(False)

    page.clear_button.click()
    assert page.view.toPlainText() == ""
    pump(lambda: "panel:inventory" in window.page_keys(), what="panel qayta ochilishi")


# --- xotira ------------------------------------------------------------------------------
def test_memory_page_lists_core_and_shell(window: MainWindow) -> None:
    page = _page(window, "memory", MemoryPage)
    pump(lambda: page.table.rowCount() >= 2, what="jarayonlar jadvali")
    kinds = [row["kind"] for row in page.rows]
    assert kinds == ["core", "shell"]
    assert page.rows[1]["pid"] == os.getpid()
    labels = [page.table.item(row, 0) for row in range(page.table.rowCount())]
    assert [item.text() for item in labels if item is not None] == ["Yadro", "Shell (shu oyna)"]
    assert "chegara 350,0 MB" in page.total.text()
    assert 0 < page.bar.value() <= 100
    total = sum(int(row["rss"]) for row in page.rows)
    assert page.bar.value() == round(100 * total / (350 * 1024 * 1024)) or page.bar.value() == 100


# --- til ----------------------------------------------------------------------------------
def test_language_switch_rebuilds_everything(core: Core, qapp: QApplication) -> None:
    saved: list[str] = []
    main = MainWindow(core.config, core.token, on_language_changed=saved.append)
    main.show()
    try:
        pump(lambda: "panel:hello" in main.page_keys(), what="panel")
        main.select("panel:hello")

        main.language.setCurrentIndex(main.language.findData("ru"))
        assert _nav_labels(main)[:5] == ["Система", "Плагины", "Журнал", "Память", "Привет"]
        assert main.windowTitle() == "Управление SRV_1"
        assert main.current_key() == "panel:hello", "tanlangan sahifa saqlanishi kerak"
        panel = main.page("panel:hello")
        assert isinstance(panel, PanelPage)
        assert panel.values["ticks"].title.text() == "Тики"
        assert panel.buttons["POST /tick"].text() == "Тик сейчас"
        pump(lambda: "Подключено" in main.connection.text(), what="ulanish matni")
        pump(
            lambda: panel.values["ticks"].value.text() != "—", what="qayta qurilgan panel ma'lumoti"
        )

        main.set_language("en")
        assert _nav_labels(main)[:5] == ["System", "Plugins", "Log", "Memory", "Hello"]
        memory = _page(main, "memory", MemoryPage)
        pump(lambda: memory.table.rowCount() >= 2, what="xotira jadvali")
        assert "limit 350.0 MB" in memory.total.text()
        plugins = _page(main, "plugins", PluginsPage)
        pump(lambda: plugins.table.rowCount() == 2, what="plaginlar")
        header = plugins.table.horizontalHeaderItem(3)
        assert header is not None
        assert header.text() == "Status"

        main.set_language("en")  # o'zgarmasa qayta qurilmaydi
        assert saved == ["ru", "en"]
        assert main.config.language == "en"
    finally:
        main.shutdown()
        main.close()
        main.deleteLater()


# --- xato holatlari --------------------------------------------------------------------------
def test_core_unreachable_is_shown(qapp: QApplication) -> None:
    config = ShellConfig(language="uz", host="127.0.0.1", port=free_port())
    main = MainWindow(config, "x" * 43)
    main.show()
    try:
        page = _page(main, "system", SystemPage)
        pump(lambda: page.error.text() != "", what="ulanish xatosi")
        assert page.error.text() == "Yadroga ulanib boʻlmadi"
        assert main.connection.objectName() == "ConnBad"
        assert "Ulanmagan" in main.connection.text()
        assert _nav_labels(main) == ["Tizim", "Plaginlar", "Jurnal", "Xotira"]
    finally:
        main.shutdown()
        main.close()
        main.deleteLater()


def test_wrong_token_is_shown(core: Core, qapp: QApplication) -> None:
    main = MainWindow(core.config, "x" * 43)
    main.show()
    try:
        page = _page(main, "system", SystemPage)
        pump(lambda: page.error.text() != "", what="token xatosi")
        assert page.error.text() == "Token notoʻgʻri"
        assert not main.events.connected
    finally:
        main.shutdown()
        main.close()
        main.deleteLater()


def test_window_is_usable_at_minimum_size(window: MainWindow) -> None:
    """Kichik oynada ham boshqaruvlar siqilib yo'qolmaydi (kesilmaydi, nol o'lchamga tushmaydi)."""
    window.resize(window.minimumSize())
    wait(50)
    page = _page(window, "panel:hello", PanelPage)
    pump(lambda: page.values["ticks"].value.text() != "—", what="panel")
    for button in [*page.buttons.values(), *(form.submit for form in page.forms.values())]:
        assert button.width() >= button.sizeHint().width() - 2, button.text()
        assert button.height() >= 24
    assert window.nav.width() >= 170
    assert window.language.isVisible()
    assert window.windowState() & Qt.WindowState.WindowMinimized == Qt.WindowState.WindowNoState
