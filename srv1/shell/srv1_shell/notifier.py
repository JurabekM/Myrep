"""Plagin bildirishnomalarini Windows bildirishnomasi (tizim tepsisi) qilib ko'rsatadi.

Plagin `ctx.notify(...)` chaqiradi -> `plugin.<nom>.notify` hodisasi -> shu yerda ko'rsatiladi.
Qachon va nima haqida xabar berish — plagin ishi; shell faqat ko'rsatadi. Shell yopiq
bo'lsa bildirishnoma chiqmaydi (yadro xizmat sifatida ekransiz sessiyada ishlaydi).
"""

import re
import time
from collections.abc import Callable, Mapping
from typing import Any

from PyQt6.QtCore import QObject
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QSystemTrayIcon

from srv1_shell.i18n import I18n

NOTIFY_TOPIC = re.compile(r"plugin\.([a-z0-9_-]+)\.notify")
REPEAT_QUIET_S = 30.0
SHOW_MS = 10_000
TITLE_MAX, MESSAGE_MAX = 80, 300
_ICONS = {
    "info": QSystemTrayIcon.MessageIcon.Information,
    "warning": QSystemTrayIcon.MessageIcon.Warning,
    "error": QSystemTrayIcon.MessageIcon.Critical,
}
Show = Callable[[str, str, str], None]


def _text(i18n: I18n, value: object, limit: int) -> str:
    if isinstance(value, Mapping):
        clean = {str(k): str(v) for k, v in value.items()}  # pyright: ignore[reportUnknownVariableType, reportUnknownArgumentType]
        return i18n.pick(clean)[:limit]
    return str(value or "")[:limit]


class Notifier(QObject):
    """`show` berilmasa, tizim tepsisidagi belgi orqali ko'rsatadi (tepsi bo'lmasa — jim)."""

    def __init__(
        self,
        icon: QIcon,
        i18n: Callable[[], I18n],
        on_click: Callable[[], None],
        parent: QObject | None = None,
        show: Show | None = None,
    ) -> None:
        super().__init__(parent)
        self._i18n = i18n
        self._last: tuple[str, str] = ("", "")
        self._last_at = 0.0
        self.shown = 0
        self._tray: QSystemTrayIcon | None = None
        self._show = show
        if show is None and QSystemTrayIcon.isSystemTrayAvailable():
            self._tray = QSystemTrayIcon(icon, self)
            self._tray.setToolTip("SRV_1")
            self._on_click = on_click
            self._tray.activated.connect(self._activated)
            self._tray.messageClicked.connect(on_click)
            self._tray.show()

    def handle(self, topic: str, data: Mapping[str, Any]) -> bool:
        """Bildirishnoma hodisasi bo'lsa ko'rsatadi. Ko'rsatilgan bo'lsa `True`."""
        match = NOTIFY_TOPIC.fullmatch(topic)
        if match is None:
            return False
        i18n = self._i18n()
        title = _text(i18n, data.get("title"), TITLE_MAX)
        message = _text(i18n, data.get("message"), MESSAGE_MAX)
        if not title:
            return False
        level = str(data.get("level", "warning"))
        level = level if level in _ICONS else "warning"
        now = time.monotonic()
        if (title, message) == self._last and now - self._last_at < REPEAT_QUIET_S:
            return False  # aynan shu xabar hozirgina ko'rsatilgan
        self._last, self._last_at = (title, message), now
        heading = f"SRV_1 · {match.group(1)}: {title}"
        if self._show is not None:
            self._show(heading, message, level)
        elif self._tray is not None:
            self._tray.showMessage(heading, message, _ICONS[level], SHOW_MS)
        else:
            return False
        self.shown += 1
        return True

    def _activated(self, _reason: QSystemTrayIcon.ActivationReason) -> None:
        self._on_click()

    def close(self) -> None:
        if self._tray is not None:
            self._tray.hide()
