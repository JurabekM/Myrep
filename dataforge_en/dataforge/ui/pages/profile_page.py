"""Profile page — deep statistics, quality checks and relationship analysis."""
from __future__ import annotations

import pandas as pd
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QComboBox, QHBoxLayout, QLabel, QListWidget,
                               QListWidgetItem, QTabWidget, QVBoxLayout, QWidget)

from ...config import PALETTE
from ...core import charting, profile as prof_mod
from ..tasks import run_async
from ..widgets import (Card, ChartCanvas, FrameTable, MultiColumnSelect, PageHeader,
                       StatTile, make_button)
from .base import BasePage


class ProfilePage(BasePage):
    title = "Profile and analysis"
    subtitle = ("Full statistics per column, automatic data quality warnings and "
                "relationship analysis.")

    def __init__(self, store, parent=None) -> None:
        super().__init__(store, parent)
        self._profile = None
        self._build()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 16)
        root.setSpacing(12)
        root.addWidget(PageHeader(self.title, self.subtitle))

        # ---- metric tiles
        tiles = QHBoxLayout()
        tiles.setSpacing(10)
        self.tiles: dict[str, StatTile] = {}
        for key, label in (("rows", "Rows"), ("cols", "Columns"),
                           ("memory", "Memory"), ("missing", "Missing"),
                           ("dupes", "Duplicates"), ("quality", "Quality score")):
            tile = StatTile(label)
            self.tiles[key] = tile
            tiles.addWidget(tile)
        root.addLayout(tiles)

        row = QHBoxLayout()
        self.run_btn = make_button("Compute profile", "Primary", self._run_profile)
        row.addWidget(self.run_btn)
        self.status = QLabel("")
        self.status.setObjectName("Hint")
        row.addWidget(self.status)
        row.addStretch(1)
        root.addLayout(row)

        # ---- tabs
        self.tabs = QTabWidget()
        self.tabs.addTab(self._tab_columns(), "Columns")
        self.tabs.addTab(self._tab_issues(), "Quality issues")
        self.tabs.addTab(self._tab_corr(), "Relationships")
        self.tabs.addTab(self._tab_group(), "Group / Pivot")
        self.tabs.addTab(self._tab_time(), "Time analysis")
        root.addWidget(self.tabs, 1)

    # --------------------------------------------------------------- tabs --
    def _tab_columns(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(12, 12, 12, 12)
        self.col_table = FrameTable(editable=False)
        lay.addWidget(self.col_table, 3)
        hint = QLabel("Click a column row to see its distribution below.")
        hint.setObjectName("Hint")
        lay.addWidget(hint)
        self.col_chart = ChartCanvas(toolbar=False)
        self.col_chart.setMinimumHeight(200)
        lay.addWidget(self.col_chart, 2)
        self.col_table.clicked.connect(self._on_column_click)
        return w

    def _tab_issues(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(12, 12, 12, 12)
        self.issues_list = QListWidget()
        self.issues_list.setWordWrap(True)
        lay.addWidget(self.issues_list)
        return w

    def _tab_corr(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(10)
        row = QHBoxLayout()
        row.addWidget(QLabel("Method:"))
        self.corr_method = QComboBox()
        self.corr_method.addItems(["pearson", "spearman", "kendall"])
        self.corr_method.currentTextChanged.connect(lambda _: self._draw_corr())
        row.addWidget(self.corr_method)
        row.addWidget(make_button("Categorical association (Cramér's V)", "Ghost",
                                  self._draw_cramers))
        row.addStretch(1)
        lay.addLayout(row)
        self.corr_canvas = ChartCanvas()
        lay.addWidget(self.corr_canvas, 2)
        self.corr_table = FrameTable(editable=False)
        self.corr_table.setMaximumHeight(200)
        lay.addWidget(self.corr_table, 1)
        return w

    def _tab_group(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(10)
        row = QHBoxLayout()
        row.addWidget(QLabel("Group by:"))
        self.group_by = MultiColumnSelect(kind="any", height=100)
        self.group_by.setMaximumWidth(260)
        row.addWidget(self.group_by)
        row.addWidget(QLabel("Value:"))
        self.group_value = QComboBox()
        self.group_value.setMinimumWidth(160)
        row.addWidget(self.group_value)
        row.addWidget(make_button("Compute", "Primary", self._run_group))
        row.addWidget(make_button("Save result as a new table", "Ghost",
                                  self._group_to_dataset))
        row.addStretch(1)
        lay.addLayout(row)
        self.group_table = FrameTable(editable=False)
        lay.addWidget(self.group_table, 1)
        return w

    def _tab_time(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(10)
        row = QHBoxLayout()
        row.addWidget(QLabel("Time column:"))
        self.time_col = QComboBox()
        self.time_col.setMinimumWidth(170)
        row.addWidget(self.time_col)
        row.addWidget(QLabel("Frequency:"))
        self.time_freq = QComboBox()
        self.time_freq.addItems(["auto", "1s", "1min", "5min", "15min",
                                 "1h", "6h", "1D", "1W", "1ME"])
        row.addWidget(self.time_freq)
        row.addWidget(QLabel("Value:"))
        self.time_value = QComboBox()
        self.time_value.setMinimumWidth(150)
        row.addWidget(self.time_value)
        row.addWidget(QLabel("Function:"))
        self.time_agg = QComboBox()
        self.time_agg.addItems(["count", "mean", "sum", "max", "min", "median"])
        row.addWidget(self.time_agg)
        row.addWidget(make_button("Plot", "Primary", self._draw_time))
        row.addStretch(1)
        lay.addLayout(row)
        self.time_canvas = ChartCanvas()
        lay.addWidget(self.time_canvas, 1)
        return w

    # --------------------------------------------------------------- logic --
    def refresh(self) -> None:
        df = self.df
        self.group_by.populate(df)
        for combo, kind in ((self.group_value, "num"), (self.time_value, "num")):
            combo.blockSignals(True)
            prev = combo.currentText()
            combo.clear()
            combo.addItem("—")
            combo.addItems([c for c in df.columns
                            if pd.api.types.is_numeric_dtype(df[c])])
            i = combo.findText(prev)
            if i >= 0:
                combo.setCurrentIndex(i)
            combo.blockSignals(False)
        self.time_col.blockSignals(True)
        prev = self.time_col.currentText()
        self.time_col.clear()
        self.time_col.addItems(prof_mod.datetime_columns(df))
        i = self.time_col.findText(prev)
        if i >= 0:
            self.time_col.setCurrentIndex(i)
        self.time_col.blockSignals(False)
        self.status.setText("The data changed — recompute the profile."
                            if self._profile else "")

    def _run_profile(self) -> None:
        if not self.has_data():
            self.notify("Load some data first", "warn")
            return
        self.status.setText("Computing…")
        self.run_btn.setEnabled(False)
        run_async(prof_mod.profile_dataframe, self.df,
                  on_done=self._on_profile, on_error=self._on_error)

    def _on_error(self, msg: str) -> None:
        self.run_btn.setEnabled(True)
        self.status.setText("Error")
        self.notify(msg.splitlines()[0], "error")

    def _on_profile(self, p) -> None:
        self._profile = p
        self.run_btn.setEnabled(True)
        self.status.setText("✓ Profile ready")

        self.tiles["rows"].set_value(f"{p.rows:,}")
        self.tiles["cols"].set_value(f"{p.cols:,}")
        self.tiles["memory"].set_value(f"{p.memory_mb:.1f} MB")
        self.tiles["missing"].set_value(
            f"{p.missing_pct:.2f}%",
            accent=PALETTE["danger"] if p.missing_pct > 20 else
            (PALETTE["warning"] if p.missing_pct > 5 else PALETTE["success"]))
        self.tiles["dupes"].set_value(
            f"{p.duplicates:,}",
            accent=PALETTE["warning"] if p.duplicates else PALETTE["success"])
        score = p.quality_score
        self.tiles["quality"].set_value(
            f"{score:.0f}/100",
            accent=PALETTE["success"] if score >= 85 else
            (PALETTE["warning"] if score >= 60 else PALETTE["danger"]))

        self.col_table.set_df(p.to_frame())

        self.issues_list.clear()
        if not p.issues:
            self.issues_list.addItem("✓ No serious problems were found.")
        for iss in p.issues:
            color = {"high": PALETTE["danger"], "medium": PALETTE["warning"]}.get(
                iss.get("level", "low"), PALETTE["faint"])
            item = QListWidgetItem(
                f"[{iss.get('level', 'low').upper()}]  {iss['title']}  —  "
                f"{iss.get('column', '')}\n        {iss['detail']}")
            item.setToolTip(iss["detail"])
            item.setForeground(QColor(color))
            self.issues_list.addItem(item)
        self._draw_corr()

    def _on_column_click(self, index) -> None:
        if self._profile is None:
            return
        try:
            name = str(self._profile.to_frame().iloc[index.row()]["column"])
        except Exception:
            return
        df = self.df
        if name not in df.columns:
            return
        kind = prof_mod.column_kind(df[name])
        try:
            if kind == prof_mod.NUMERIC:
                fig = charting.build_chart(df, "hist", x=name, figsize=(9, 2.6))
            elif kind == prof_mod.DATETIME:
                fig = charting.build_chart(df, "timeseries", x=name, figsize=(9, 2.6))
            else:
                fig = charting.build_chart(df, "bar", x=name, agg="count",
                                           figsize=(9, 2.6))
            self.col_chart.set_figure(fig)
        except Exception as exc:
            self.col_chart.show_message(f"Could not draw the chart: {exc}")

    def _draw_corr(self) -> None:
        df = self.df
        if df.empty:
            return
        method = self.corr_method.currentText()
        try:
            corr = prof_mod.correlation(df, method=method)
            if corr.empty:
                self.corr_canvas.show_message("At least 2 numeric columns are required")
                self.corr_table.set_df(pd.DataFrame())
                return
            fig = charting.build_chart(df, "corr", method=method, figsize=(8.5, 5))
            self.corr_canvas.set_figure(fig)
            self.corr_table.set_df(prof_mod.top_correlations(corr, threshold=0.3))
        except Exception as exc:
            self.corr_canvas.show_message(f"Error: {exc}")

    def _draw_cramers(self) -> None:
        df = self.df
        try:
            m = prof_mod.categorical_association(df)
        except Exception as exc:
            self.notify(f"Could not compute: {exc}", "error")
            return
        if m.empty:
            self.notify("At least 2 categorical columns are required", "warn")
            return
        self.corr_table.set_df(m.reset_index().rename(columns={"index": "column"}))
        self.notify("The Cramér's V matrix is shown in the table", "success")

    def _run_group(self) -> None:
        by = self.group_by.values()
        if not by:
            self.notify("Choose a column to group by", "warn")
            return
        value = self.group_value.currentText()
        value = None if value in ("", "—") else value
        try:
            out = prof_mod.group_summary(self.df, by, value)
        except Exception as exc:
            self.notify(f"Error: {exc}", "error")
            return
        self._group_result = out
        self.group_table.set_df(out.head(5000))

    def _group_to_dataset(self) -> None:
        res = getattr(self, "_group_result", None)
        if res is None or res.empty:
            self.notify("Compute the grouping first", "warn")
            return
        self.store.add(f"{self.store.active_name}_grouped", res)

    def _draw_time(self) -> None:
        col = self.time_col.currentText()
        if not col:
            self.notify("No time column was found", "warn")
            return
        freq = self.time_freq.currentText()
        value = self.time_value.currentText()
        value = None if value in ("", "—") else value
        agg = self.time_agg.currentText()
        opts = {} if freq == "auto" else {"freq": freq}
        try:
            fig = charting.build_chart(self.df, "timeseries", x=col, y=value,
                                       agg=agg, figsize=(10, 5), **opts)
            self.time_canvas.set_figure(fig)
        except Exception as exc:
            self.time_canvas.show_message(f"Error: {exc}")
