"""ML Studio — AutoML, klasterlash, anomaliya, o'lchov kamaytirish, bashorat."""
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
    subtitle = ("Bir necha modelni avtomatik taqqoslang, klaster toping, anomaliyalarni "
                "aniqlang va kelajakni bashorat qiling — hammasi ma'lumotingiz ustida.")

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
        self.tabs.addTab(self._tab_cluster(), "Klasterlash")
        self.tabs.addTab(self._tab_anomaly(), "Anomaliya")
        self.tabs.addTab(self._tab_reduce(), "O'lchov kamaytirish")
        self.tabs.addTab(self._tab_forecast(), "Bashorat")
        self.tabs.addTab(self._tab_model(), "Saqlangan model")
        root.addWidget(self.tabs, 1)

    # =====================================================  AutoML  =========
    def _tab_automl(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(10)

        split = QSplitter(Qt.Orientation.Horizontal)
        split.setChildrenCollapsible(False)

        # ---- sozlamalar
        left = QWidget()
        left.setMaximumWidth(360)
        lv = QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 8, 0)
        lv.setSpacing(10)

        cfg = Card("Sozlamalar")
        row = QHBoxLayout()
        row.addWidget(QLabel("Nishon (target):"))
        self.target = ColumnCombo("any")
        self.target.currentTextChanged.connect(self._on_target_changed)
        row.addWidget(self.target, 1)
        cfg.add_layout(row)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Vazifa:"))
        self.task_combo = QComboBox()
        self.task_combo.addItems(["avtomatik", ml.CLASSIFICATION, ml.REGRESSION])
        row2.addWidget(self.task_combo, 1)
        cfg.add_layout(row2)

        cfg.add(QLabel("Xususiyatlar:"))
        self.features = MultiColumnSelect(kind="any", height=170)
        cfg.add(self.features)

        row3 = QHBoxLayout()
        row3.addWidget(QLabel("Test ulushi:"))
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
        self.fast_cb = make_checkbox("Tezkor rejim", True)
        self.fast_cb.setToolTip("Sekin modellarni (SVM, MLP) tashlab ketadi")
        self.text_cb = make_checkbox("Matn xususiyatlari (TF-IDF)", True)
        row4.addWidget(self.fast_cb)
        row4.addWidget(self.text_cb)
        cfg.add_layout(row4)

        row5 = QHBoxLayout()
        row5.addWidget(QLabel("Maks. qator:"))
        self.max_rows = QSpinBox()
        self.max_rows.setRange(200, 5_000_000)
        self.max_rows.setSingleStep(5000)
        self.max_rows.setValue(50_000)
        row5.addWidget(self.max_rows, 1)
        cfg.add_layout(row5)

        self.run_btn = make_button("Modellarni o'qitish", "Primary", self._run_automl)
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

        out = Card("Natija bilan ishlash")
        orow = QHBoxLayout()
        orow.addWidget(make_button("Modelni saqlash", "Ghost", self._save_model))
        orow.addWidget(make_button("Bashoratni ustun qilish", "Ghost", self._apply_pred))
        out.add_layout(orow)
        lv.addWidget(out)
        lv.addStretch(1)
        split.addWidget(left)

        # ---- natijalar
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
        self.result_tabs.addTab(self.board_table, "Modellar reytingi")
        self.eval_canvas = ChartCanvas()
        self.result_tabs.addTab(self.eval_canvas, "Baholash grafigi")
        self.imp_canvas = ChartCanvas()
        self.result_tabs.addTab(self.imp_canvas, "Xususiyat muhimligi")
        self.imp_table = FrameTable(editable=False)
        self.result_tabs.addTab(self.imp_table, "Muhimlik jadvali")
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
                f"'{name}' → {task} · {uniq:,} unikal qiymat")
        except Exception:
            pass
        self.features.set_values([c for c in df.columns if c != name])

    def _run_automl(self) -> None:
        if not self.has_data():
            self.notify("Avval ma'lumot yuklang", "warn")
            return
        target = self.target.value()
        if not target:
            self.notify("Nishon ustunini tanlang", "warn")
            return
        feats = [c for c in self.features.values() if c != target]
        if not feats:
            self.notify("Kamida bitta xususiyat tanlang", "warn")
            return
        task = self.task_combo.currentText()
        self.run_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setValue(0)
        self.ml_status.setText("Boshlandi…")
        run_async(
            ml.run_automl, self.df, target,
            features=feats,
            task=None if task == "avtomatik" else task,
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
        self.ml_status.setText(f"Xato: {first}")
        self.notify(f"AutoML xatosi: {first}", "error")

    def _on_automl_done(self, res: ml.MLResult) -> None:
        self.result = res
        self.run_btn.setEnabled(True)
        self.progress.setVisible(False)
        note = (" · " + "; ".join(res.warnings)) if res.warnings else ""
        self.ml_status.setText(
            f"✓ {res.best_name} · trening {res.n_train:,} / test {res.n_test:,}{note}")
        self.board_table.set_df(res.leaderboard)

        items = list(res.metrics.items())[:4]
        for tile, (k, v) in zip(self.ml_tiles, items):
            good = (v >= 0.8 if res.task == ml.CLASSIFICATION else v >= 0.7) \
                if k in ("F1 (makro)", "aniqlik (accuracy)", "R²") else None
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
                self.result_tabs.setTabText(1, "Chalkashlik matritsasi")
            else:
                self.eval_canvas.set_figure(
                    charting.residual_figure(res.y_true, res.y_pred))
                self.result_tabs.setTabText(1, "Qoldiqlar tahlili")
        except Exception as exc:
            self.eval_canvas.show_message(str(exc))

        if res.importance is not None and not res.importance.empty:
            self.imp_canvas.set_figure(charting.importance_figure(res.importance))
            self.imp_table.set_df(res.importance)
        else:
            self.imp_canvas.show_message("Muhimlik hisoblanmadi")

        # ROC ni alohida tab sifatida
        if res.task == ml.CLASSIFICATION and res.y_proba is not None:
            curves = ml.roc_curves(res.y_true, res.y_proba, res.classes)
            if curves:
                if not hasattr(self, "roc_canvas"):
                    self.roc_canvas = ChartCanvas()
                    self.result_tabs.addTab(self.roc_canvas, "ROC")
                self.roc_canvas.set_figure(charting.roc_figure(curves))
        self.notify(f"Model tayyor: {res.best_name}", "success")

    def _save_model(self) -> None:
        if self.result is None:
            self.notify("Avval modelni o'qiting", "warn")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Modelni saqlash",
            str(MODELS_DIR / f"{self.result.target}_model.joblib"),
            "Joblib (*.joblib)")
        if path:
            ml.save_model(self.result, path)
            self.notify(f"Model saqlandi: {path}", "success")

    def _apply_pred(self) -> None:
        if self.result is None:
            self.notify("Avval modelni o'qiting", "warn")
            return
        try:
            bundle = {"model": self.result.best_model, "task": self.result.task}
            out = ml.predict_with(bundle, self.df)
        except Exception as exc:
            self.notify(f"Bashorat xatosi: {exc}", "error")
            return
        self.store.commit(out, f"Bashorat ustuni qo'shildi ({self.result.best_name})")

    # ==================================================  Klasterlash  =======
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
        cfg = Card("Sozlamalar")
        cfg.add(QLabel("Ustunlar (sonli):"))
        self.cl_cols = MultiColumnSelect(kind="num", height=170)
        cfg.add(self.cl_cols)
        row = QHBoxLayout()
        row.addWidget(QLabel("Algoritm:"))
        self.cl_algo = QComboBox()
        self.cl_algo.addItems(["KMeans", "Agglomerative", "GaussianMixture", "DBSCAN"])
        row.addWidget(self.cl_algo, 1)
        cfg.add_layout(row)
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("k (0 = avto):"))
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
        cfg.add(make_button("Klasterlash", "Primary", self._run_cluster))
        row4 = QHBoxLayout()
        row4.addWidget(make_button("Optimal k grafigi", "Ghost", self._draw_elbow))
        row4.addWidget(make_button("Klasterni ustun qilish", "Ghost", self._apply_cluster))
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
        right.addTab(self.cl_canvas, "Klaster xaritasi")
        self.cl_table = FrameTable(editable=False)
        right.addTab(self.cl_table, "Klaster profili")
        lay.addWidget(right, 1)
        return w

    def _run_cluster(self) -> None:
        cols = self.cl_cols.values()
        if len(cols) < 1:
            self.notify("Kamida bitta sonli ustun tanlang", "warn")
            return
        self.cl_status.setText("Hisoblanmoqda…")
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
            f"✓ {res.algo}: {res.k} klaster · siluet {sil}"
            + (f" · shovqin {res.noise:,}" if res.noise else ""))
        if res.coords is not None:
            self.cl_canvas.set_figure(charting.cluster_figure(
                res.coords, res.labels,
                title=f"{res.algo} — {res.k} klaster (PCA proyeksiyasi)"))
        if res.profile is not None:
            self.cl_table.set_df(res.profile)

    def _draw_elbow(self) -> None:
        cols = self.cl_cols.values()
        if len(cols) < 1:
            self.notify("Ustunlarni tanlang", "warn")
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
            self.notify("Avval klasterlashni bajaring", "warn")
            return
        df = self.df.copy()
        labels = self._cluster.labels
        if len(labels) != len(df):
            self.notify("Klaster natijasi namunada hisoblangan — to'liq ma'lumotga "
                        "qo'llash uchun 'Maks. qator' chegarasini oshiring", "warn")
            return
        df["klaster"] = labels
        self.store.commit(df, f"Klaster ustuni ({self._cluster.algo}, k={self._cluster.k})")

    # ====================================================  Anomaliya  =======
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
        cfg = Card("Sozlamalar")
        cfg.add(QLabel("Ustunlar (sonli):"))
        self.an_cols = MultiColumnSelect(kind="num", height=160)
        cfg.add(self.an_cols)
        row = QHBoxLayout()
        row.addWidget(QLabel("Usul:"))
        self.an_method = QComboBox()
        self.an_method.addItems(ml.ANOMALY_METHODS)
        row.addWidget(self.an_method, 1)
        cfg.add_layout(row)
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Kutilgan ulush:"))
        self.an_contam = QDoubleSpinBox()
        self.an_contam.setRange(0.001, 0.4)
        self.an_contam.setSingleStep(0.005)
        self.an_contam.setDecimals(3)
        self.an_contam.setValue(0.02)
        row2.addWidget(self.an_contam)
        cfg.add_layout(row2)
        row3 = QHBoxLayout()
        row3.addWidget(QLabel("z chegara:"))
        self.an_z = QDoubleSpinBox()
        self.an_z.setRange(1.0, 10.0)
        self.an_z.setValue(3.0)
        self.an_z.setSingleStep(0.5)
        row3.addWidget(self.an_z)
        cfg.add_layout(row3)
        row4 = QHBoxLayout()
        row4.addWidget(QLabel("Grafik ustuni:"))
        self.an_plot_col = ColumnCombo("num", allow_empty=True)
        row4.addWidget(self.an_plot_col, 1)
        cfg.add_layout(row4)
        cfg.add(make_button("Anomaliyalarni topish", "Primary", self._run_anomaly))
        cfg.add(make_button("Belgini ustun qilish", "Ghost", self._apply_anomaly))
        self.an_status = QLabel("")
        self.an_status.setObjectName("Hint")
        self.an_status.setWordWrap(True)
        cfg.add(self.an_status)
        lv.addWidget(cfg)
        lv.addStretch(1)
        lay.addWidget(left)

        right = QTabWidget()
        self.an_canvas = ChartCanvas()
        right.addTab(self.an_canvas, "Grafik")
        self.an_table = FrameTable(editable=False)
        right.addTab(self.an_table, "Anomal qatorlar")
        lay.addWidget(right, 1)
        return w

    def _run_anomaly(self) -> None:
        cols = self.an_cols.values()
        if not cols:
            self.notify("Ustunlarni tanlang", "warn")
            return
        self.an_status.setText("Qidirilmoqda…")
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
            f"✓ {res.method}: {res.n_anomalies:,} ta anomaliya ({pct:.2f}%)")
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
            flagged.insert(0, "anomaliya_bahosi", np.round(res.scores[res.is_anomaly], 4))
            self.an_table.set_df(flagged.head(3000))
        except Exception:
            pass

    def _apply_anomaly(self) -> None:
        if self._anomaly is None:
            self.notify("Avval anomaliyalarni toping", "warn")
            return
        df = self.df.copy()
        res = self._anomaly
        df["anomaliya"] = False
        df["anomaliya_bahosi"] = np.nan
        df.loc[res.index, "anomaliya"] = res.is_anomaly
        df.loc[res.index, "anomaliya_bahosi"] = res.scores
        self.store.commit(df, f"Anomaliya belgisi ({res.method})")

    # =============================================  O'lchov kamaytirish  ====
    def _tab_reduce(self) -> QWidget:
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(12)
        left = QWidget()
        left.setMaximumWidth(330)
        lv = QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 0, 0)
        cfg = Card("Sozlamalar")
        cfg.add(QLabel("Ustunlar:"))
        self.rd_cols = MultiColumnSelect(kind="num", height=170)
        cfg.add(self.rd_cols)
        row = QHBoxLayout()
        row.addWidget(QLabel("Usul:"))
        self.rd_method = QComboBox()
        self.rd_method.addItems(["PCA", "t-SNE", "SVD"])
        row.addWidget(self.rd_method, 1)
        cfg.add_layout(row)
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Rang ustuni:"))
        self.rd_hue = ColumnCombo("any", allow_empty=True)
        row2.addWidget(self.rd_hue, 1)
        cfg.add_layout(row2)
        cfg.add(make_button("Hisoblash", "Primary", self._run_reduce))
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
            self.notify("Kamida 2 ta sonli ustun tanlang", "warn")
            return
        self.rd_status.setText("Hisoblanmoqda… (t-SNE sekin bo'lishi mumkin)")
        run_async(ml.reduce_dim, self.df, cols, method=self.rd_method.currentText(),
                  on_done=self._on_reduce,
                  on_error=lambda m: self._simple_error(self.rd_status, m))

    def _on_reduce(self, payload) -> None:
        coords, info = payload
        hue = self.rd_hue.value()
        labels = np.zeros(len(coords), dtype=int)
        title = f"{info['method']} proyeksiya"
        if hue and hue in self.df.columns:
            try:
                s = self.df.loc[info["index"], hue]
                labels = pd.factorize(s.astype(str))[0]
                title += f" · rang: {hue}"
            except Exception:
                pass
        self.rd_canvas.set_figure(charting.cluster_figure(coords, labels, title=title))
        exp = info.get("explained")
        if exp:
            self.rd_status.setText(
                "✓ Tushuntirilgan dispersiya: "
                + ", ".join(f"PC{i + 1}={v:.1%}" for i, v in enumerate(exp))
                + f" · jami {sum(exp):.1%}")
        else:
            self.rd_status.setText(f"✓ {info['method']} tayyor ({info['n']:,} nuqta)")

    # =====================================================  Bashorat  =======
    def _tab_forecast(self) -> QWidget:
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(12)
        left = QWidget()
        left.setMaximumWidth(330)
        lv = QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 0, 0)
        cfg = Card("Sozlamalar")
        row = QHBoxLayout()
        row.addWidget(QLabel("Vaqt ustuni:"))
        self.fc_time = ColumnCombo("dt")
        row.addWidget(self.fc_time, 1)
        cfg.add_layout(row)
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Qiymat:"))
        self.fc_value = ColumnCombo("num", allow_empty=True)
        row2.addWidget(self.fc_value, 1)
        cfg.add_layout(row2)
        row3 = QHBoxLayout()
        row3.addWidget(QLabel("Chastota:"))
        self.fc_freq = QComboBox()
        self.fc_freq.addItems(["avtomatik", "1min", "5min", "15min", "1h", "6h",
                               "1D", "1W", "1ME"])
        row3.addWidget(self.fc_freq, 1)
        cfg.add_layout(row3)
        row4 = QHBoxLayout()
        row4.addWidget(QLabel("Funksiya:"))
        self.fc_agg = QComboBox()
        self.fc_agg.addItems(["count", "mean", "sum", "max", "min"])
        row4.addWidget(self.fc_agg, 1)
        cfg.add_layout(row4)
        row5 = QHBoxLayout()
        row5.addWidget(QLabel("Nechta oldinga:"))
        self.fc_periods = QSpinBox()
        self.fc_periods.setRange(1, 2000)
        self.fc_periods.setValue(24)
        row5.addWidget(self.fc_periods)
        row5.addWidget(QLabel("Mavsum:"))
        self.fc_season = QSpinBox()
        self.fc_season.setRange(0, 400)
        self.fc_season.setValue(24)
        self.fc_season.setSpecialValueText("yo'q")
        row5.addWidget(self.fc_season)
        cfg.add_layout(row5)
        cfg.add(make_button("Bashorat qilish", "Primary", self._run_forecast))
        cfg.add(make_button("Natijani jadval qilish", "Ghost", self._forecast_to_dataset))
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
            self.notify("Vaqt ustuni topilmadi", "warn")
            return
        value = self.fc_value.value()
        agg = self.fc_agg.currentText()
        freq = self.fc_freq.currentText()
        periods = self.fc_periods.value()
        season = self.fc_season.value() or None
        df = self.df

        def work():
            f = prof_mod.suggest_freq(df[tcol]) if freq == "avtomatik" else freq
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
            f"✓ {len(series):,} nuqta ({freq}) asosida {len(fc)} qadam bashorat")

    def _forecast_to_dataset(self) -> None:
        fc = getattr(self, "_forecast_df", None)
        if fc is None:
            self.notify("Avval bashorat qiling", "warn")
            return
        self.store.add(f"{self.store.active_name}_bashorat", fc)

    # ================================================  Saqlangan model  =====
    def _tab_model(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(10)
        card = Card("Saqlangan modelni qo'llash",
                    "avval o'qitilgan modelni yangi ma'lumotga qo'llang")
        row = QHBoxLayout()
        row.addWidget(make_button("Model faylini tanlash…", "Ghost", self._load_model))
        row.addWidget(make_button("Joriy jadvalga qo'llash", "Primary", self._predict))
        row.addStretch(1)
        card.add_layout(row)
        self.model_info = QLabel("Model yuklanmagan")
        self.model_info.setObjectName("Mono")
        self.model_info.setWordWrap(True)
        card.add(self.model_info)
        lay.addWidget(card)
        self.pred_table = FrameTable(editable=False)
        lay.addWidget(self.pred_table, 1)
        return w

    def _load_model(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Model", str(MODELS_DIR),
                                              "Joblib (*.joblib);;Barchasi (*.*)")
        if not path:
            return
        try:
            self._bundle = ml.load_model(path)
        except Exception as exc:
            self.notify(f"Model yuklanmadi: {exc}", "error")
            return
        b = self._bundle
        metrics = " · ".join(f"{k}={v:.4f}" if isinstance(v, float) else f"{k}={v}"
                             for k, v in list(b.get("metrics", {}).items())[:4])
        self.model_info.setText(
            f"Model: {b.get('name')}\nVazifa: {b.get('task')}\n"
            f"Nishon: {b.get('target')}\nXususiyatlar ({len(b.get('features', []))}): "
            f"{', '.join(b.get('features', [])[:15])}\nMetrikalar: {metrics}")
        self.notify("Model yuklandi", "success")

    def _predict(self) -> None:
        if self._bundle is None:
            self.notify("Avval model faylini tanlang", "warn")
            return
        if not self.has_data():
            self.notify("Avval ma'lumot yuklang", "warn")
            return
        try:
            out = ml.predict_with(self._bundle, self.df)
        except Exception as exc:
            self.notify(f"Bashorat xatosi: {exc}", "error")
            return
        self.pred_table.set_df(out.head(1000))
        self.store.commit(out, f"Saqlangan model bashorati ({self._bundle.get('name')})")

    # ---------------------------------------------------------- umumiy -----
    def _simple_error(self, label: QLabel, msg: str) -> None:
        first = msg.splitlines()[0]
        label.setText(f"Xato: {first}")
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
