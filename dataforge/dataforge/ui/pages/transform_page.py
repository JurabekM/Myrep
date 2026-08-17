"""Tahrirlash sahifasi — 30 dan ortiq amal, dinamik forma va tarix bilan."""
from __future__ import annotations

from typing import Any

import pandas as pd
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QComboBox, QDoubleSpinBox, QFormLayout, QHBoxLayout,
                               QLabel, QLineEdit, QListWidget, QListWidgetItem,
                               QSplitter, QTreeWidget, QTreeWidgetItem, QVBoxLayout,
                               QWidget)

from ...core import transform
from ..widgets import (Card, FrameTable, MultiColumnSelect, PageHeader, make_button,
                       make_checkbox)
from .base import BasePage

KIND_MAP = {"col": "any", "numcol": "num", "catcol": "cat", "dtcol": "dt",
            "cols": "any", "numcols": "num", "catcols": "cat"}


class TransformPage(BasePage):
    title = "Tahrirlash"
    subtitle = ("Filtr, tozalash, matn amallari, yangi ustunlar, kodlash, guruhlash — "
                "har bir amal bekor qilinadi va tarixda saqlanadi.")

    def __init__(self, store, parent=None) -> None:
        super().__init__(store, parent)
        self._widgets: dict[str, tuple[str, Any]] = {}
        self._current: transform.OpSpec | None = None
        self._build()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 16)
        root.setSpacing(12)
        root.addWidget(PageHeader(self.title, self.subtitle))

        split = QSplitter(Qt.Orientation.Horizontal)
        split.setChildrenCollapsible(False)

        # ---------------- chap: amallar daraxti
        left = QWidget()
        lv = QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 0, 0)
        lv.setSpacing(10)

        card_ops = Card("Amallar", f"{len(transform.OPS)} ta")
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setMinimumWidth(230)
        self.tree.currentItemChanged.connect(self._on_op_selected)
        for group, specs in sorted(transform.op_groups().items()):
            node = QTreeWidgetItem([group])
            node.setFlags(Qt.ItemFlag.ItemIsEnabled)
            font = node.font(0)
            font.setBold(True)
            node.setFont(0, font)
            for spec in specs:
                child = QTreeWidgetItem([spec.label])
                child.setData(0, Qt.ItemDataRole.UserRole, spec.key)
                child.setToolTip(0, spec.doc)
                node.addChild(child)
            self.tree.addTopLevelItem(node)
        self.tree.expandAll()
        card_ops.add(self.tree)
        lv.addWidget(card_ops, 1)
        split.addWidget(left)

        # ---------------- markaz: forma
        mid = QWidget()
        mv = QVBoxLayout(mid)
        mv.setContentsMargins(0, 0, 0, 0)
        mv.setSpacing(10)

        self.form_card = Card("Amal sozlamalari", "chapdan amalni tanlang")
        self.doc_label = QLabel("")
        self.doc_label.setObjectName("Hint")
        self.doc_label.setWordWrap(True)
        self.form_card.add(self.doc_label)

        self.form_host = QWidget()
        self.form = QFormLayout(self.form_host)
        self.form.setContentsMargins(0, 6, 0, 6)
        self.form.setSpacing(9)
        self.form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        self.form_card.add(self.form_host)

        btns = QHBoxLayout()
        self.apply_btn = make_button("Qo'llash", "Primary", self._apply)
        self.apply_btn.setEnabled(False)
        btns.addWidget(self.apply_btn)
        btns.addWidget(make_button("Bekor (undo)", "Ghost", self.store.undo))
        btns.addWidget(make_button("Qaytar (redo)", "Ghost", self.store.redo))
        btns.addStretch(1)
        self.form_card.add_layout(btns)
        mv.addWidget(self.form_card)

        quick = Card("Tez amallar", "eng ko'p ishlatiladigan")
        qrow1 = QHBoxLayout()
        for label, key, params in (
            ("Dublikatlarni o'chirish", "drop_duplicates", {}),
            ("Bo'sh qatorlarni o'chirish", "dropna", {"how": "all"}),
            ("Doimiy ustunlarni o'chirish", "remove_constant", {}),
            ("Indeksni tiklash", "reset_index", {}),
        ):
            qrow1.addWidget(make_button(label, "Chip",
                                        lambda k=key, p=params: self.store.run_op(k, **p)))
        qrow1.addStretch(1)
        quick.add_layout(qrow1)
        mv.addWidget(quick)

        hist = Card("Amallar tarixi", "bosib o'sha holatga qayting")
        self.history_list = QListWidget()
        self.history_list.setMaximumHeight(190)
        self.history_list.itemClicked.connect(self._on_history_click)
        hist.add(self.history_list)
        mv.addWidget(hist, 1)
        split.addWidget(mid)

        # ---------------- o'ng: natija
        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setContentsMargins(0, 0, 0, 0)
        rv.setSpacing(10)
        prev = Card("Natija", "birinchi 200 qator")
        self.preview = FrameTable(editable=False)
        prev.add(self.preview)
        self.shape_label = QLabel("")
        self.shape_label.setObjectName("Hint")
        prev.add(self.shape_label)
        rv.addWidget(prev, 1)
        split.addWidget(right)

        split.setSizes([260, 430, 560])
        root.addWidget(split, 1)

    # ------------------------------------------------------------ forma ----
    def _on_op_selected(self, item: QTreeWidgetItem | None, _prev=None) -> None:
        if item is None:
            return
        key = item.data(0, Qt.ItemDataRole.UserRole)
        if not key:
            return
        spec = transform.OPS.get(key)
        if spec is None:
            return
        self._current = spec
        self.form_card.title_label.setText(spec.label)
        self.doc_label.setText(spec.doc)
        self.apply_btn.setEnabled(True)
        self._build_form(spec)

    def _clear_form(self) -> None:
        while self.form.count():
            item = self.form.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()
        self._widgets.clear()

    def _build_form(self, spec: transform.OpSpec) -> None:
        self._clear_form()
        df = self.df
        for p in spec.params:
            if p.get("hidden"):
                continue
            ptype = p.get("type", "text")
            label = p["label"] + ("" if not p.get("optional") else " (ixtiyoriy)")
            widget: Any

            if ptype in ("col", "numcol", "catcol", "dtcol"):
                widget = QComboBox()
                widget.addItem("—") if p.get("optional") else None
                kind = KIND_MAP.get(ptype, "any")
                from ..widgets import KIND_FILTERS

                test = KIND_FILTERS.get(kind, KIND_FILTERS["any"])
                for c in df.columns:
                    try:
                        if test(df[c]):
                            widget.addItem(str(c))
                    except Exception:
                        continue
            elif ptype in ("cols", "numcols", "catcols"):
                widget = MultiColumnSelect(kind=KIND_MAP.get(ptype, "any"), height=120)
                widget.populate(df)
            elif ptype == "bool":
                widget = make_checkbox("", bool(p.get("default", False)))
            elif ptype == "number":
                widget = QDoubleSpinBox()
                widget.setRange(-1e12, 1e12)
                widget.setDecimals(4)
                widget.setValue(float(p.get("default", 0)))
                if p.get("optional"):
                    widget.setSpecialValueText("—")
                    widget.setMinimum(-1e12)
            elif ptype == "choice":
                widget = QComboBox()
                widget.addItems([str(o) for o in p.get("options", [])])
                if p.get("default") in p.get("options", []):
                    widget.setCurrentText(str(p["default"]))
            elif ptype == "multichoice":
                widget = QListWidget()
                widget.setMaximumHeight(120)
                defaults = set(p.get("default", []))
                for o in p.get("options", []):
                    it = QListWidgetItem(str(o))
                    it.setFlags(it.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                    it.setCheckState(Qt.CheckState.Checked if o in defaults
                                     else Qt.CheckState.Unchecked)
                    widget.addItem(it)
            else:
                widget = QLineEdit()
                widget.setPlaceholderText(p.get("placeholder", ""))
                if p.get("default") is not None:
                    widget.setText(str(p["default"]))

            self._widgets[p["name"]] = (ptype, widget)
            self.form.addRow(label, widget)

    def _read_form(self) -> dict[str, Any]:
        values: dict[str, Any] = {}
        for name, (ptype, widget) in self._widgets.items():
            if ptype in ("col", "numcol", "catcol", "dtcol", "choice"):
                txt = widget.currentText()
                values[name] = None if txt in ("", "—") else txt
            elif ptype in ("cols", "numcols", "catcols"):
                values[name] = widget.values()
            elif ptype == "bool":
                values[name] = widget.isChecked()
            elif ptype == "number":
                values[name] = widget.value()
            elif ptype == "multichoice":
                values[name] = [widget.item(i).text() for i in range(widget.count())
                                if widget.item(i).checkState() == Qt.CheckState.Checked]
            else:
                txt = widget.text().strip()
                values[name] = txt or None
        return values

    def _apply(self) -> None:
        if self._current is None:
            return
        if not self.has_data():
            self.notify("Avval ma'lumot yuklang", "warn")
            return
        params = self._read_form()
        spec = self._current
        # majburiy maydonlarni tekshirish
        for p in spec.params:
            if p.get("optional") or p.get("hidden"):
                continue
            v = params.get(p["name"])
            if v in (None, "", []):
                self.notify(f"'{p['label']}' maydonini to'ldiring", "warn")
                return
        clean = {k: v for k, v in params.items() if v is not None}
        self.store.run_op(spec.key, **clean)

    # ------------------------------------------------------------ tarix ----
    def _on_history_click(self, item: QListWidgetItem) -> None:
        idx = self.history_list.row(item)
        self.store.goto_history(idx)

    def refresh(self) -> None:
        df = self.df
        self.preview.set_df(df.head(200))
        self.shape_label.setText(
            f"{len(df):,} qator × {df.shape[1]} ustun" if not df.empty
            else "Ma'lumot yuklanmagan")

        hist = self.store.history()
        self.history_list.clear()
        if hist:
            for i, entry in enumerate(hist.entries()):
                mark = "▶ " if i == hist.index else "   "
                item = QListWidgetItem(
                    f"{mark}{i + 1}. {entry.label}  ·  {entry.shape[0]:,}×{entry.shape[1]}")
                if i == hist.index:
                    f = item.font()
                    f.setBold(True)
                    item.setFont(f)
                elif i > hist.index:
                    item.setForeground(Qt.GlobalColor.gray)
                self.history_list.addItem(item)
            self.history_list.scrollToBottom()

        if self._current is not None and not df.empty:
            self._build_form(self._current)
