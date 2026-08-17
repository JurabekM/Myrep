"""Table page — view, search and edit the data directly."""
from __future__ import annotations

import numpy as np
import pandas as pd
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (QComboBox, QHBoxLayout, QInputDialog, QLabel,
                               QLineEdit, QMessageBox, QVBoxLayout, QWidget)

from ...core import transform
from ..widgets import FrameTable, PageHeader, make_button, make_checkbox
from .base import BasePage


class TablePage(BasePage):
    title = "Table"
    subtitle = ("Double-click a cell to edit it, right-click a column header to reach "
                "the column operations. Every change is recorded in the history.")

    def __init__(self, store, parent=None) -> None:
        super().__init__(store, parent)
        self._filtered: pd.DataFrame | None = None
        self._build()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 16)
        root.setSpacing(12)
        root.addWidget(PageHeader(self.title, self.subtitle))

        # ---- search bar
        bar = QHBoxLayout()
        bar.setSpacing(8)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search… (across all columns)")
        self.search.setClearButtonEnabled(True)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(280)
        self._timer.timeout.connect(self._apply_search)
        self.search.textChanged.connect(lambda _: self._timer.start())
        bar.addWidget(self.search, 2)

        self.search_col = QComboBox()
        self.search_col.setMinimumWidth(150)
        self.search_col.currentIndexChanged.connect(lambda _: self._timer.start())
        bar.addWidget(self.search_col)

        self.regex_cb = make_checkbox("Regex", False, lambda _: self._timer.start())
        bar.addWidget(self.regex_cb)
        self.case_cb = make_checkbox("Aa", False, lambda _: self._timer.start())
        self.case_cb.setToolTip("Case sensitive")
        bar.addWidget(self.case_cb)
        bar.addWidget(make_button("Apply as filter", "Ghost", self._commit_filter,
                                  "Make the current search result permanent"))
        bar.addStretch(1)
        root.addLayout(bar)

        # ---- action bar
        acts = QHBoxLayout()
        acts.setSpacing(8)
        for text, tip, fn in (
            ("↶ Undo", "Undo the last operation (Ctrl+Z)", self.store.undo),
            ("↷ Redo", "Redo (Ctrl+Y)", self.store.redo),
        ):
            acts.addWidget(make_button(text, "Ghost", fn, tip))
        acts.addSpacing(12)
        acts.addWidget(make_button("+ Row", "Ghost", lambda: self.store.add_row(),
                                   "Append an empty row"))
        acts.addWidget(make_button("+ Column", "Ghost", self._add_column))
        acts.addWidget(make_button("− Rows", "Ghost", self._delete_rows,
                                   "Delete the selected rows"))
        acts.addSpacing(12)
        acts.addWidget(make_button("Drop duplicates", "Ghost",
                                   lambda: self.store.run_op("drop_duplicates")))
        acts.addWidget(make_button("Drop empty rows", "Ghost",
                                   lambda: self.store.run_op("dropna", how="all")))
        self.heat_cb = make_checkbox("Heat colouring", False, self._toggle_heat)
        self.heat_cb.setToolTip("Colour the current numeric column by value")
        acts.addWidget(self.heat_cb)
        acts.addStretch(1)
        root.addLayout(acts)

        # ---- table
        self.table = FrameTable(editable=True)
        self.table.model_.edit_requested.connect(self._on_edit)
        self.table.column_action.connect(self._on_column_action)
        self.table.selectionModel().selectionChanged.connect(self._update_selection_stats)
        root.addWidget(self.table, 1)

        # ---- footer
        foot = QHBoxLayout()
        self.info = QLabel("No data loaded")
        self.info.setObjectName("Hint")
        self.sel_info = QLabel("")
        self.sel_info.setObjectName("Hint")
        foot.addWidget(self.info)
        foot.addStretch(1)
        foot.addWidget(self.sel_info)
        root.addLayout(foot)

    # ------------------------------------------------------------ refreshing --
    def refresh(self) -> None:
        df = self.df
        prev = self.search_col.currentText()
        self.search_col.blockSignals(True)
        self.search_col.clear()
        self.search_col.addItem("all columns")
        self.search_col.addItems([str(c) for c in df.columns])
        i = self.search_col.findText(prev)
        if i >= 0:
            self.search_col.setCurrentIndex(i)
        self.search_col.blockSignals(False)
        self._apply_search()

    def _apply_search(self) -> None:
        df = self.df
        text = self.search.text().strip()
        if df.empty:
            self.table.set_df(pd.DataFrame())
            self.info.setText("No data loaded")
            self._filtered = None
            return

        view = df
        if text:
            col = self.search_col.currentText()
            regex = self.regex_cb.isChecked()
            case = self.case_cb.isChecked()
            try:
                if col and col != "all columns" and col in df.columns:
                    mask = df[col].astype(str).str.contains(
                        text, case=case, regex=regex, na=False)
                else:
                    joined = df.astype(str).apply(
                        lambda r: "".join(r.to_numpy()), axis=1)
                    mask = joined.str.contains(text, case=case, regex=regex, na=False)
                view = df[mask]
                self.search.setProperty("state", "")
            except Exception:
                self.search.setProperty("state", "error")
            self.search.style().unpolish(self.search)
            self.search.style().polish(self.search)

        self._filtered = view if text else None
        self.table.set_df(view)
        shown = f"{len(view):,}"
        total = f"{len(df):,}"
        extra = f" (filtered from {total})" if text else ""
        mem = df.memory_usage(deep=True).sum() / 1024 / 1024
        self.info.setText(f"{shown} rows{extra} · {df.shape[1]} columns · {mem:.1f} MB")

    def _update_selection_stats(self) -> None:
        idxs = self.table.selectionModel().selectedIndexes()
        if len(idxs) < 2:
            self.sel_info.setText("")
            return
        df = self.table.model_.df
        vals: list[float] = []
        for i in idxs[:20_000]:
            try:
                v = df.iat[i.row(), i.column()]
            except Exception:
                continue
            if isinstance(v, (int, float, np.integer, np.floating)) and pd.notna(v):
                vals.append(float(v))
        if vals:
            arr = np.array(vals)
            self.sel_info.setText(
                f"selected: {len(idxs):,} cells · numeric: {len(arr):,} · "
                f"sum: {arr.sum():,.3f} · mean: {arr.mean():,.3f} · "
                f"min: {arr.min():,.3f} · max: {arr.max():,.3f}")
        else:
            self.sel_info.setText(f"selected: {len(idxs):,} cells")

    # -------------------------------------------------------------- actions --
    def _on_edit(self, row: int, col: str, value) -> None:
        if self._filtered is not None:
            # editing a filtered view — map back to the original index
            try:
                real = self.df.index.get_loc(self._filtered.index[row])
            except Exception:
                self.notify("This cell cannot be edited in a filtered view", "warn")
                return
            row = int(real)
        self.store.set_cell(row, col, value)

    def _add_column(self) -> None:
        name, ok = QInputDialog.getText(self, "New column", "Column name:")
        if ok and name.strip():
            self.store.add_column(name.strip())

    def _delete_rows(self) -> None:
        rows = self.table.selected_rows()
        if not rows:
            self.notify("Select some rows first", "warn")
            return
        if len(rows) > 20 and QMessageBox.question(
                self, "Confirm", f"Delete {len(rows):,} rows?") \
                != QMessageBox.StandardButton.Yes:
            return
        if self._filtered is not None:
            labels = self._filtered.index[rows]
            new = self.df.drop(index=labels)
            self.store.commit(new, f"{len(rows)} rows deleted")
        else:
            self.store.run_op("drop_rows", indices=rows)

    def _commit_filter(self) -> None:
        if self._filtered is None:
            self.notify("Type a search term first", "warn")
            return
        self.store.commit(self._filtered.copy(),
                          f"Search filter: '{self.search.text().strip()}'")
        self.search.clear()

    def _toggle_heat(self, on: bool) -> None:
        col = self.table.current_column() if on else None
        self.table.model_.heat_column = col
        self.table.model_.layoutChanged.emit()
        if on and not col:
            self.notify("Select a cell in a numeric column first", "warn")

    def _on_column_action(self, action: str, column: str) -> None:
        df = self.df
        if action == "sort_asc":
            self.store.run_op("sort", by=[column], ascending=True)
        elif action == "sort_desc":
            self.store.run_op("sort", by=[column], ascending=False)
        elif action == "drop":
            self.store.run_op("drop_cols", columns=[column])
        elif action == "rename":
            new, ok = QInputDialog.getText(self, "Rename", "New name:", text=column)
            if ok and new.strip():
                self.store.run_op("rename", column=column, new_name=new.strip())
        elif action == "astype":
            spec = next(p for p in transform.OPS["astype"].params if p["name"] == "dtype")
            choice, ok = QInputDialog.getItem(self, "Type", "New type:",
                                              spec["options"], 0, False)
            if ok:
                self.store.run_op("astype", column=column, dtype=choice)
        elif action == "fillna":
            spec = next(p for p in transform.OPS["fillna"].params if p["name"] == "method")
            choice, ok = QInputDialog.getItem(self, "Fill", "Method:",
                                              spec["options"], 2, False)
            if ok:
                self.store.run_op("fillna", columns=[column], method=choice)
        elif action == "heat":
            self.table.model_.heat_column = column
            self.heat_cb.setChecked(True)
            self.table.model_.layoutChanged.emit()
        elif action == "stats":
            self._show_stats(column)
        elif action == "copy":
            from PySide6.QtGui import QGuiApplication

            QGuiApplication.clipboard().setText(
                "\n".join(df[column].astype(str).head(100_000)))
            self.notify(f"Column '{column}' copied", "success")
        elif action == "drop_rows":
            self._delete_rows()
        elif action == "filter_value":
            idx = self.table.currentIndex()
            if idx.isValid():
                model_df = self.table.model_.df
                col = str(model_df.columns[idx.column()])
                val = model_df.iat[idx.row(), idx.column()]
                self.search_col.setCurrentText(col)
                self.search.setText(str(val))

    def _show_stats(self, column: str) -> None:
        from ...core.profile import profile_column

        cp = profile_column(self.df[column], column)
        lines = [f"Column: {cp.name}", f"Kind: {cp.kind} ({cp.dtype})",
                 f"Filled: {cp.count:,}", f"Missing: {cp.missing:,} ({cp.missing_pct:.2f}%)",
                 f"Unique: {cp.unique:,} ({cp.unique_pct:.2f}%)", ""]
        for k, v in cp.stats.items():
            lines.append(f"{k}: {v if not isinstance(v, float) else f'{v:,.4f}'}")
        if cp.top:
            lines.append("\nMost frequent values:")
            for val, cnt in cp.top[:10]:
                lines.append(f"  {str(val)[:60]}  —  {cnt:,}")
        box = QMessageBox(self)
        box.setWindowTitle(f"Statistics — {column}")
        box.setText("<pre style='font-family:Consolas,monospace'>"
                    + "\n".join(lines) + "</pre>")
        box.exec()
