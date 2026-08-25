"""Sahifalar uchun umumiy asos."""

from __future__ import annotations

import logging

from PySide6.QtWidgets import QMessageBox, QVBoxLayout, QWidget

from distribos.app_context import AppContext
from distribos.i18n import tr
from distribos.presentation.theme import SPACE_MD
from distribos.presentation.widgets import PageHeader

logger = logging.getLogger(__name__)


class BasePage(QWidget):
    """Har sahifa: sarlavha + tarkib + `refresh()`."""

    #: Sinxronizatsiya aylanishidan keyin avtomatik yangilansinmi.
    live = False

    def __init__(self, context: AppContext, title: str, subtitle: str = "") -> None:
        super().__init__()
        self._context = context
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(SPACE_MD)

        self.header = PageHeader(title, subtitle)
        self._layout.addWidget(self.header)

    @property
    def context(self) -> AppContext:
        return self._context

    def add(self, widget: QWidget, stretch: int = 0) -> QWidget:
        self._layout.addWidget(widget, stretch)
        return widget

    def refresh(self) -> None:
        """Sahifa ochilganda chaqiriladi. Sahifalar qayta belgilaydi."""

    def refresh_if_live(self) -> None:
        if self.live:
            try:
                self.refresh()
            except Exception:
                logger.exception("Jonli yangilashda xato: %s", type(self).__name__)

    # --- yordamchilar -----------------------------------------------------

    def notify(self, text: str, title: str | None = None) -> None:
        # Standart sarlavha PARAMETR SUKUTIDA emas, TANADA `tr()`
        # qilinadi: sukut qiymati funksiya TA'RIFLANGANDA (import
        # vaqtida, til o'rnatilishidan OLDIN) bir marta hisoblanadi va
        # muzlab qolardi.
        QMessageBox.information(self, title if title is not None else tr("Bajarildi"), text)

    def warn(self, text: str, title: str | None = None) -> None:
        QMessageBox.warning(self, title if title is not None else tr("Diqqat"), text)

    def confirm(self, text: str, title: str | None = None) -> bool:
        answer = QMessageBox.question(
            self, title if title is not None else tr("Tasdiqlang"), text,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return answer == QMessageBox.StandardButton.Yes

    def report_error(self, exc: Exception, action: str) -> None:
        """Xatoni foydalanuvchiga TUSHUNARLI tilda ko'rsatadi.

        Texnik tafsilot log'ga tushadi; foydalanuvchi nima qilishni biladi.
        """
        logger.exception("%s bajarilmadi", action)
        QMessageBox.critical(
            self, tr("Xatolik"),
            tr(
                "{action} bajarilmadi.\n\n{error}\n\n"
                "Ma'lumotlaringiz saqlanib qoldi. Qayta urinib ko'ring yoki "
                "Sozlamalar > Diagnostika bo'limidan yordam to'plamini yarating."
            ).format(action=action, error=exc),
        )
