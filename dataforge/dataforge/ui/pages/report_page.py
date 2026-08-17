"""Hisobot sahifasi — HTML hisobot yig'ish va eksport."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QFileDialog, QHBoxLayout, QLabel, QLineEdit,
                               QPlainTextEdit, QVBoxLayout, QWidget)

from ...config import EXPORTS_DIR
from ...core import charting, ingest, profile as prof_mod, report
from ..tasks import run_async
from ..widgets import Card, PageHeader, make_button, make_checkbox
from .base import BasePage


class ReportPage(BasePage):
    title = "Hisobot"
    subtitle = ("Profil, grafiklar va ML natijalarini bitta mustaqil HTML faylga "
                "jamlang — hech qanday tashqi bog'liqliksiz ochiladi.")

    def __init__(self, store, chart_page=None, ml_page=None, parent=None) -> None:
        super().__init__(store, parent)
        self.chart_page = chart_page
        self.ml_page = ml_page
        self._html: str | None = None
        self._build()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 16)
        root.setSpacing(12)
        root.addWidget(PageHeader(self.title, self.subtitle))

        cfg = Card("Hisobot tarkibi")
        row = QHBoxLayout()
        row.addWidget(QLabel("Sarlavha:"))
        self.title_edit = QLineEdit("Ma'lumot tahlili hisoboti")
        row.addWidget(self.title_edit, 1)
        cfg.add_layout(row)

        opts = QHBoxLayout()
        self.opt_profile = make_checkbox("Profil va sifat tahlili", True)
        self.opt_charts = make_checkbox("Galereyadagi grafiklar", True)
        self.opt_auto_charts = make_checkbox("Avtomatik grafiklar", True)
        self.opt_ml = make_checkbox("ML natijalari", True)
        self.opt_history = make_checkbox("Tahrirlar tarixi", True)
        for w in (self.opt_profile, self.opt_charts, self.opt_auto_charts,
                  self.opt_ml, self.opt_history):
            opts.addWidget(w)
        opts.addStretch(1)
        cfg.add_layout(opts)

        btns = QHBoxLayout()
        btns.addWidget(make_button("Hisobotni yaratish", "Primary", self._build_report))
        btns.addWidget(make_button("Saqlash va ochish…", "Ghost", self._save_open))
        btns.addWidget(make_button("Ma'lumotni eksport…", "Ghost", self._export_data))
        btns.addStretch(1)
        cfg.add_layout(btns)
        self.status = QLabel("")
        self.status.setObjectName("Hint")
        self.status.setWordWrap(True)
        cfg.add(self.status)
        root.addWidget(cfg)

        prev = Card("Hisobot ko'rinishi (HTML manba)", "birinchi 4000 belgi")
        self.preview = QPlainTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setObjectName("Mono")
        prev.add(self.preview)
        root.addWidget(prev, 1)

    # ------------------------------------------------------------ mantiq ---
    def _build_report(self) -> None:
        if not self.has_data():
            self.notify("Avval ma'lumot yuklang", "warn")
            return
        df = self.df
        name = self.store.active_name or "dataset"
        title = self.title_edit.text().strip() or "Ma'lumot tahlili hisoboti"

        figures: list[tuple[object, str]] = []
        if self.opt_charts.isChecked() and self.chart_page is not None:
            figures.extend(self.chart_page.gallery())
        if self.opt_auto_charts.isChecked():
            figures.extend(self._auto_figures(df))

        ml_res = None
        if self.opt_ml.isChecked() and self.ml_page is not None:
            ml_res = self.ml_page.result

        history = self.store.history_labels() if self.opt_history.isChecked() else None
        profile = prof_mod.profile_dataframe(df) if self.opt_profile.isChecked() else None

        self.status.setText("Hisobot yig'ilmoqda…")
        run_async(report.build_report, df, title=title, dataset_name=name,
                  profile=profile, figures=figures, ml_result=ml_res,
                  history=history,
                  on_done=self._on_built,
                  on_error=lambda m: self._fail(m))

    def _auto_figures(self, df) -> list[tuple[object, str]]:
        """Ma'lumot turiga qarab foydali grafiklarni avtomatik quradi."""
        out: list[tuple[object, str]] = []
        try:
            nums = prof_mod.numeric_columns(df)
            dts = prof_mod.datetime_columns(df)
            cats = prof_mod.categorical_columns(df, max_card=30)

            if df.isna().sum().sum() > 0:
                out.append((charting.build_chart(df, "missing", figsize=(9, 4)),
                            "Bo'sh qiymatlar xaritasi"))
            if len(nums) >= 2:
                out.append((charting.build_chart(df, "corr", figsize=(8, 5.5)),
                            "Korrelyatsiya matritsasi"))
            if dts:
                out.append((charting.build_chart(df, "timeseries", x=dts[0],
                                                 figsize=(9.5, 4.2)),
                            f"Vaqt bo'yicha hodisalar zichligi ({dts[0]})"))
            for c in nums[:3]:
                out.append((charting.build_chart(df, "hist", x=c, figsize=(8, 3.4)),
                            f"'{c}' taqsimoti"))
            for c in cats[:3]:
                out.append((charting.build_chart(df, "bar", x=c, agg="count",
                                                 figsize=(8, 3.4)),
                            f"'{c}' bo'yicha taqsimot"))
        except Exception:
            pass
        return out

    def _on_built(self, html: str) -> None:
        self._html = html
        self.preview.setPlainText(html[:4000] + "\n…")
        size = len(html.encode("utf-8")) / 1024
        self.status.setText(f"✓ Hisobot tayyor · {size:,.0f} KB · endi saqlang")
        self.notify("Hisobot yaratildi", "success")

    def _fail(self, msg: str) -> None:
        first = msg.splitlines()[0]
        self.status.setText(f"Xato: {first}")
        self.notify(first, "error")

    def _save_open(self) -> None:
        if self._html is None:
            self._build_report()
            self.notify("Hisobot yaratilmoqda — tayyor bo'lgach yana bosing", "info")
            return
        name = (self.store.active_name or "hisobot").replace(" ", "_")
        path, _ = QFileDialog.getSaveFileName(
            self, "Hisobotni saqlash", str(EXPORTS_DIR / f"{name}_hisobot.html"),
            "HTML (*.html)")
        if not path:
            return
        report.save_report(self._html, path)
        self.status.setText(f"✓ Saqlandi: {path}")
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(path).resolve())))

    def _export_data(self) -> None:
        if not self.has_data():
            self.notify("Ma'lumot yo'q", "warn")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Ma'lumotni eksport qilish",
            str(EXPORTS_DIR / f"{self.store.active_name}.csv"),
            "CSV (*.csv);;Excel (*.xlsx);;Parquet (*.parquet);;JSON (*.json);;"
            "JSON Lines (*.jsonl);;SQLite (*.db);;HTML (*.html);;Markdown (*.md)")
        if not path:
            return
        try:
            ingest.export_df(self.df, path)
            self.notify(f"Saqlandi: {path}", "success")
            self.status.setText(f"✓ Ma'lumot saqlandi: {path}")
        except Exception as exc:
            self._fail(str(exc))
