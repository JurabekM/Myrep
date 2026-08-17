"""Log AI — template mining, burst detection, text clustering, entity extraction."""
from __future__ import annotations

import pandas as pd
from PySide6.QtWidgets import (QComboBox, QDoubleSpinBox, QHBoxLayout, QLabel,
                               QPlainTextEdit, QSpinBox, QTabWidget, QVBoxLayout,
                               QWidget)

from ...config import PALETTE
from ...core import charting, logparse, ml
from ...core import profile as prof_mod
from ..tasks import run_async
from ..widgets import (Card, ChartCanvas, ColumnCombo, FrameTable, PageHeader,
                       StatTile, make_button, make_checkbox)
from .base import BasePage


class LogAIPage(BasePage):
    title = "Log AI"
    subtitle = ("Mine templates out of log messages, surface rare events, detect "
                "bursts and group messages into topics.")

    def __init__(self, store, parent=None) -> None:
        super().__init__(store, parent)
        self._templates: pd.DataFrame | None = None
        self._tids: pd.Series | None = None
        self._build()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 16)
        root.setSpacing(12)
        root.addWidget(PageHeader(self.title, self.subtitle))

        bar = QHBoxLayout()
        bar.setSpacing(8)
        bar.addWidget(QLabel("Text column:"))
        self.text_col = ColumnCombo("any")
        bar.addWidget(self.text_col)
        bar.addWidget(QLabel("Time column:"))
        self.time_col = ColumnCombo("dt", allow_empty=True)
        bar.addWidget(self.time_col)
        bar.addWidget(QLabel("Level column:"))
        self.level_col = ColumnCombo("cat", allow_empty=True)
        bar.addWidget(self.level_col)
        bar.addStretch(1)
        root.addLayout(bar)

        tiles = QHBoxLayout()
        self.tiles = {}
        for key, label in (("lines", "Lines"), ("templates", "Templates"),
                           ("rare", "Rare"), ("errors", "Error rate"),
                           ("bursts", "Bursts")):
            t = StatTile(label)
            self.tiles[key] = t
            tiles.addWidget(t)
        root.addLayout(tiles)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._tab_templates(), "Templates")
        # NB: a literal "&" would be swallowed as a Qt mnemonic in a tab label
        self.tabs.addTab(self._tab_burst(), "Bursts and dynamics")
        self.tabs.addTab(self._tab_cluster(), "Text clusters")
        self.tabs.addTab(self._tab_entities(), "Entities")
        root.addWidget(self.tabs, 1)

    # -------------------------------------------------------- Templates ----
    def _tab_templates(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(10)
        row = QHBoxLayout()
        row.addWidget(make_button("Mine templates", "Primary", self._mine))
        row.addWidget(QLabel("Rare threshold:"))
        self.rare_thr = QDoubleSpinBox()
        self.rare_thr.setRange(0.00001, 0.2)
        self.rare_thr.setDecimals(5)
        self.rare_thr.setSingleStep(0.0005)
        self.rare_thr.setValue(0.001)
        row.addWidget(self.rare_thr)
        self.only_rare = make_checkbox("Rare only", False,
                                       lambda _: self._show_templates())
        row.addWidget(self.only_rare)
        row.addWidget(make_button("Add template column", "Ghost",
                                  self._apply_templates))
        row.addStretch(1)
        lay.addLayout(row)
        info = QLabel("The variable parts of each message (<NUM>, <IP>, <UUID>, "
                      "<PATH>, <STR>) are masked and identical patterns are grouped.")
        info.setObjectName("Hint")
        info.setWordWrap(True)
        lay.addWidget(info)
        self.tpl_table = FrameTable(editable=False)
        self.tpl_table.clicked.connect(self._on_template_click)
        lay.addWidget(self.tpl_table, 2)
        self.tpl_examples = QPlainTextEdit()
        self.tpl_examples.setReadOnly(True)
        self.tpl_examples.setObjectName("Mono")
        self.tpl_examples.setMaximumHeight(150)
        self.tpl_examples.setPlaceholderText("Click a template row — examples appear here")
        lay.addWidget(self.tpl_examples, 1)
        return w

    def _mine(self) -> None:
        col = self.text_col.value()
        if not col or col not in self.df.columns:
            self.notify("Choose a text column", "warn")
            return
        series = self.df[col]
        run_async(logparse.mine_templates, series,
                  on_done=self._on_templates,
                  on_error=lambda m: self.notify(m.splitlines()[0], "error"))

    def _on_templates(self, payload) -> None:
        tids, table = payload
        self._tids = tids
        self._templates = table
        self.tiles["templates"].set_value(f"{len(table):,}")
        rare = logparse.rare_templates(table, self.rare_thr.value())
        self.tiles["rare"].set_value(
            f"{len(rare):,}",
            accent=PALETTE["warning"] if len(rare) else PALETTE["success"])
        self._show_templates()
        self.notify(f"{len(table):,} templates found", "success")

    def _show_templates(self) -> None:
        if self._templates is None:
            return
        table = self._templates
        if self.only_rare.isChecked():
            table = logparse.rare_templates(table, self.rare_thr.value())
        show = table.copy()
        show["ratio"] = (show["ratio"] * 100).round(3)
        show = show.rename(columns={"template_id": "id", "count": "count",
                                    "ratio": "share %", "tokens": "tokens"})
        self.tpl_table.set_df(show.head(5000))

    def _on_template_click(self, index) -> None:
        if self._templates is None or self._tids is None:
            return
        try:
            row = self.tpl_table.model_.df.iloc[index.row()]
            tid = int(row["id"])
        except Exception:
            return
        col = self.text_col.value()
        mask = (self._tids == tid).to_numpy()
        examples = self.df.loc[mask, col].astype(str).head(12)
        self.tpl_examples.setPlainText(
            f"# template {tid} — {int(row['count']):,} occurrences\n\n"
            + "\n".join(f"{i + 1:2d}. {e[:400]}" for i, e in enumerate(examples)))

    def _apply_templates(self) -> None:
        if self._tids is None:
            self.notify("Mine the templates first", "warn")
            return
        df = self.df.copy()
        if len(self._tids) != len(df):
            self.notify("The data changed — mine the templates again", "warn")
            return
        df["template_id"] = self._tids.to_numpy()
        if self._templates is not None:
            mapping = dict(zip(self._templates["template_id"], self._templates["template"]))
            df["template"] = df["template_id"].map(mapping)
        self.store.commit(df, "Template columns added")

    # ------------------------------------------------------------ Bursts ---
    def _tab_burst(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(10)
        row = QHBoxLayout()
        row.addWidget(QLabel("Window:"))
        self.burst_freq = QComboBox()
        self.burst_freq.addItems(["10s", "1min", "5min", "15min", "1h", "1D"])
        self.burst_freq.setCurrentText("1min")
        row.addWidget(self.burst_freq)
        row.addWidget(QLabel("z threshold:"))
        self.burst_z = QDoubleSpinBox()
        self.burst_z.setRange(1.0, 12.0)
        self.burst_z.setValue(3.0)
        row.addWidget(self.burst_z)
        row.addWidget(make_button("Find bursts", "Primary", self._run_burst))
        row.addWidget(make_button("Level dynamics", "Ghost", self._level_timeline))
        row.addStretch(1)
        lay.addLayout(row)
        self.burst_canvas = ChartCanvas()
        lay.addWidget(self.burst_canvas, 2)
        self.burst_table = FrameTable(editable=False)
        self.burst_table.setMaximumHeight(190)
        lay.addWidget(self.burst_table, 1)
        return w

    def _run_burst(self) -> None:
        tcol = self.time_col.value()
        if not tcol:
            self.notify("Choose a time column", "warn")
            return
        freq = self.burst_freq.currentText()
        z = self.burst_z.value()
        df = self.df

        def work():
            return logparse.burst_detect(df[tcol], freq=freq, z=z)

        run_async(work, on_done=self._on_burst,
                  on_error=lambda m: self.notify(m.splitlines()[0], "error"))

    def _on_burst(self, out: pd.DataFrame) -> None:
        if out.empty:
            self.notify("No usable time data was found", "warn")
            return
        n = int(out["is_burst"].sum())
        self.tiles["bursts"].set_value(
            f"{n:,}", accent=PALETTE["danger"] if n else PALETTE["success"])
        self.burst_table.set_df(
            out[out["is_burst"]].sort_values("count", ascending=False).head(500))

        from matplotlib.figure import Figure

        fig = Figure(figsize=(10, 5), dpi=110)
        fig.patch.set_facecolor(PALETTE["surface"])
        ax = fig.add_subplot(111)
        ax.set_facecolor(PALETTE["surface"])
        ax.plot(out["bucket"], out["count"], color=PALETTE["accent"], linewidth=1.4)
        ax.fill_between(out["bucket"], out["count"], alpha=0.2, color=PALETTE["accent"])
        burst = out[out["is_burst"]]
        if not burst.empty:
            ax.scatter(burst["bucket"], burst["count"], color=PALETTE["danger"],
                       s=44, zorder=5, label=f"burst ({len(burst)})")
            ax.legend(frameon=True)
        ax.set_title(f"Event density · window {self.burst_freq.currentText()}")
        ax.set_ylabel("event count")
        ax.grid(alpha=0.4, color=PALETTE["border"])
        ax.tick_params(colors=PALETTE["muted"])
        for lbl in ax.get_xticklabels():
            lbl.set_rotation(30)
            lbl.set_ha("right")
        fig.tight_layout()
        self.burst_canvas.set_figure(fig)

    def _level_timeline(self) -> None:
        tcol, lcol = self.time_col.value(), self.level_col.value()
        if not tcol or not lcol:
            self.notify("Choose both the time and the level column", "warn")
            return
        try:
            fig = charting.build_chart(self.df, "timeseries", x=tcol, hue=lcol,
                                       figsize=(10, 5.4),
                                       freq=self.burst_freq.currentText())
            self.burst_canvas.set_figure(fig)
        except Exception as exc:
            self.burst_canvas.show_message(str(exc))

    # ------------------------------------------------------ Text clusters --
    def _tab_cluster(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(10)
        row = QHBoxLayout()
        row.addWidget(QLabel("Cluster count:"))
        self.tc_k = QSpinBox()
        self.tc_k.setRange(2, 40)
        self.tc_k.setValue(6)
        row.addWidget(self.tc_k)
        row.addWidget(make_button("Cluster the messages", "Primary", self._run_tc))
        row.addWidget(make_button("Add cluster column", "Ghost", self._apply_tc))
        row.addStretch(1)
        lay.addLayout(row)
        self.tc_canvas = ChartCanvas()
        lay.addWidget(self.tc_canvas, 2)
        self.tc_text = QPlainTextEdit()
        self.tc_text.setReadOnly(True)
        self.tc_text.setObjectName("Mono")
        self.tc_text.setMinimumHeight(180)
        lay.addWidget(self.tc_text, 1)
        return w

    def _run_tc(self) -> None:
        col = self.text_col.value()
        if not col:
            self.notify("Choose a text column", "warn")
            return
        run_async(ml.text_cluster, self.df[col], k=self.tc_k.value(),
                  on_done=self._on_tc,
                  on_error=lambda m: self.notify(m.splitlines()[0], "error"))

    def _on_tc(self, res: ml.TextClusterResult) -> None:
        self._tc = res
        if res.coords is not None:
            self.tc_canvas.set_figure(charting.cluster_figure(
                res.coords, res.labels, title=f"Message clusters (k={res.k})"))
        lines = []
        for i in range(res.k):
            size = int(res.sizes.get(i, 0))
            lines.append(f"━━ Cluster {i} · {size:,} messages ━━")
            lines.append("  key terms: " + ", ".join(res.terms.get(i, [])))
            for ex in res.examples.get(i, [])[:3]:
                lines.append(f"    · {ex}")
            lines.append("")
        self.tc_text.setPlainText("\n".join(lines))

    def _apply_tc(self) -> None:
        res = getattr(self, "_tc", None)
        if res is None:
            self.notify("Run the clustering first", "warn")
            return
        df = self.df.copy()
        if len(res.labels) != len(df):
            self.notify("The clustering ran on a sample and cannot be applied to "
                        "the whole table", "warn")
            return
        df["text_cluster"] = res.labels
        self.store.commit(df, f"Text cluster (k={res.k})")

    # ---------------------------------------------------------- Entities ---
    def _tab_entities(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(10)
        row = QHBoxLayout()
        row.addWidget(make_button("Extract entities", "Primary", self._run_entities))
        row.addWidget(QLabel("(IP, IPv6, MAC, UUID, email, URL)"))
        row.addWidget(make_button("Top values", "Ghost", self._top_entities))
        row.addStretch(1)
        lay.addLayout(row)
        hint = QLabel("Extracted entities are written into new columns prefixed with "
                      "'e_' and are immediately usable in the table.")
        hint.setObjectName("Hint")
        hint.setWordWrap(True)
        lay.addWidget(hint)
        self.ent_table = FrameTable(editable=False)
        lay.addWidget(self.ent_table, 1)
        return w

    def _run_entities(self) -> None:
        col = self.text_col.value()
        if not col:
            self.notify("Choose a text column", "warn")
            return
        try:
            out = logparse.enrich(self.df, text_col=col)
        except Exception as exc:
            self.notify(f"Error: {exc}", "error")
            return
        new_cols = [c for c in out.columns if c.startswith("e_")]
        if not new_cols:
            self.notify("No entities were found", "warn")
            return
        self.store.commit(out, f"Entity columns: {', '.join(new_cols)}")
        self.ent_table.set_df(out[[col] + new_cols].head(2000))

    def _top_entities(self) -> None:
        df = self.df
        ent_cols = [c for c in df.columns if c.startswith("e_")]
        if not ent_cols:
            self.notify("Extract the entities first", "warn")
            return
        rows = []
        for c in ent_cols:
            vc = df[c].dropna().value_counts().head(20)
            for val, cnt in vc.items():
                rows.append({"kind": c[2:], "value": val, "count": int(cnt),
                             "share %": round(100 * cnt / max(1, df[c].notna().sum()), 2)})
        self.ent_table.set_df(pd.DataFrame(rows))

    # ------------------------------------------------------------ shared ---
    def refresh(self) -> None:
        df = self.df
        for combo in (self.text_col, self.time_col, self.level_col):
            combo.populate(df)
        if df.empty:
            return

        # Smart defaults: the text column must be a message, not ts/level
        candidates = ("message", "msg", "text", "template", "_raw")
        if self.text_col.value() not in candidates:
            for cand in candidates:
                i = self.text_col.findText(cand)
                if i >= 0:
                    self.text_col.setCurrentIndex(i)
                    break
        if not self.time_col.value():
            dt_cols = prof_mod.datetime_columns(df)
            if dt_cols:
                i = self.time_col.findText(dt_cols[0])
                if i >= 0:
                    self.time_col.setCurrentIndex(i)
        if not self.level_col.value():
            for cand in ("level", "severity", "state", "status"):
                i = self.level_col.findText(cand)
                if i >= 0:
                    self.level_col.setCurrentIndex(i)
                    break

        self.tiles["lines"].set_value(f"{len(df):,}")
        lcol = self.level_col.value() or ("level" if "level" in df.columns else None)
        if lcol and lcol in df.columns:
            s = df[lcol].astype(str).str.upper()
            err = s.isin(["ERROR", "CRITICAL", "FATAL", "ALERT"]).mean() * 100
            self.tiles["errors"].set_value(
                f"{err:.2f}%",
                accent=PALETTE["danger"] if err > 5 else
                (PALETTE["warning"] if err > 1 else PALETTE["success"]))
        else:
            self.tiles["errors"].set_value("—")
