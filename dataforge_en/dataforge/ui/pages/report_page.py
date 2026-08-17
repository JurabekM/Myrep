"""Report page — assemble and export the HTML report."""
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
    title = "Report"
    subtitle = ("Collect the profile, the charts and the ML results into a single "
                "self-contained HTML file that opens without any dependencies.")

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

        cfg = Card("Report contents")
        row = QHBoxLayout()
        row.addWidget(QLabel("Title:"))
        self.title_edit = QLineEdit("Data analysis report")
        row.addWidget(self.title_edit, 1)
        cfg.add_layout(row)

        opts = QHBoxLayout()
        self.opt_profile = make_checkbox("Profile and quality analysis", True)
        self.opt_charts = make_checkbox("Charts from the gallery", True)
        self.opt_auto_charts = make_checkbox("Automatic charts", True)
        self.opt_ml = make_checkbox("ML results", True)
        self.opt_history = make_checkbox("Edit history", True)
        for w in (self.opt_profile, self.opt_charts, self.opt_auto_charts,
                  self.opt_ml, self.opt_history):
            opts.addWidget(w)
        opts.addStretch(1)
        cfg.add_layout(opts)

        btns = QHBoxLayout()
        btns.addWidget(make_button("Build report", "Primary", self._build_report))
        btns.addWidget(make_button("Save and open…", "Ghost", self._save_open))
        btns.addWidget(make_button("Export data…", "Ghost", self._export_data))
        btns.addStretch(1)
        cfg.add_layout(btns)
        self.status = QLabel("")
        self.status.setObjectName("Hint")
        self.status.setWordWrap(True)
        cfg.add(self.status)
        root.addWidget(cfg)

        prev = Card("Report preview (HTML source)", "first 4000 characters")
        self.preview = QPlainTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setObjectName("Mono")
        prev.add(self.preview)
        root.addWidget(prev, 1)

    # ------------------------------------------------------------- logic ---
    def _build_report(self) -> None:
        if not self.has_data():
            self.notify("Load some data first", "warn")
            return
        df = self.df
        name = self.store.active_name or "dataset"
        title = self.title_edit.text().strip() or "Data analysis report"

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

        self.status.setText("Assembling the report…")
        run_async(report.build_report, df, title=title, dataset_name=name,
                  profile=profile, figures=figures, ml_result=ml_res,
                  history=history,
                  on_done=self._on_built,
                  on_error=lambda m: self._fail(m))

    def _auto_figures(self, df) -> list[tuple[object, str]]:
        """Build useful charts automatically based on the data types."""
        out: list[tuple[object, str]] = []
        try:
            nums = prof_mod.numeric_columns(df)
            dts = prof_mod.datetime_columns(df)
            cats = prof_mod.categorical_columns(df, max_card=30)

            if df.isna().sum().sum() > 0:
                out.append((charting.build_chart(df, "missing", figsize=(9, 4)),
                            "Missing value map"))
            if len(nums) >= 2:
                out.append((charting.build_chart(df, "corr", figsize=(8, 5.5)),
                            "Correlation matrix"))
            if dts:
                out.append((charting.build_chart(df, "timeseries", x=dts[0],
                                                 figsize=(9.5, 4.2)),
                            f"Event density over time ({dts[0]})"))
            for c in nums[:3]:
                out.append((charting.build_chart(df, "hist", x=c, figsize=(8, 3.4)),
                            f"Distribution of '{c}'"))
            for c in cats[:3]:
                out.append((charting.build_chart(df, "bar", x=c, agg="count",
                                                 figsize=(8, 3.4)),
                            f"Breakdown by '{c}'"))
        except Exception:
            pass
        return out

    def _on_built(self, html: str) -> None:
        self._html = html
        self.preview.setPlainText(html[:4000] + "\n…")
        size = len(html.encode("utf-8")) / 1024
        self.status.setText(f"✓ Report ready · {size:,.0f} KB · you can save it now")
        self.notify("Report generated", "success")

    def _fail(self, msg: str) -> None:
        first = msg.splitlines()[0]
        self.status.setText(f"Error: {first}")
        self.notify(first, "error")

    def _save_open(self) -> None:
        if self._html is None:
            self._build_report()
            self.notify("The report is being built — press again when it is ready",
                        "info")
            return
        name = (self.store.active_name or "report").replace(" ", "_")
        path, _ = QFileDialog.getSaveFileName(
            self, "Save the report", str(EXPORTS_DIR / f"{name}_report.html"),
            "HTML (*.html)")
        if not path:
            return
        report.save_report(self._html, path)
        self.status.setText(f"✓ Saved: {path}")
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(path).resolve())))

    def _export_data(self) -> None:
        if not self.has_data():
            self.notify("There is no data", "warn")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export the data",
            str(EXPORTS_DIR / f"{self.store.active_name}.csv"),
            "CSV (*.csv);;Excel (*.xlsx);;Parquet (*.parquet);;JSON (*.json);;"
            "JSON Lines (*.jsonl);;SQLite (*.db);;HTML (*.html);;Markdown (*.md)")
        if not path:
            return
        try:
            ingest.export_df(self.df, path)
            self.notify(f"Saved: {path}", "success")
            self.status.setText(f"✓ Data saved: {path}")
        except Exception as exc:
            self._fail(str(exc))
