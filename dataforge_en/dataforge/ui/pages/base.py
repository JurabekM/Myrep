"""Common base class for all pages."""
from __future__ import annotations

import pandas as pd
from PySide6.QtWidgets import QWidget

from ..store import DataStore
from ..widgets import PageHeader, ScrollPage


class BasePage(QWidget):
    """A page wired to the data store."""

    title: str = ""
    subtitle: str = ""

    def __init__(self, store: DataStore, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.store = store
        self._dirty = True
        self._built = False
        store.data_changed.connect(self._mark_dirty)
        store.active_changed.connect(lambda _: self._mark_dirty())

    # ---- helpers
    @property
    def df(self) -> pd.DataFrame:
        return self.store.df()

    def has_data(self) -> bool:
        return not self.store.df().empty

    def notify(self, text: str, level: str = "info") -> None:
        self.store.message.emit(text, level)

    # ---- refreshing
    def _mark_dirty(self) -> None:
        self._dirty = True
        if self.isVisible():
            self.refresh()
            self._dirty = False

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        if self._dirty:
            self.refresh()
            self._dirty = False

    def refresh(self) -> None:
        """Refresh the page contents (overridden by subclasses)."""

    def make_scroll(self) -> ScrollPage:
        page = ScrollPage(self)
        if self.title:
            page.add(PageHeader(self.title, self.subtitle))
        return page
