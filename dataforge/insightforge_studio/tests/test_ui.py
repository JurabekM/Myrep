from __future__ import annotations

import os

import pandas as pd
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from insightforge.ui.main_window import MainWindow
from insightforge.ui.widgets import FrameModel


@pytest.fixture(scope="session")
def app():
    instance = QApplication.instance() or QApplication([])
    yield instance


def test_frame_model(app):
    model = FrameModel(pd.DataFrame({"a": [1, 2], "b": ["x", None]}))
    assert model.rowCount() == 2
    assert model.columnCount() == 2
    assert model.data(model.index(1, 1)) == ""


def test_main_window_pages(app):
    window = MainWindow()
    assert set(window.pages) == {"dashboard", "import", "explorer", "pipeline",
                                 "analytics", "logs", "models", "report"}
    for key in window.pages:
        window._go(key)
        assert window.stack.currentWidget() is window.pages[key]
    window.state.workspace.clear()
    window.close()


def test_demo_flow(app):
    window = MainWindow(demo=True)
    assert window.state.workspace.active is not None
    assert len(window.state.workspace.active.frame) == 2500
    window._go("analytics")
    window.pages["analytics"].kind.setCurrentText("histogram")
    window.pages["analytics"].x.setCurrentText("revenue")
    window.pages["analytics"]._draw()
    assert window.pages["analytics"].current_figure is not None
    window.state.workspace.clear()
    window.close()
