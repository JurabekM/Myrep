"""Bildirishnomalar: SDK `ctx.notify`, `monitor` matnlari, shell `Notifier`.

Windows bildirishnomasining ekranda chiqishi bu yerda sinalmaydi (`offscreen` rejimida
tizim tepsisi yo'q): ko'rsatish funksiyasi almashtiriladi.
"""

import importlib
import sys
from collections.abc import Mapping
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from srv1_core.plugins.registry import BUILTIN_DIR
from srv1_sdk.context import PluginContext
from srv1_sdk.manifest import PluginManifest
from srv1_shell.i18n import I18n
from srv1_shell.notifier import REPEAT_QUIET_S, Notifier


def _module(name: str) -> ModuleType:
    sys.path.insert(0, str(BUILTIN_DIR.parent))
    try:
        return importlib.import_module(f"plugins.monitor.{name}")
    finally:
        sys.path.pop(0)


alerts = _module("alerts")
notices = _module("notices")


# --- SDK --------------------------------------------------------------------------------
class _Backend:
    def __init__(self) -> None:
        self.published: list[tuple[str, Mapping[str, Any]]] = []

    def publish(self, topic: str, data: Mapping[str, Any]) -> None:
        self.published.append((topic, data))

    async def audit(self, action: str, target: str, ok: bool, detail: Mapping[str, Any]) -> None:
        raise AssertionError("audit kutilmagan")

    def log(self, level: str, event: str, fields: Mapping[str, Any]) -> None:
        raise AssertionError("log kutilmagan")


def test_context_notify_publishes_clipped_event(tmp_path: Path) -> None:
    manifest = PluginManifest.model_validate({"name": "demo", "version": "1.0.0"})
    backend = _Backend()
    ctx = PluginContext(manifest, tmp_path, backend)  # pyright: ignore[reportArgumentType]
    ctx.notify({"uz": "S" * 200, "en": "Title"}, "x" * 1000, level="error")
    ctx.notify("Oddiy")
    (topic, data), (_, plain) = backend.published
    assert topic == "plugin.demo.notify"
    assert data["level"] == "error"
    assert data["title"] == {"uz": "S" * 80, "en": "Title"}
    assert len(data["message"]) == 300
    assert plain == {"level": "warning", "title": "Oddiy", "message": ""}


# --- monitor matnlari -----------------------------------------------------------------
@pytest.mark.parametrize(
    ("alert", "title_uz", "message_en"),
    [
        (("memory", "raised", 92.3, 90.0, ""), "Xotira chegaradan oshdi", "Now 92.3 %, limit 90 %"),
        (("memory", "cleared", 80.0, 90.0, ""), "Xotira meʼyorga qaytdi", "Now 80 %, limit 90 %"),
        (("cpu", "raised", 97.0, 90.0, ""), "Protsessor uzoq vaqt band", "Now 97 %, limit 90 %"),
        (
            ("disk:C:\\", "raised", 4.2, 10.0, ""),
            "Diskda joy kam: C:\\",
            "4.2 GB free, limit 10 GB",
        ),
        (("disk:D:\\", "cleared", None, 10.0, "disk topilmadi"), "Diskda joy yetarli: D:\\", None),
        (("plugin:iot", "raised", None, None, "kod 3"), "Plagin ishdan chiqdi: iot", None),
        (("plugin:iot", "cleared", None, None, ""), "Plagin tiklandi: iot", None),
    ],
)
def test_monitor_notice_texts(
    alert: tuple[str, str, float | None, float | None, str], title_uz: str, message_en: str | None
) -> None:
    key, state, value, limit, note = alert
    title, message = notices.notice(alerts.Alert(1.0, key, state, value, limit, note))
    assert set(title) == {"uz", "ru", "en"} and all(title.values())
    assert title["uz"] == title_uz
    if message_en is None:
        assert message == note
    else:
        assert message["en"] == message_en and set(message) == {"uz", "ru", "en"}


# --- shell ----------------------------------------------------------------------------
@pytest.fixture(scope="module")
def qapp() -> QApplication:
    existing = QApplication.instance()
    return existing if isinstance(existing, QApplication) else QApplication([])


def test_notifier_shows_plugin_notifications(
    qapp: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    shown: list[tuple[str, str, str]] = []
    language = ["uz"]
    notifier = Notifier(
        QIcon(),
        lambda: I18n(language[0]),
        lambda: None,
        show=lambda title, message, level: shown.append((title, message, level)),
    )
    event = {
        "level": "warning",
        "title": {"uz": "Xotira chegaradan oshdi", "ru": "Память выше порога", "en": "Memory"},
        "message": {"uz": "Hozir 92 %", "ru": "Сейчас 92 %", "en": "Now 92 %"},
    }
    # boshqa hodisalar bildirishnoma emas
    for topic in ("plugin.monitor.alert", "plugins.state", "plugin.monitor.notify.x", "notify"):
        assert not notifier.handle(topic, event)
    assert notifier.handle("plugin.monitor.notify", event)
    assert shown == [("SRV_1 · monitor: Xotira chegaradan oshdi", "Hozir 92 %", "warning")]

    # aynan shu xabar darhol takrorlanmaydi; vaqt o'tgach yana ko'rsatiladi
    assert not notifier.handle("plugin.monitor.notify", event)
    clock = [1000.0]
    monkeypatch.setattr("srv1_shell.notifier.time.monotonic", lambda: clock[0])
    assert notifier.handle("plugin.monitor.notify", event | {"message": "boshqa"})
    assert not notifier.handle("plugin.monitor.notify", event | {"message": "boshqa"})
    clock[0] += REPEAT_QUIET_S + 1
    assert notifier.handle("plugin.monitor.notify", event | {"message": "boshqa"})

    # til o'zgarsa matn ham; oddiy satr, noma'lum daraja va uzun matn
    language[0] = "ru"
    assert notifier.handle("plugin.iot.notify", event)
    assert shown[-1] == ("SRV_1 · iot: Память выше порога", "Сейчас 92 %", "warning")
    assert notifier.handle("plugin.x.notify", {"title": "T" * 500, "level": "zzz"})
    assert shown[-1] == (f"SRV_1 · x: {'T' * 80}", "", "warning")
    assert not notifier.handle("plugin.x.notify", {"message": "sarlavhasiz"})
    assert notifier.shown == len(shown) == 5
    notifier.close()


def test_notifier_without_tray_is_silent(qapp: QApplication) -> None:
    """`offscreen` rejimida tizim tepsisi yo'q: xato bermaydi, shunchaki ko'rsatmaydi."""
    notifier = Notifier(QIcon(), lambda: I18n("uz"), lambda: None)
    assert not notifier.handle("plugin.monitor.notify", {"title": "x"})
    notifier.close()
