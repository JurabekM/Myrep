"""Jadval sahifasi — ma'lumotni ko'rish, qidirish va to'g'ridan-to'g'ri tahrirlash."""
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
    title = "Jadval"
    subtitle = ("Kataklarni ikki marta bosib tahrirlang, ustun sarlavhasiga o'ng tugma "
                "bilan bosib amallarni chaqiring. Barcha o'zgarishlar tarixga yoziladi.")

    def __init__(self, store, parent=None) -> None:
        super().__init__(store, parent)
        self._filtered: pd.DataFrame | None = None
        self._build()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 16)
        root.setSpacing(12)
        root.addWidget(PageHeader(self.title, self.subtitle))

        # ---- qidiruv paneli
        bar = QHBoxLayout()
        bar.setSpacing(8)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Qidirish… (barcha ustunlar bo'yicha)")
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
        self.case_cb.setToolTip("Katta-kichik harf farqi")
        bar.addWidget(self.case_cb)
        bar.addWidget(make_button("Filtrni qo'llash", "Ghost", self._commit_filter,
                                  "Qidiruv natijasini jadvalga doimiy qo'llaydi"))
        bar.addStretch(1)
        root.addLayout(bar)

        # ---- amallar paneli
        acts = QHBoxLayout()
        acts.setSpacing(8)
        for text, tip, fn in (
            ("↶ Bekor", "Oxirgi amalni bekor qilish (Ctrl+Z)", self.store.undo),
            ("↷ Qaytar", "Qaytarish (Ctrl+Y)", self.store.redo),
        ):
            acts.addWidget(make_button(text, "Ghost", fn, tip))
        acts.addSpacing(12)
        acts.addWidget(make_button("+ Qator", "Ghost", lambda: self.store.add_row(),
                                   "Oxiriga bo'sh qator qo'shish"))
        acts.addWidget(make_button("+ Ustun", "Ghost", self._add_column))
        acts.addWidget(make_button("− Qatorlar", "Ghost", self._delete_rows,
                                   "Tanlangan qatorlarni o'chirish"))
        acts.addSpacing(12)
        acts.addWidget(make_button("Dublikatlarni o'chirish", "Ghost",
                                   lambda: self.store.run_op("drop_duplicates")))
        acts.addWidget(make_button("Bo'sh qatorlarni o'chirish", "Ghost",
                                   lambda: self.store.run_op("dropna", how="all")))
        self.heat_cb = make_checkbox("Issiqlik bo'yash", False, self._toggle_heat)
        self.heat_cb.setToolTip("Joriy sonli ustunni qiymatga qarab bo'yash")
        acts.addWidget(self.heat_cb)
        acts.addStretch(1)
        root.addLayout(acts)

        # ---- jadval
        self.table = FrameTable(editable=True)
        self.table.model_.edit_requested.connect(self._on_edit)
        self.table.column_action.connect(self._on_column_action)
        self.table.selectionModel().selectionChanged.connect(self._update_selection_stats)
        root.addWidget(self.table, 1)

        # ---- pastki qator
        foot = QHBoxLayout()
        self.info = QLabel("Ma'lumot yuklanmagan")
        self.info.setObjectName("Hint")
        self.sel_info = QLabel("")
        self.sel_info.setObjectName("Hint")
        foot.addWidget(self.info)
        foot.addStretch(1)
        foot.addWidget(self.sel_info)
        root.addLayout(foot)

    # ------------------------------------------------------------ yangilash --
    def refresh(self) -> None:
        df = self.df
        prev = self.search_col.currentText()
        self.search_col.blockSignals(True)
        self.search_col.clear()
        self.search_col.addItem("barcha ustunlar")
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
            self.info.setText("Ma'lumot yuklanmagan")
            self._filtered = None
            return

        view = df
        if text:
            col = self.search_col.currentText()
            regex = self.regex_cb.isChecked()
            case = self.case_cb.isChecked()
            try:
                if col and col != "barcha ustunlar" and col in df.columns:
                    mask = df[col].astype(str).str.contains(
                        text, case=case, regex=regex, na=False)
                else:
                    joined = df.astype(str).apply(
                        lambda r: "".join(r.to_numpy()), axis=1)
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
        extra = f" (jami {total} dan filtrlangan)" if text else ""
        mem = df.memory_usage(deep=True).sum() / 1024 / 1024
        self.info.setText(f"{shown} qator{extra} · {df.shape[1]} ustun · {mem:.1f} MB")

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
                f"tanlangan: {len(idxs):,} katak · son: {len(arr):,} · "
                f"yig'indi: {arr.sum():,.3f} · o'rtacha: {arr.mean():,.3f} · "
                f"min: {arr.min():,.3f} · maks: {arr.max():,.3f}")
        else:
            self.sel_info.setText(f"tanlangan: {len(idxs):,} katak")

    # -------------------------------------------------------------- amallar --
    def _on_edit(self, row: int, col: str, value) -> None:
        if self._filtered is not None:
            # filtrlangan ko'rinishda tahrirlash — asl indeksga moslash
            try:
                real = self.df.index.get_loc(self._filtered.index[row])
            except Exception:
                self.notify("Filtrlangan ko'rinishda bu katakni tahrirlab bo'lmadi", "warn")
                return
            row = int(real)
        self.store.set_cell(row, col, value)

    def _add_column(self) -> None:
        name, ok = QInputDialog.getText(self, "Yangi ustun", "Ustun nomi:")
        if ok and name.strip():
            self.store.add_column(name.strip())

    def _delete_rows(self) -> None:
        rows = self.table.selected_rows()
        if not rows:
            self.notify("Avval qatorlarni tanlang", "warn")
            return
        if len(rows) > 20 and QMessageBox.question(
                self, "Tasdiqlash", f"{len(rows):,} qator o'chirilsinmi?") \
                != QMessageBox.StandardButton.Yes:
            return
        if self._filtered is not None:
            labels = self._filtered.index[rows]
            new = self.df.drop(index=labels)
            self.store.commit(new, f"{len(rows)} qator o'chirildi")
        else:
            self.store.run_op("drop_rows", indices=rows)

    def _commit_filter(self) -> None:
        if self._filtered is None:
            self.notify("Avval qidiruv matnini kiriting", "warn")
            return
        self.store.commit(self._filtered.copy(),
                          f"Qidiruv filtri: '{self.search.text().strip()}'")
        self.search.clear()

    def _toggle_heat(self, on: bool) -> None:
        col = self.table.current_column() if on else None
        self.table.model_.heat_column = col
        self.table.model_.layoutChanged.emit()
        if on and not col:
            self.notify("Avval sonli ustunda katakni tanlang", "warn")

    def _on_column_action(self, action: str, column: str) -> None:
        df = self.df
        if action == "sort_asc":
            self.store.run_op("sort", by=[column], ascending=True)
        elif action == "sort_desc":
            self.store.run_op("sort", by=[column], ascending=False)
        elif action == "drop":
            self.store.run_op("drop_cols", columns=[column])
        elif action == "rename":
            new, ok = QInputDialog.getText(self, "Nomni o'zgartirish", "Yangi nom:",
                                           text=column)
            if ok and new.strip():
                self.store.run_op("rename", column=column, new_name=new.strip())
        elif action == "astype":
            spec = next(p for p in transform.OPS["astype"].params if p["name"] == "dtype")
            choice, ok = QInputDialog.getItem(self, "Turi", "Yangi tur:",
                                              spec["options"], 0, False)
            if ok:
                self.store.run_op("astype", column=column, dtype=choice)
        elif action == "fillna":
            spec = next(p for p in transform.OPS["fillna"].params if p["name"] == "method")
            choice, ok = QInputDialog.getItem(self, "To'ldirish", "Usul:",
                                              spec["options"], 1, False)
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
            self.notify(f"'{column}' ustuni nusxalandi", "success")
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
        lines = [f"Ustun: {cp.name}", f"Turi: {cp.kind} ({cp.dtype})",
                 f"To'ldirilgan: {cp.count:,}", f"Bo'sh: {cp.missing:,} ({cp.missing_pct:.2f}%)",
                 f"Unikal: {cp.unique:,} ({cp.unique_pct:.2f}%)", ""]
        for k, v in cp.stats.items():
            lines.append(f"{k}: {v if not isinstance(v, float) else f'{v:,.4f}'}")
        if cp.top:
            lines.append("\nEng ko'p uchraydigan:")
            for val, cnt in cp.top[:10]:
                lines.append(f"  {str(val)[:60]}  —  {cnt:,}")
        box = QMessageBox(self)
        box.setWindowTitle(f"Statistika — {column}")
        box.setText("<pre style='font-family:Consolas,monospace'>"
                    + "\n".join(lines) + "</pre>")
        box.exec()
