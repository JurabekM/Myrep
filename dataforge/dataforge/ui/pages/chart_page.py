"""Grafiklar sahifasi — 25 xil vizualizatsiya turi, jonli sozlash bilan."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QComboBox, QFileDialog, QHBoxLayout, QLabel,
                               QLineEdit, QListWidget, QListWidgetItem, QSpinBox,
                               QSplitter, QVBoxLayout, QWidget)

from ...config import EXPORTS_DIR
from ...core import charting
from ..widgets import (Card, ChartCanvas, ColumnCombo, PageHeader, ScrollPage,
                       make_button, make_checkbox)
from .base import BasePage

AGGS = ["count", "mean", "sum", "median", "min", "max", "std", "nunique"]


class ChartPage(BasePage):
    title = "Grafiklar"
    subtitle = ("Chiziqli, ustunli, taqsimot, issiqlik xaritasi, vaqt qatori va boshqa "
                "25 xil grafik. Har birini PNG/SVG sifatida saqlash mumkin.")

    def __init__(self, store, parent=None) -> None:
        super().__init__(store, parent)
        self._gallery: list[tuple[object, str]] = []
        self._build()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 16)
        root.setSpacing(12)
        root.addWidget(PageHeader(self.title, self.subtitle))

        split = QSplitter(Qt.Orientation.Horizontal)
        split.setChildrenCollapsible(False)

        # ---------------- chap panel
        panel = ScrollPage(margins=(0, 0, 8, 0), spacing=10)
        panel.setMinimumWidth(330)
        panel.setMaximumWidth(390)
        panel.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        card_type = Card("Grafik turi")
        self.type_list = QListWidget()
        self.type_list.setMinimumHeight(210)
        for group, specs in charting.chart_groups().items():
            header = QListWidgetItem(f"── {group} ──")
            header.setFlags(Qt.ItemFlag.NoItemFlags)
            header.setForeground(Qt.GlobalColor.gray)
            self.type_list.addItem(header)
            for spec in specs:
                item = QListWidgetItem("   " + spec.label)
                item.setData(Qt.ItemDataRole.UserRole, spec.key)
                self.type_list.addItem(item)
        self.type_list.currentItemChanged.connect(self._on_type_changed)
        card_type.add(self.type_list)
        panel.add(card_type)

        card_fields = Card("Maydonlar")
        self.x_combo = ColumnCombo("any", allow_empty=True)
        self.y_combo = ColumnCombo("any", allow_empty=True)
        self.hue_combo = ColumnCombo("any", allow_empty=True)
        self.size_combo = ColumnCombo("num", allow_empty=True)
        self.agg_combo = QComboBox()
        self.agg_combo.addItems(AGGS)
        for label, w in (("X o'qi:", self.x_combo), ("Y o'qi:", self.y_combo),
                         ("Rang (hue):", self.hue_combo), ("O'lcham:", self.size_combo),
                         ("Jamlash:", self.agg_combo)):
            row = QHBoxLayout()
            lbl = QLabel(label)
            lbl.setFixedWidth(92)
            row.addWidget(lbl)
            row.addWidget(w, 1)
            card_fields.add_layout(row)
        panel.add(card_fields)

        card_opts = Card("Sozlamalar")
        row1 = QHBoxLayout()
        self.bins = QSpinBox()
        self.bins.setRange(5, 300)
        self.bins.setValue(40)
        row1.addWidget(QLabel("Bin:"))
        row1.addWidget(self.bins)
        self.top_n = QSpinBox()
        self.top_n.setRange(3, 60)
        self.top_n.setValue(12)
        row1.addWidget(QLabel("Top N:"))
        row1.addWidget(self.top_n)
        card_opts.add_layout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Chastota:"))
        self.freq = QComboBox()
        self.freq.addItems(["avtomatik", "1s", "1min", "5min", "15min", "1h",
                            "6h", "1D", "1W", "1ME"])
        row2.addWidget(self.freq, 1)
        card_opts.add_layout(row2)

        row3 = QHBoxLayout()
        self.logy = make_checkbox("log Y", False)
        self.logx = make_checkbox("log X", False)
        self.grid = make_checkbox("Setka", True)
        for w in (self.logy, self.logx, self.grid):
            row3.addWidget(w)
        row3.addStretch(1)
        card_opts.add_layout(row3)
        row3b = QHBoxLayout()
        self.trend = make_checkbox("Trend chizig'i", True)
        row3b.addWidget(self.trend)
        row3b.addStretch(1)
        card_opts.add_layout(row3b)

        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Grafik sarlavhasi (ixtiyoriy)")
        card_opts.add(self.title_edit)
        panel.add(card_opts)

        actions = Card("Amallar")
        arow = QHBoxLayout()
        arow.addWidget(make_button("Chizish", "Primary", self.draw))
        arow.addWidget(make_button("Saqlash…", "Ghost", self._save))
        arow.addWidget(make_button("Nusxalash", "Ghost", self._copy))
        actions.add_layout(arow)
        brow = QHBoxLayout()
        brow.addWidget(make_button("Hisobotga qo'shish", "Ghost", self._add_to_gallery,
                                   "Grafik hisobot sahifasida ishlatiladi"))
        self.gallery_label = QLabel("galereya: 0")
        self.gallery_label.setObjectName("Hint")
        brow.addWidget(self.gallery_label)
        brow.addStretch(1)
        actions.add_layout(brow)
        panel.add(actions)
        panel.add_stretch()
        split.addWidget(panel)

        # ---------------- o'ng: kanvas
        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setContentsMargins(0, 0, 0, 0)
        self.canvas = ChartCanvas()
        rv.addWidget(self.canvas, 1)
        self.hint = QLabel("")
        self.hint.setObjectName("Hint")
        self.hint.setWordWrap(True)
        rv.addWidget(self.hint)
        split.addWidget(right)
        split.setSizes([340, 820])
        root.addWidget(split, 1)

        # dastlabki tanlov
        for i in range(self.type_list.count()):
            if self.type_list.item(i).data(Qt.ItemDataRole.UserRole):
                self.type_list.setCurrentRow(i)
                break

    # ------------------------------------------------------------- mantiq --
    def current_kind(self) -> str | None:
        item = self.type_list.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _on_type_changed(self, item, _prev=None) -> None:
        kind = self.current_kind()
        if not kind:
            return
        spec = charting.CHART_TYPES[kind]
        need = ", ".join(spec.needs) or "—"
        opt = ", ".join(spec.optional) or "—"
        self.hint.setText(f"«{spec.label}» · majburiy maydonlar: {need} · "
                          f"ixtiyoriy: {opt}")
        self._retype_combos(spec)

    def _retype_combos(self, spec: charting.ChartSpec) -> None:
        df = self.df
        self.x_combo.kind = spec.x_kind if spec.x_kind != "any" else "any"
        self.y_combo.kind = spec.y_kind if spec.y_kind != "any" else "any"
        self.x_combo.populate(df)
        self.y_combo.populate(df)

    def refresh(self) -> None:
        df = self.df
        for combo in (self.x_combo, self.y_combo, self.hue_combo, self.size_combo):
            combo.populate(df)

    def _opts(self) -> dict:
        opts = {
            "bins": self.bins.value(),
            "top": self.top_n.value(),
            "logy": self.logy.isChecked(),
            "logx": self.logx.isChecked(),
            "grid": self.grid.isChecked(),
            "trend": self.trend.isChecked(),
        }
        if self.freq.currentText() != "avtomatik":
            opts["freq"] = self.freq.currentText()
        title = self.title_edit.text().strip()
        if title:
            opts["title"] = title
        return opts

    def draw(self) -> None:
        if not self.has_data():
            self.notify("Avval ma'lumot yuklang", "warn")
            return
        kind = self.current_kind()
        if not kind:
            self.notify("Grafik turini tanlang", "warn")
            return
        try:
            fig = charting.build_chart(
                self.df, kind,
                x=self.x_combo.value(), y=self.y_combo.value(),
                hue=self.hue_combo.value(), size=self.size_combo.value(),
                agg=self.agg_combo.currentText(), figsize=(10.5, 6.2),
                value=self.y_combo.value(), **self._opts())
            self.canvas.set_figure(fig)
        except Exception as exc:
            self.canvas.show_message(str(exc))
            self.notify(f"Grafik xatosi: {exc}", "error")

    def _save(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Grafikni saqlash", str(EXPORTS_DIR / "grafik.png"),
            "PNG (*.png);;SVG (*.svg);;PDF (*.pdf)")
        if path:
            self.canvas.save(path)
            self.notify(f"Saqlandi: {path}", "success")

    def _copy(self) -> None:
        self.canvas.copy_to_clipboard()
        self.notify("Grafik buferga nusxalandi", "success")

    def _add_to_gallery(self) -> None:
        kind = self.current_kind()
        if not kind:
            return
        caption = (self.title_edit.text().strip()
                   or charting.CHART_TYPES[kind].label)
        self._gallery.append((self.canvas.figure, caption))
        self.gallery_label.setText(f"galereya: {len(self._gallery)}")
        self.notify(f"Hisobot galereyasiga qo'shildi ({len(self._gallery)} ta)",
                    "success")

    # hisobot sahifasi shu orqali grafiklarni oladi
    def gallery(self) -> list[tuple[object, str]]:
        return list(self._gallery)

    def clear_gallery(self) -> None:
        self._gallery.clear()
        self.gallery_label.setText("galereya: 0")
