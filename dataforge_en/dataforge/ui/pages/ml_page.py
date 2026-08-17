"""ML Studio — AutoML, clustering, anomalies, dimensionality reduction, forecasting."""
from __future__ import annotations

import numpy as np
import pandas as pd
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QComboBox, QDoubleSpinBox, QFileDialog, QHBoxLayout,
                               QLabel, QProgressBar, QSpinBox, QSplitter, QTabWidget,
                               QVBoxLayout, QWidget)

from ...config import MODELS_DIR, PALETTE
from ...core import charting, ml
from ...core import profile as prof_mod
from ..tasks import run_async
from ..widgets import (Card, ChartCanvas, ColumnCombo, FrameTable, MultiColumnSelect,
                       PageHeader, StatTile, make_button, make_checkbox)
from .base import BasePage


class MLPage(BasePage):
    title = "ML Studio"
    subtitle = ("Compare models automatically, find clusters, detect anomalies and "
                "forecast the future — all on your own data.")

    def __init__(self, store, parent=None) -> None:
        super().__init__(store, parent)
        self.result: ml.MLResult | None = None
        self._cluster: ml.ClusterResult | None = None
        self._anomaly: ml.AnomalyResult | None = None
        self._bundle = None
        self._build()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 16)
        root.setSpacing(12)
        root.addWidget(PageHeader(self.title, self.subtitle))
        self.tabs = QTabWidget()
        self.tabs.addTab(self._tab_automl(), "AutoML")
        self.tabs.addTab(self._tab_cluster(), "Clustering")
        self.tabs.addTab(self._tab_anomaly(), "Anomalies")
        self.tabs.addTab(self._tab_reduce(), "Dimensionality")
        self.tabs.addTab(self._tab_forecast(), "Forecast")
        self.tabs.addTab(self._tab_model(), "Saved model")
        root.addWidget(self.tabs, 1)

    # =====================================================  AutoML  =========
    def _tab_automl(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(10)

        split = QSplitter(Qt.Orientation.Horizontal)
        split.setChildrenCollapsible(False)

        # ---- settings
        left = QWidget()
        left.setMaximumWidth(360)
        lv = QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 8, 0)
        lv.setSpacing(10)

        cfg = Card("Settings")
        row = QHBoxLayout()
        row.addWidget(QLabel("Target:"))
        self.target = ColumnCombo("any")
        self.target.currentTextChanged.connect(self._on_target_changed)
        row.addWidget(self.target, 1)
        cfg.add_layout(row)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Task:"))
        self.task_combo = QComboBox()
        self.task_combo.addItems(["auto", ml.CLASSIFICATION, ml.REGRESSION])
        row2.addWidget(self.task_combo, 1)
        cfg.add_layout(row2)

        cfg.add(QLabel("Features:"))
        self.features = MultiColumnSelect(kind="any", height=170)
        cfg.add(self.features)

        row3 = QHBoxLayout()
        row3.addWidget(QLabel("Test size:"))
        self.test_size = QDoubleSpinBox()
        self.test_size.setRange(0.05, 0.5)
        self.test_size.setSingleStep(0.05)
        self.test_size.setValue(0.2)
        row3.addWidget(self.test_size)
        row3.addWidget(QLabel("CV:"))
        self.cv = QSpinBox()
        self.cv.setRange(0, 10)
        self.cv.setValue(3)
        row3.addWidget(self.cv)
        cfg.add_layout(row3)

        row4 = QHBoxLayout()
        self.fast_cb = make_checkbox("Fast mode", True)
        self.fast_cb.setToolTip("Skips the slow models (SVM, MLP)")
        self.text_cb = make_checkbox("Text features (TF-IDF)", True)
        row4.addWidget(self.fast_cb)
        row4.addWidget(self.text_cb)
        cfg.add_layout(row4)

        row5 = QHBoxLayout()
        row5.addWidget(QLabel("Max rows:"))
        self.max_rows = QSpinBox()
        self.max_rows.setRange(200, 5_000_000)
        self.max_rows.setSingleStep(5000)
        self.max_rows.setValue(50_000)
        row5.addWidget(self.max_rows, 1)
        cfg.add_layout(row5)

        self.run_btn = make_button("Train models", "Primary", self._run_automl)
        cfg.add(self.run_btn)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setVisible(False)
        cfg.add(self.progress)
        self.ml_status = QLabel("")
        self.ml_status.setObjectName("Hint")
        self.ml_status.setWordWrap(True)
        cfg.add(self.ml_status)
        lv.addWidget(cfg)

        out = Card("Use the result")
        orow = QHBoxLayout()
        orow.addWidget(make_button("Save model", "Ghost", self._save_model))
        orow.addWidget(make_button("Add predictions", "Ghost", self._apply_pred))
        out.add_layout(orow)
        lv.addWidget(out)
        lv.addStretch(1)
        split.addWidget(left)

        # ---- results
        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setContentsMargins(0, 0, 0, 0)
        rv.setSpacing(10)

        tiles = QHBoxLayout()
        self.ml_tiles: list[StatTile] = []
        for _ in range(4):
            t = StatTile("—", "—")
            self.ml_tiles.append(t)
            tiles.addWidget(t)
        rv.addLayout(tiles)

        self.result_tabs = QTabWidget()
        self.board_table = FrameTable(editable=False)
        self.result_tabs.addTab(self.board_table, "Leaderboard")
        self.eval_canvas = ChartCanvas()
        self.result_tabs.addTab(self.eval_canvas, "Evaluation chart")
        self.imp_canvas = ChartCanvas()
        self.result_tabs.addTab(self.imp_canvas, "Feature importance")
        self.imp_table = FrameTable(editable=False)
        self.result_tabs.addTab(self.imp_table, "Importance table")
        rv.addWidget(self.result_tabs, 1)
        split.addWidget(right)
        split.setSizes([340, 800])
        lay.addWidget(split, 1)
        return w

    def _on_target_changed(self, name: str) -> None:
        df = self.df
        if not name or name not in df.columns or df.empty:
            return
        try:
            task = ml.detect_task(df[name])
            uniq = df[name].nunique()
            self.ml_status.setText(
                f"'{name}' → {task} · {uniq:,} distinct values")
        except Exception:
            pass
        self.features.set_values([c for c in df.columns if c != name])

    def _run_automl(self) -> None:
        if not self.has_data():
            self.notify("Load some data first", "warn")
            return
        target = self.target.value()
        if not target:
            self.notify("Choose a target column", "warn")
            return
        feats = [c for c in self.features.values() if c != target]
        if not feats:
            self.notify("Select at least one feature", "warn")
            return
        task = self.task_combo.currentText()
        self.run_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setValue(0)
        self.ml_status.setText("Starting…")
        run_async(
            ml.run_automl, self.df, target,
            features=feats,
            task=None if task == "auto" else task,
            test_size=self.test_size.value(),
            cv=self.cv.value(),
            fast=self.fast_cb.isChecked(),
            use_text=self.text_cb.isChecked(),
            max_rows=self.max_rows.value(),
            with_progress=True,
            on_progress=self._on_progress,
            on_done=self._on_automl_done,
            on_error=self._on_automl_error,
        )

    def _on_progress(self, msg: str, pct: int) -> None:
        self.ml_status.setText(msg)
        self.progress.setValue(max(0, min(100, pct)))

    def _on_automl_error(self, msg: str) -> None:
        self.run_btn.setEnabled(True)
        self.progress.setVisible(False)
        first = msg.splitlines()[0]
        self.ml_status.setText(f"Error: {first}")
        self.notify(f"AutoML error: {first}", "error")

    def _on_automl_done(self, res: ml.MLResult) -> None:
        self.result = res
        self.run_btn.setEnabled(True)
        self.progress.setVisible(False)
        note = (" · " + "; ".join(res.warnings)) if res.warnings else ""
        self.ml_status.setText(
            f"✓ {res.best_name} · train {res.n_train:,} / test {res.n_test:,}{note}")
        self.board_table.set_df(res.leaderboard)

        items = list(res.metrics.items())[:4]
        for tile, (k, v) in zip(self.ml_tiles, items):
            good = (v >= 0.8 if res.task == ml.CLASSIFICATION else v >= 0.7) \
                if k in ("F1 (macro)", "accuracy", "R²") else None
            accent = None
            if good is True:
                accent = PALETTE["success"]
            elif good is False:
                accent = PALETTE["warning"]
            tile.key_label.setText(k.upper())
            tile.set_value(f"{v:.4f}" if isinstance(v, float) else str(v),
                           res.best_name, accent)

        try:
            if res.task == ml.CLASSIFICATION and res.confusion is not None:
                self.eval_canvas.set_figure(charting.confusion_figure(res.confusion))
                self.result_tabs.setTabText(1, "Confusion matrix")
            else:
                self.eval_canvas.set_figure(
                    charting.residual_figure(res.y_true, res.y_pred))
                self.result_tabs.setTabText(1, "Residual analysis")
        except Exception as exc:
            self.eval_canvas.show_message(str(exc))

        if res.importance is not None and not res.importance.empty:
            self.imp_canvas.set_figure(charting.importance_figure(res.importance))
            self.imp_table.set_df(res.importance)
        else:
            self.imp_canvas.show_message("Importance could not be computed")

        # ROC in its own tab
        if res.task == ml.CLASSIFICATION and res.y_proba is not None:
            curves = ml.roc_curves(res.y_true, res.y_proba, res.classes)
            if curves:
                if not hasattr(self, "roc_canvas"):
                    self.roc_canvas = ChartCanvas()
                    self.result_tabs.addTab(self.roc_canvas, "ROC")
                self.roc_canvas.set_figure(charting.roc_figure(curves))
        self.notify(f"Model ready: {res.best_name}", "success")

    def _save_model(self) -> None:
        if self.result is None:
            self.notify("Train a model first", "warn")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save the model",
            str(MODELS_DIR / f"{self.result.target}_model.joblib"),
            "Joblib (*.joblib)")
        if path:
            ml.save_model(self.result, path)
            self.notify(f"Model saved: {path}", "success")

    def _apply_pred(self) -> None:
        if self.result is None:
            self.notify("Train a model first", "warn")
            return
        try:
            bundle = {"model": self.result.best_model, "task": self.result.task}
            out = ml.predict_with(bundle, self.df)
        except Exception as exc:
            self.notify(f"Prediction error: {exc}", "error")
            return
        self.store.commit(out, f"Prediction column added ({self.result.best_name})")

    # ==================================================  Clustering  ========
    def _tab_cluster(self) -> QWidget:
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(12)

        left = QWidget()
        left.setMaximumWidth(330)
        lv = QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 0, 0)
        lv.setSpacing(10)
        cfg = Card("Settings")
        cfg.add(QLabel("Columns (numeric):"))
        self.cl_cols = MultiColumnSelect(kind="num", height=170)
        cfg.add(self.cl_cols)
        row = QHBoxLayout()
        row.addWidget(QLabel("Algorithm:"))
        self.cl_algo = QComboBox()
        self.cl_algo.addItems(["KMeans", "Agglomerative", "GaussianMixture", "DBSCAN"])
        row.addWidget(self.cl_algo, 1)
        cfg.add_layout(row)
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("k (0 = auto):"))
        self.cl_k = QSpinBox()
        self.cl_k.setRange(0, 50)
        self.cl_k.setValue(0)
        row2.addWidget(self.cl_k)
        cfg.add_layout(row2)
        row3 = QHBoxLayout()
        row3.addWidget(QLabel("eps:"))
        self.cl_eps = QDoubleSpinBox()
        self.cl_eps.setRange(0.05, 20.0)
        self.cl_eps.setValue(0.6)
        self.cl_eps.setSingleStep(0.1)
        row3.addWidget(self.cl_eps)
        row3.addWidget(QLabel("min_samples:"))
        self.cl_min = QSpinBox()
        self.cl_min.setRange(2, 200)
        self.cl_min.setValue(8)
        row3.addWidget(self.cl_min)
        cfg.add_layout(row3)
        cfg.add(make_button("Run clustering", "Primary", self._run_cluster))
        row4 = QHBoxLayout()
        row4.addWidget(make_button("Optimal k chart", "Ghost", self._draw_elbow))
        row4.addWidget(make_button("Add cluster column", "Ghost", self._apply_cluster))
        cfg.add_layout(row4)
        self.cl_status = QLabel("")
        self.cl_status.setObjectName("Hint")
        self.cl_status.setWordWrap(True)
        cfg.add(self.cl_status)
        lv.addWidget(cfg)
        lv.addStretch(1)
        lay.addWidget(left)

        right = QTabWidget()
        self.cl_canvas = ChartCanvas()
        right.addTab(self.cl_canvas, "Cluster map")
        self.cl_table = FrameTable(editable=False)
        right.addTab(self.cl_table, "Cluster profile")
        lay.addWidget(right, 1)
        return w

    def _run_cluster(self) -> None:
        cols = self.cl_cols.values()
        if len(cols) < 1:
            self.notify("Select at least one numeric column", "warn")
            return
        self.cl_status.setText("Computing…")
        run_async(ml.cluster, self.df, cols,
                  algo=self.cl_algo.currentText(),
                  k=None if self.cl_k.value() == 0 else self.cl_k.value(),
                  eps=self.cl_eps.value(), min_samples=self.cl_min.value(),
                  on_done=self._on_cluster,
                  on_error=lambda m: self._simple_error(self.cl_status, m))

    def _on_cluster(self, res: ml.ClusterResult) -> None:
        self._cluster = res
        sil = "—" if np.isnan(res.silhouette) else f"{res.silhouette:.3f}"
        self.cl_status.setText(
            f"✓ {res.algo}: {res.k} clusters · silhouette {sil}"
            + (f" · noise {res.noise:,}" if res.noise else ""))
        if res.coords is not None:
            self.cl_canvas.set_figure(charting.cluster_figure(
                res.coords, res.labels,
                title=f"{res.algo} — {res.k} clusters (PCA projection)"))
        if res.profile is not None:
            self.cl_table.set_df(res.profile)

    def _draw_elbow(self) -> None:
        cols = self.cl_cols.values()
        if len(cols) < 1:
            self.notify("Select the columns first", "warn")
            return

        def work():
            from sklearn.impute import SimpleImputer
            from sklearn.preprocessing import StandardScaler

            num = self.df[cols].select_dtypes(include=[np.number])
            X = StandardScaler().fit_transform(
                SimpleImputer(strategy="median").fit_transform(num))
            return ml.auto_k(X, 2, 10)[1]

        run_async(work,
                  on_done=lambda scores: self.cl_canvas.set_figure(
                      charting.elbow_figure(scores)),
                  on_error=lambda m: self._simple_error(self.cl_status, m))

    def _apply_cluster(self) -> None:
        if self._cluster is None:
            self.notify("Run the clustering first", "warn")
            return
        df = self.df.copy()
        labels = self._cluster.labels
        if len(labels) != len(df):
            self.notify("The clustering ran on a sample — raise the row limit to "
                        "apply it to the whole table", "warn")
            return
        df["cluster"] = labels
        self.store.commit(df, f"Cluster column ({self._cluster.algo}, k={self._cluster.k})")

    # ====================================================  Anomalies  =======
    def _tab_anomaly(self) -> QWidget:
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(12)

        left = QWidget()
        left.setMaximumWidth(330)
        lv = QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 0, 0)
        lv.setSpacing(10)
        cfg = Card("Settings")
        cfg.add(QLabel("Columns (numeric):"))
        self.an_cols = MultiColumnSelect(kind="num", height=160)
        cfg.add(self.an_cols)
        row = QHBoxLayout()
        row.addWidget(QLabel("Method:"))
        self.an_method = QComboBox()
        self.an_method.addItems(ml.ANOMALY_METHODS)
        row.addWidget(self.an_method, 1)
        cfg.add_layout(row)
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Expected share:"))
        self.an_contam = QDoubleSpinBox()
        self.an_contam.setRange(0.001, 0.4)
        self.an_contam.setSingleStep(0.005)
        self.an_contam.setDecimals(3)
        self.an_contam.setValue(0.02)
        row2.addWidget(self.an_contam)
        cfg.add_layout(row2)
        row3 = QHBoxLayout()
        row3.addWidget(QLabel("z threshold:"))
        self.an_z = QDoubleSpinBox()
        self.an_z.setRange(1.0, 10.0)
        self.an_z.setValue(3.0)
        self.an_z.setSingleStep(0.5)
        row3.addWidget(self.an_z)
        cfg.add_layout(row3)
        row4 = QHBoxLayout()
        row4.addWidget(QLabel("Plot column:"))
        self.an_plot_col = ColumnCombo("num", allow_empty=True)
        row4.addWidget(self.an_plot_col, 1)
        cfg.add_layout(row4)
        cfg.add(make_button("Find anomalies", "Primary", self._run_anomaly))
        cfg.add(make_button("Add flag column", "Ghost", self._apply_anomaly))
        self.an_status = QLabel("")
        self.an_status.setObjectName("Hint")
        self.an_status.setWordWrap(True)
        cfg.add(self.an_status)
        lv.addWidget(cfg)
        lv.addStretch(1)
        lay.addWidget(left)

        right = QTabWidget()
        self.an_canvas = ChartCanvas()
        right.addTab(self.an_canvas, "Chart")
        self.an_table = FrameTable(editable=False)
        right.addTab(self.an_table, "Anomalous rows")
        lay.addWidget(right, 1)
        return w

    def _run_anomaly(self) -> None:
        cols = self.an_cols.values()
        if not cols:
            self.notify("Select the columns first", "warn")
            return
        self.an_status.setText("Searching…")
        run_async(ml.detect_anomalies, self.df, cols,
                  method=self.an_method.currentText(),
                  contamination=self.an_contam.value(),
                  z_threshold=self.an_z.value(),
                  on_done=self._on_anomaly,
                  on_error=lambda m: self._simple_error(self.an_status, m))

    def _on_anomaly(self, res: ml.AnomalyResult) -> None:
        self._anomaly = res
        pct = 100 * res.n_anomalies / max(1, len(res.index))
        self.an_status.setText(
            f"✓ {res.method}: {res.n_anomalies:,} anomalies ({pct:.2f}%)")
        df = self.df
        col = self.an_plot_col.value() or (self.an_cols.values() or [None])[0]
        try:
            if col:
                sub = df.loc[res.index, col]
                dt_cols = prof_mod.datetime_columns(df)
                xs = df.loc[res.index, dt_cols[0]] if dt_cols else None
                self.an_canvas.set_figure(
                    charting.anomaly_figure(sub.reset_index(drop=True), res.is_anomaly,
                                            res.scores,
                                            xs.reset_index(drop=True) if xs is not None
                                            else None))
        except Exception as exc:
            self.an_canvas.show_message(str(exc))
        try:
            flagged = df.loc[res.index[res.is_anomaly]].copy()
            flagged.insert(0, "anomaly_score", np.round(res.scores[res.is_anomaly], 4))
            self.an_table.set_df(flagged.head(3000))
        except Exception:
            pass

    def _apply_anomaly(self) -> None:
        if self._anomaly is None:
            self.notify("Find the anomalies first", "warn")
            return
        df = self.df.copy()
        res = self._anomaly
        df["anomaly"] = False
        df["anomaly_score"] = np.nan
        df.loc[res.index, "anomaly"] = res.is_anomaly
        df.loc[res.index, "anomaly_score"] = res.scores
        self.store.commit(df, f"Anomaly flag ({res.method})")

    # =================================================  Dimensionality  =====
    def _tab_reduce(self) -> QWidget:
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(12)
        left = QWidget()
        left.setMaximumWidth(330)
        lv = QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 0, 0)
        cfg = Card("Settings")
        cfg.add(QLabel("Columns:"))
        self.rd_cols = MultiColumnSelect(kind="num", height=170)
        cfg.add(self.rd_cols)
        row = QHBoxLayout()
        row.addWidget(QLabel("Method:"))
        self.rd_method = QComboBox()
        self.rd_method.addItems(["PCA", "t-SNE", "SVD"])
        row.addWidget(self.rd_method, 1)
        cfg.add_layout(row)
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Colour column:"))
        self.rd_hue = ColumnCombo("any", allow_empty=True)
        row2.addWidget(self.rd_hue, 1)
        cfg.add_layout(row2)
        cfg.add(make_button("Compute", "Primary", self._run_reduce))
        self.rd_status = QLabel("")
        self.rd_status.setObjectName("Hint")
        self.rd_status.setWordWrap(True)
        cfg.add(self.rd_status)
        lv.addWidget(cfg)
        lv.addStretch(1)
        lay.addWidget(left)
        self.rd_canvas = ChartCanvas()
        lay.addWidget(self.rd_canvas, 1)
        return w

    def _run_reduce(self) -> None:
        cols = self.rd_cols.values()
        if len(cols) < 2:
            self.notify("Select at least 2 numeric columns", "warn")
            return
        self.rd_status.setText("Computing… (t-SNE can be slow)")
        run_async(ml.reduce_dim, self.df, cols, method=self.rd_method.currentText(),
                  on_done=self._on_reduce,
                  on_error=lambda m: self._simple_error(self.rd_status, m))

    def _on_reduce(self, payload) -> None:
        coords, info = payload
        hue = self.rd_hue.value()
        labels = np.zeros(len(coords), dtype=int)
        title = f"{info['method']} projection"
        if hue and hue in self.df.columns:
            try:
                s = self.df.loc[info["index"], hue]
                labels = pd.factorize(s.astype(str))[0]
                title += f" · colour: {hue}"
            except Exception:
                pass
        self.rd_canvas.set_figure(charting.cluster_figure(coords, labels, title=title))
        exp = info.get("explained")
        if exp:
            self.rd_status.setText(
                "✓ Explained variance: "
                + ", ".join(f"PC{i + 1}={v:.1%}" for i, v in enumerate(exp))
                + f" · total {sum(exp):.1%}")
        else:
            self.rd_status.setText(f"✓ {info['method']} ready ({info['n']:,} points)")

    # =====================================================  Forecast  =======
    def _tab_forecast(self) -> QWidget:
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(12)
        left = QWidget()
        left.setMaximumWidth(330)
        lv = QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 0, 0)
        cfg = Card("Settings")
        row = QHBoxLayout()
        row.addWidget(QLabel("Time column:"))
        self.fc_time = ColumnCombo("dt")
        row.addWidget(self.fc_time, 1)
        cfg.add_layout(row)
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Value:"))
        self.fc_value = ColumnCombo("num", allow_empty=True)
        row2.addWidget(self.fc_value, 1)
        cfg.add_layout(row2)
        row3 = QHBoxLayout()
        row3.addWidget(QLabel("Frequency:"))
        self.fc_freq = QComboBox()
        self.fc_freq.addItems(["auto", "1min", "5min", "15min", "1h", "6h",
                               "1D", "1W", "1ME"])
        row3.addWidget(self.fc_freq, 1)
        cfg.add_layout(row3)
        row4 = QHBoxLayout()
        row4.addWidget(QLabel("Function:"))
        self.fc_agg = QComboBox()
        self.fc_agg.addItems(["count", "mean", "sum", "max", "min"])
        row4.addWidget(self.fc_agg, 1)
        cfg.add_layout(row4)
        row5 = QHBoxLayout()
        row5.addWidget(QLabel("Steps ahead:"))
        self.fc_periods = QSpinBox()
        self.fc_periods.setRange(1, 2000)
        self.fc_periods.setValue(24)
        row5.addWidget(self.fc_periods)
        row5.addWidget(QLabel("Season:"))
        self.fc_season = QSpinBox()
        self.fc_season.setRange(0, 400)
        self.fc_season.setValue(24)
        self.fc_season.setSpecialValueText("none")
        row5.addWidget(self.fc_season)
        cfg.add_layout(row5)
        cfg.add(make_button("Forecast", "Primary", self._run_forecast))
        cfg.add(make_button("Save result as a table", "Ghost", self._forecast_to_dataset))
        self.fc_status = QLabel("")
        self.fc_status.setObjectName("Hint")
        self.fc_status.setWordWrap(True)
        cfg.add(self.fc_status)
        lv.addWidget(cfg)
        lv.addStretch(1)
        lay.addWidget(left)
        self.fc_canvas = ChartCanvas()
        lay.addWidget(self.fc_canvas, 1)
        return w

    def _run_forecast(self) -> None:
        tcol = self.fc_time.value()
        if not tcol:
            self.notify("No time column was found", "warn")
            return
        value = self.fc_value.value()
        agg = self.fc_agg.currentText()
        freq = self.fc_freq.currentText()
        periods = self.fc_periods.value()
        season = self.fc_season.value() or None
        df = self.df

        def work():
            f = prof_mod.suggest_freq(df[tcol]) if freq == "auto" else freq
            ts = prof_mod.time_series(df, tcol, freq=f, value=value, agg=agg)
            series = pd.Series(ts.iloc[:, 1].to_numpy(),
                               index=pd.DatetimeIndex(ts.iloc[:, 0]))
            return series, ml.forecast(series, periods=periods,
                                       seasonal_periods=season), f

        run_async(work, on_done=self._on_forecast,
                  on_error=lambda m: self._simple_error(self.fc_status, m))

    def _on_forecast(self, payload) -> None:
        series, fc, freq = payload
        self._forecast_df = fc
        self.fc_canvas.set_figure(charting.forecast_figure(series, fc))
        self.fc_status.setText(
            f"✓ {len(fc)} steps forecast from {len(series):,} points ({freq})")

    def _forecast_to_dataset(self) -> None:
        fc = getattr(self, "_forecast_df", None)
        if fc is None:
            self.notify("Run the forecast first", "warn")
            return
        self.store.add(f"{self.store.active_name}_forecast", fc)

    # ===================================================  Saved model  ======
    def _tab_model(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(10)
        card = Card("Apply a saved model",
                    "run a previously trained model on new data")
        row = QHBoxLayout()
        row.addWidget(make_button("Choose a model file…", "Ghost", self._load_model))
        row.addWidget(make_button("Apply to the current table", "Primary", self._predict))
        row.addStretch(1)
        card.add_layout(row)
        self.model_info = QLabel("No model loaded")
        self.model_info.setObjectName("Mono")
        self.model_info.setWordWrap(True)
        card.add(self.model_info)
        lay.addWidget(card)
        self.pred_table = FrameTable(editable=False)
        lay.addWidget(self.pred_table, 1)
        return w

    def _load_model(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Model", str(MODELS_DIR),
                                              "Joblib (*.joblib);;All files (*.*)")
        if not path:
            return
        try:
            self._bundle = ml.load_model(path)
        except Exception as exc:
            self.notify(f"Could not load the model: {exc}", "error")
            return
        b = self._bundle
        metrics = " · ".join(f"{k}={v:.4f}" if isinstance(v, float) else f"{k}={v}"
                             for k, v in list(b.get("metrics", {}).items())[:4])
        self.model_info.setText(
            f"Model: {b.get('name')}\nTask: {b.get('task')}\n"
            f"Target: {b.get('target')}\nFeatures ({len(b.get('features', []))}): "
            f"{', '.join(b.get('features', [])[:15])}\nMetrics: {metrics}")
        self.notify("Model loaded", "success")

    def _predict(self) -> None:
        if self._bundle is None:
            self.notify("Choose a model file first", "warn")
            return
        if not self.has_data():
            self.notify("Load some data first", "warn")
            return
        try:
            out = ml.predict_with(self._bundle, self.df)
        except Exception as exc:
            self.notify(f"Prediction error: {exc}", "error")
            return
        self.pred_table.set_df(out.head(1000))
        self.store.commit(out, f"Saved-model prediction ({self._bundle.get('name')})")

    # ---------------------------------------------------------- shared -----
    def _simple_error(self, label: QLabel, msg: str) -> None:
        first = msg.splitlines()[0]
        label.setText(f"Error: {first}")
        self.notify(first, "error")

    def refresh(self) -> None:
        df = self.df
        self.target.populate(df)
        self.features.populate(df)
        for sel in (self.cl_cols, self.an_cols, self.rd_cols):
            sel.populate(df)
        for combo in (self.an_plot_col, self.rd_hue, self.fc_time, self.fc_value):
            combo.populate(df)
        if not df.empty and not self.features.values():
            target = self.target.value()
            self.features.set_values([c for c in df.columns if c != target])
