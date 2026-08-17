"""GUI qatlami testlari (offscreen rejimda ishlaydi — displey talab qilmaydi)."""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from dataforge.ui.store import DataStore  # noqa: E402
from dataforge.ui.widgets import (ColumnCombo, DataFrameModel, FrameTable,  # noqa: E402
                                  MultiColumnSelect, StatTile, fmt_num)


@pytest.fixture(scope="session")
def app():
    inst = QApplication.instance() or QApplication([])
    yield inst


@pytest.fixture
def df() -> pd.DataFrame:
    rng = np.random.default_rng(3)
    n = 120
    t0 = datetime(2024, 5, 1)
    return pd.DataFrame({
        "ts": [t0 + timedelta(minutes=i) for i in range(n)],
        "cat": rng.choice(["x", "y", "z"], n),
        "val": rng.normal(10, 2, n).round(3),
        "flag": rng.integers(0, 2, n),
        "msg": ["hodisa " + str(i) for i in range(n)],
    })


# --------------------------------------------------------------- DataStore --
class TestDataStore:
    def test_add_and_active(self, app, df):
        s = DataStore()
        name = s.add("d1", df)
        assert name == "d1"
        assert s.active_name == "d1"
        assert len(s.df()) == len(df)

    def test_duplicate_name_gets_suffix(self, app, df):
        s = DataStore()
        s.add("d", df)
        second = s.add("d", df)
        assert second == "d (2)"
        assert len(s.names) == 2

    def test_remove_switches_active(self, app, df):
        s = DataStore()
        s.add("a", df)
        s.add("b", df)
        s.remove("b")
        assert s.active_name == "a"
        assert s.names == ["a"]

    def test_rename(self, app, df):
        s = DataStore()
        s.add("old", df)
        s.rename("old", "new")
        assert s.names == ["new"] and s.active_name == "new"

    def test_run_op_and_undo(self, app, df):
        s = DataStore()
        s.add("d", df)
        assert s.run_op("filter_range", column="val", low=10)
        assert len(s.df()) < len(df)
        assert s.can_undo()
        s.undo()
        assert len(s.df()) == len(df)
        assert s.can_redo()
        s.redo()
        assert len(s.df()) < len(df)

    def test_run_op_invalid_returns_false(self, app, df):
        s = DataStore()
        s.add("d", df)
        assert s.run_op("filter_query", expr="mavjud_emas > 1") is False
        assert len(s.df()) == len(df)   # ma'lumot buzilmadi

    def test_set_cell_numeric(self, app, df):
        s = DataStore()
        s.add("d", df)
        assert s.set_cell(0, "val", "99.5")
        assert s.df().iloc[0]["val"] == 99.5

    def test_set_cell_bad_column(self, app, df):
        s = DataStore()
        s.add("d", df)
        assert s.set_cell(0, "yo'q", 1) is False

    def test_add_row_and_column(self, app, df):
        s = DataStore()
        s.add("d", df)
        s.add_row()
        assert len(s.df()) == len(df) + 1
        s.add_column("yangi", 0)
        assert "yangi" in s.df().columns

    def test_history_labels(self, app, df):
        s = DataStore()
        s.add("d", df)
        s.run_op("head", n=10)
        labels = s.history_labels()
        assert len(labels) == 2 and "Birinchi" in labels[1]

    def test_clear(self, app, df):
        s = DataStore()
        s.add("d", df)
        s.clear()
        assert s.is_empty and s.active_name is None

    def test_signals_emitted(self, app, df):
        s = DataStore()
        seen = []
        s.message.connect(lambda t, l: seen.append(l))
        s.add("d", df)
        s.run_op("head", n=5)
        assert "success" in seen and "info" in seen


# ------------------------------------------------------------- vidjetlar ---
class TestWidgets:
    def test_fmt_num(self):
        assert fmt_num(1234) == "1,234"
        assert fmt_num(None) == "—"
        assert fmt_num(float("nan")) == "—"
        assert fmt_num(1.5) == "1.5"

    def test_dataframe_model_basic(self, app, df):
        m = DataFrameModel(df)
        assert m.rowCount() == len(df)
        assert m.columnCount() == df.shape[1]
        idx = m.index(0, 2)
        assert m.data(idx, Qt.ItemDataRole.DisplayRole) is not None
        assert m.headerData(0, Qt.Orientation.Horizontal,
                            Qt.ItemDataRole.DisplayRole) == "ts"

    def test_dataframe_model_edit_signal(self, app, df):
        m = DataFrameModel(df, editable=True)
        got = []
        m.edit_requested.connect(lambda r, c, v: got.append((r, c, v)))
        m.setData(m.index(1, 2), "42", Qt.ItemDataRole.EditRole)
        assert got == [(1, "val", "42")]

    def test_dataframe_model_empty(self, app):
        m = DataFrameModel(pd.DataFrame())
        assert m.rowCount() == 0 and m.columnCount() == 0

    def test_dataframe_model_nan_display(self, app):
        m = DataFrameModel(pd.DataFrame({"a": [None, 1.0]}))
        assert m.data(m.index(0, 0), Qt.ItemDataRole.DisplayRole) == ""

    def test_frame_table_set_df(self, app, df):
        t = FrameTable(editable=True)
        t.set_df(df)
        assert t.model_.rowCount() == len(df)

    def test_column_combo_filters_numeric(self, app, df):
        c = ColumnCombo("num")
        c.populate(df)
        items = [c.itemText(i) for i in range(c.count())]
        assert "val" in items and "msg" not in items

    def test_column_combo_allow_empty(self, app, df):
        c = ColumnCombo("any", allow_empty=True)
        c.populate(df)
        assert c.value() is None

    def test_multi_column_select(self, app, df):
        m = MultiColumnSelect("num")
        m.populate(df)
        m.set_all(True)
        assert "val" in m.values()
        m.set_all(False)
        assert m.values() == []
        m.set_values(["val"])
        assert m.values() == ["val"]

    def test_stat_tile(self, app):
        t = StatTile("Qator", "10")
        t.set_value("20", "o'sdi")
        assert t.value_label.text() == "20"


# ----------------------------------------------------------- MainWindow ----
class TestMainWindow:
    @pytest.fixture
    def win(self, app):
        from dataforge.ui.main_window import MainWindow

        w = MainWindow()
        yield w
        w.close()

    def test_pages_created(self, win):
        assert set(win.pages) == {"import", "table", "transform", "profile",
                                  "chart", "ml", "logai", "report"}

    def test_navigation(self, win, app):
        for key in win.pages:
            win._go(key)
            app.processEvents()
            assert win.stack.currentWidget() is win.pages[key]
            assert win.nav_buttons[key].isChecked()

    def test_pages_refresh_with_data(self, win, app, df):
        win.store.add("d", df)
        for key, page in win.pages.items():
            win._go(key)
            page.refresh()
            app.processEvents()
        assert win.store.active_name == "d"

    def test_topbar_updates(self, win, app, df):
        win.store.add("d", df)
        app.processEvents()
        assert "120" in win.shape_label.text()

    def test_table_page_search(self, win, app, df):
        win.store.add("d", df)
        page = win.pages["table"]
        win._go("table")
        page.refresh()
        page.search.setText("hodisa 1")
        page._apply_search()
        app.processEvents()
        assert page.table.model_.rowCount() < len(df)

    def test_transform_page_form(self, win, app, df):
        win.store.add("d", df)
        page = win.pages["transform"]
        win._go("transform")
        page.refresh()
        spec = __import__("dataforge.core.transform", fromlist=["OPS"]).OPS["head"]
        page._current = spec
        page._build_form(spec)
        params = page._read_form()
        assert "n" in params

    def test_chart_page_draw(self, win, app, df):
        win.store.add("d", df)
        page = win.pages["chart"]
        win._go("chart")
        page.refresh()
        page.x_combo.setCurrentText("val")
        for i in range(page.type_list.count()):
            if page.type_list.item(i).data(Qt.ItemDataRole.UserRole) == "hist":
                page.type_list.setCurrentRow(i)
                break
        page.draw()
        app.processEvents()
        assert page.canvas.figure is not None

    def test_profile_page_profile(self, win, app, df):
        win.store.add("d", df)
        page = win.pages["profile"]
        win._go("profile")
        from dataforge.core.profile import profile_dataframe

        page._on_profile(profile_dataframe(df))
        app.processEvents()
        assert "120" in page.tiles["rows"].value_label.text()

    def test_project_save_load(self, win, app, df, tmp_path):
        from dataforge.core import project

        win.store.add("d", df)
        p = project.save_project(tmp_path / "p.dfp",
                                 {"d": win.store.get("d")}, active="d")
        data, meta = project.load_project(p)
        win.store.clear()
        for n, d in data.items():
            win.store.add(n, d, activate=False)
        assert win.store.names == ["d"]
