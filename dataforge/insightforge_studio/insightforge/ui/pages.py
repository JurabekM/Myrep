from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractItemView, QComboBox, QFileDialog, QFormLayout,
                               QGridLayout, QHBoxLayout, QLabel, QLineEdit, QListWidget,
                               QListWidgetItem, QMessageBox, QPlainTextEdit, QProgressBar,
                               QSpinBox, QSplitter, QTabWidget, QTextEdit, QVBoxLayout,
                               QWidget)

from ..config import EXPORT_DIR, MODEL_DIR
from ..core import charts, importer, logs, ml, persistence, pipeline, profiling, reporting
from ..core.types import ImportResult
from .state import AppState
from .widgets import (Card, ColumnCombo, FrameTable, PageHeader, StatCard, button,
                      human_bytes, row)
from .workers import submit


class BasePage(QWidget):
    def __init__(self, state: AppState) -> None:
        super().__init__()
        self.state = state

    @property
    def dataset(self):
        return self.state.workspace.active

    def refresh(self) -> None:
        pass

    def error(self, detail: str) -> None:
        QMessageBox.critical(self, "Amal bajarilmadi", detail)


class DashboardPage(BasePage):
    def __init__(self, state: AppState) -> None:
        super().__init__(state)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.addWidget(PageHeader("Command Center", "Workspace holati va tezkor analitik ko'rsatkichlar"))
        metrics = QHBoxLayout()
        self.cards = {
            "datasets": StatCard("Datasetlar"), "rows": StatCard("Jami qatorlar"),
            "memory": StatCard("Xotira"), "events": StatCard("Audit hodisalari"),
        }
        for card in self.cards.values():
            metrics.addWidget(card)
        layout.addLayout(metrics)
        body = QSplitter()
        catalog = Card("Dataset katalogi")
        self.catalog = FrameTable()
        catalog.layout_.addWidget(self.catalog)
        body.addWidget(catalog)
        health = Card("Faol dataset health")
        self.health_label = QLabel("Dataset yuklanmagan")
        self.health_label.setStyleSheet("font-size:34px;font-weight:800;color:#38D996")
        self.issues = QListWidget()
        health.layout_.addWidget(self.health_label)
        health.layout_.addWidget(self.issues)
        body.addWidget(health)
        body.setSizes([700, 380])
        layout.addWidget(body, 1)

    def refresh(self) -> None:
        summary = self.state.workspace.summary()
        self.cards["datasets"].value.setText(f"{summary['datasets']:,}")
        self.cards["rows"].value.setText(f"{summary['rows']:,}")
        self.cards["memory"].value.setText(human_bytes(summary["memory_bytes"]))
        self.cards["events"].value.setText(f"{summary['audit_events']:,}")
        records = [{"name": d.name, "rows": len(d.frame), "columns": d.frame.shape[1],
                    "kind": d.kind, "revision": d.revision, "memory": human_bytes(d.memory_bytes)}
                   for d in self.state.workspace.datasets]
        self.catalog.set_frame(pd.DataFrame(records))
        self.issues.clear()
        if self.dataset is None:
            self.health_label.setText("Dataset yo'q")
            return
        result = profiling.profile_frame(self.dataset.frame)
        self.health_label.setText(f"{result.health_score:.0f} / 100")
        for issue in result.issues[:12]:
            self.issues.addItem(f"{issue.severity.upper()} · {issue.title} · {issue.column or 'dataset'}")


class ImportPage(BasePage):
    def __init__(self, state: AppState) -> None:
        super().__init__(state)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.addWidget(PageHeader("Data Hub", "Fayl, URL, clipboard va demo manbalarni workspace'ga ulang"))
        actions = QHBoxLayout()
        open_file = button("Fayl tanlash", True)
        open_file.clicked.connect(self._file)
        demo = button("Demo dataset")
        demo.clicked.connect(self._demo)
        actions.addWidget(open_file)
        actions.addWidget(demo)
        actions.addStretch()
        layout.addLayout(actions)
        tabs = QTabWidget()
        tabs.addTab(self._text_tab(), "Matn / Clipboard")
        tabs.addTab(self._url_tab(), "Internet URL")
        layout.addWidget(tabs, 1)
        self.preview_card = Card("Import preview")
        self.preview = FrameTable()
        self.preview_card.layout_.addWidget(self.preview)
        layout.addWidget(self.preview_card, 2)
        self.pending: ImportResult | None = None
        self.add_button = button("Workspace'ga qo'shish", True)
        self.add_button.clicked.connect(self._accept)
        self.add_button.setEnabled(False)
        layout.addWidget(self.add_button, alignment=Qt.AlignmentFlag.AlignRight)

    def _text_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        self.text_name = QLineEdit("Clipboard data")
        self.text_input = QPlainTextEdit()
        self.text_input.setPlaceholderText("CSV, TSV yoki JSON matnini shu yerga qo'ying…")
        parse = button("Tahlil qilish")
        parse.clicked.connect(self._parse_text)
        layout.addWidget(self.text_name)
        layout.addWidget(self.text_input)
        layout.addWidget(parse, alignment=Qt.AlignmentFlag.AlignRight)
        return tab

    def _url_tab(self) -> QWidget:
        tab = QWidget()
        layout = QFormLayout(tab)
        self.url = QLineEdit()
        self.url.setPlaceholderText("https://example.com/data.csv")
        fetch = button("Yuklash", True)
        fetch.clicked.connect(self._fetch_url)
        layout.addRow("URL", self.url)
        layout.addRow("", fetch)
        return tab

    def _file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Ma'lumot fayli", "",
            "Data (*.csv *.tsv *.json *.jsonl *.xlsx *.parquet *.feather *.log *.txt *.zip *.db *.sqlite);;All files (*)")
        if path:
            submit(importer.load_file, path, on_done=self._loaded, on_error=self.error)

    def _parse_text(self) -> None:
        try:
            self._loaded(importer.load_text(self.text_input.toPlainText(), self.text_name.text()))
        except Exception as exc:
            self.error(str(exc))

    def _fetch_url(self) -> None:
        submit(importer.load_url, self.url.text().strip(), on_done=self._loaded, on_error=self.error)

    def _loaded(self, result: ImportResult) -> None:
        self.pending = result
        self.preview.set_frame(result.frame.head(1000))
        self.add_button.setEnabled(True)
        self.state.message.emit(f"Preview: {len(result.frame):,} qator", "info")

    def _accept(self) -> None:
        if not self.pending:
            return
        self.state.workspace.add(self.pending.name, self.pending.frame, source=self.pending.source,
                                 kind=self.pending.kind)
        self.state.notify_added()
        self.state.message.emit(f"{self.pending.name} workspace'ga qo'shildi", "success")
        self.pending = None
        self.add_button.setEnabled(False)

    def _demo(self) -> None:
        rng = np.random.default_rng(17)
        n = 2500
        dates = pd.date_range("2025-01-01", periods=n, freq="h")
        region = rng.choice(["Toshkent", "Samarqand", "Farg'ona", "Buxoro"], n)
        channel = rng.choice(["Web", "Mobile", "Partner"], n, p=[.48, .40, .12])
        revenue = rng.gamma(5, 42, n) * np.where(channel == "Partner", 1.25, 1)
        frame = pd.DataFrame({"timestamp": dates, "region": region, "channel": channel,
                              "revenue": revenue.round(2), "orders": rng.poisson(4, n),
                              "latency_ms": rng.lognormal(4.4, .45, n).round(1),
                              "converted": rng.random(n) < .29})
        frame.loc[rng.choice(n, 70, replace=False), "revenue"] = np.nan
        self._loaded(ImportResult(frame, "Commerce Pulse", "generated", "demo"))


class ExplorerPage(BasePage):
    def __init__(self, state: AppState) -> None:
        super().__init__(state)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.addWidget(PageHeader("Data Explorer", "Qidirish, saralash va dataset tarkibini tekshirish"))
        toolbar = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Barcha ustunlardan qidirish…")
        self.search.returnPressed.connect(self.refresh)
        self.info = QLabel()
        undo = button("↶ Undo")
        redo = button("↷ Redo")
        undo.clicked.connect(self._undo)
        redo.clicked.connect(self._redo)
        export = button("Eksport")
        export.clicked.connect(self._export)
        toolbar.addWidget(self.search, 1)
        toolbar.addWidget(self.info)
        toolbar.addWidget(undo)
        toolbar.addWidget(redo)
        toolbar.addWidget(export)
        layout.addLayout(toolbar)
        self.table = FrameTable()
        layout.addWidget(self.table, 1)

    def refresh(self) -> None:
        if not self.dataset:
            self.table.set_frame(pd.DataFrame())
            self.info.setText("Dataset yo'q")
            return
        frame = self.dataset.frame
        query = self.search.text().strip()
        if query:
            mask = frame.astype("string").apply(lambda column: column.str.contains(query, case=False, regex=False, na=False)).any(axis=1)
            frame = frame.loc[mask]
        self.table.set_frame(frame)
        self.info.setText(f"{len(frame):,} × {frame.shape[1]}")

    def _undo(self) -> None:
        if self.dataset:
            self.state.workspace.undo(self.dataset.id)
            self.state.notify_data()

    def _redo(self) -> None:
        if self.dataset:
            self.state.workspace.redo(self.dataset.id)
            self.state.notify_data()

    def _export(self) -> None:
        if not self.dataset:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Eksport", str(EXPORT_DIR / self.dataset.name),
                                               "CSV (*.csv);;Excel (*.xlsx);;Parquet (*.parquet);;JSON (*.json)")
        if path:
            try:
                importer.export_frame(self.dataset.frame, path)
                self.state.message.emit("Eksport tayyor", "success")
            except Exception as exc:
                self.error(str(exc))


class PipelinePage(BasePage):
    def __init__(self, state: AppState) -> None:
        super().__init__(state)
        self.pipeline = pipeline.Pipeline("Workspace pipeline")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.addWidget(PageHeader("Pipeline Builder", "Transformlarni ketma-ket yig'ing, preview qiling va qo'llang"))
        splitter = QSplitter()
        library = Card("Operatsiyalar")
        self.operations = QListWidget()
        for key, op in pipeline.OPERATIONS.items():
            item = QListWidgetItem(f"{op.group} · {op.label}")
            item.setData(Qt.ItemDataRole.UserRole, key)
            self.operations.addItem(item)
        add = button("Pipeline'ga qo'shish", True)
        add.clicked.connect(self._add)
        library.layout_.addWidget(self.operations)
        library.layout_.addWidget(add)
        splitter.addWidget(library)
        center = Card("Pipeline")
        self.steps = QListWidget()
        self.steps.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        remove = button("Tanlanganni o'chirish", danger=True)
        remove.clicked.connect(self._remove)
        center.layout_.addWidget(self.steps)
        center.layout_.addWidget(remove)
        splitter.addWidget(center)
        params = Card("Parametrlar")
        self.params = QTextEdit()
        self.params.setPlaceholderText('{\n  "columns": ["revenue"],\n  "method": "median"\n}')
        preview = button("Preview")
        preview.clicked.connect(self._preview)
        apply = button("Datasetga qo'llash", True)
        apply.clicked.connect(self._apply)
        params.layout_.addWidget(QLabel("JSON parametrlar"))
        params.layout_.addWidget(self.params)
        params.layout_.addWidget(row(preview, apply))
        splitter.addWidget(params)
        splitter.setSizes([260, 390, 390])
        layout.addWidget(splitter, 1)
        self.preview_table = FrameTable()
        layout.addWidget(self.preview_table, 1)

    def _add(self) -> None:
        import json
        item = self.operations.currentItem()
        if not item:
            return
        key = item.data(Qt.ItemDataRole.UserRole)
        try:
            params = json.loads(self.params.toPlainText() or "{}")
            self.pipeline.add(key, **params)
            self._sync()
        except Exception as exc:
            self.error(str(exc))

    def _remove(self) -> None:
        row_index = self.steps.currentRow()
        if row_index >= 0:
            self.pipeline.steps.pop(row_index)
            self._sync()

    def _sync(self) -> None:
        self.steps.clear()
        for index, step in enumerate(self.pipeline.steps, 1):
            self.steps.addItem(f"{index:02d}  {pipeline.OPERATIONS[step.operation].label}  {step.params}")

    def _preview(self) -> None:
        if not self.dataset:
            return
        try:
            result = self.pipeline.run(self.dataset.frame.head(20_000))
            self.preview_table.set_frame(result.frame)
            self.state.message.emit(f"Preview: {result.frame.shape}", "success")
        except Exception as exc:
            self.error(str(exc))

    def _apply(self) -> None:
        if not self.dataset:
            return
        dataset_id = self.dataset.id
        submit(self.pipeline.run, self.dataset.frame, on_done=lambda result: self._committed(dataset_id, result),
               on_error=self.error)

    def _committed(self, dataset_id, result) -> None:
        self.state.workspace.commit(dataset_id, result.frame, "pipeline.run", {"steps": len(result.log)})
        self.state.notify_data()
        self.preview_table.set_frame(result.frame)


class AnalyticsPage(BasePage):
    def __init__(self, state: AppState) -> None:
        super().__init__(state)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.addWidget(PageHeader("Analytics Lab", "Data health, segmentlar va interaktiv vizualizatsiya"))
        controls = QHBoxLayout()
        self.kind = QComboBox(); self.kind.addItems(charts.CHARTS.keys())
        self.x = ColumnCombo(empty=True); self.y = ColumnCombo(empty=True); self.color = ColumnCombo(empty=True)
        draw = button("Grafik chizish", True); draw.clicked.connect(self._draw)
        add = button("Hisobotga qo'shish"); add.clicked.connect(self._gallery)
        for label, widget in (("Grafik", self.kind), ("X", self.x), ("Y", self.y), ("Rang", self.color)):
            controls.addWidget(QLabel(label)); controls.addWidget(widget)
        controls.addWidget(draw); controls.addWidget(add)
        layout.addLayout(controls)
        splitter = QSplitter(Qt.Orientation.Vertical)
        self.canvas = FigureCanvasQTAgg(charts.build_chart(pd.DataFrame(), "histogram"))
        splitter.addWidget(self.canvas)
        tabs = QTabWidget()
        self.profile_table = FrameTable(); self.issue_table = FrameTable(); self.corr_table = FrameTable()
        tabs.addTab(self.profile_table, "Ustunlar profili")
        tabs.addTab(self.issue_table, "Quality issues")
        tabs.addTab(self.corr_table, "Korrelyatsiyalar")
        splitter.addWidget(tabs)
        splitter.setSizes([540, 280])
        layout.addWidget(splitter, 1)
        self.current_figure = None

    def refresh(self) -> None:
        frame = self.dataset.frame if self.dataset else pd.DataFrame()
        for combo in (self.x, self.y, self.color):
            combo.populate(frame)
        if self.dataset:
            result = profiling.profile_frame(frame)
            self.profile_table.set_frame(result.column_stats)
            self.issue_table.set_frame(pd.DataFrame([vars_issue(issue) for issue in result.issues]))
            self.corr_table.set_frame(profiling.strongest_correlations(frame))

    def _draw(self) -> None:
        if not self.dataset:
            return
        try:
            figure = charts.build_chart(self.dataset.frame, self.kind.currentText(), x=self.x.value(),
                                        y=self.y.value(), color=self.color.value())
            self.canvas.figure = figure
            self.canvas.draw()
            self.current_figure = figure
        except Exception as exc:
            self.error(str(exc))

    def _gallery(self) -> None:
        if self.current_figure:
            self.state.figures.append((charts.CHARTS[self.kind.currentText()], self.current_figure))
            self.state.message.emit("Grafik hisobot galereyasiga qo'shildi", "success")


class ModelPage(BasePage):
    def __init__(self, state: AppState) -> None:
        super().__init__(state)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.addWidget(PageHeader("Model Studio", "AutoML, klasterlash va anomaliya deteksiyasi"))
        controls = QHBoxLayout()
        self.target = ColumnCombo()
        self.mode = QComboBox(); self.mode.addItems(["AutoML", "Anomaly detection", "Clustering"])
        self.count = QSpinBox(); self.count.setRange(2, 12); self.count.setValue(4)
        run = button("Ishga tushirish", True); run.clicked.connect(self._run)
        save = button("Modelni saqlash"); save.clicked.connect(self._save)
        controls.addWidget(QLabel("Rejim")); controls.addWidget(self.mode)
        controls.addWidget(QLabel("Target / K")); controls.addWidget(self.target); controls.addWidget(self.count)
        controls.addStretch(); controls.addWidget(run); controls.addWidget(save)
        layout.addLayout(controls)
        self.progress = QProgressBar(); layout.addWidget(self.progress)
        tabs = QTabWidget()
        self.leaderboard = FrameTable(); self.predictions = FrameTable(); self.notes = QListWidget()
        tabs.addTab(self.leaderboard, "Leaderboard")
        tabs.addTab(self.predictions, "Natijalar")
        tabs.addTab(self.notes, "Tavsiyalar")
        layout.addWidget(tabs, 1)

    def refresh(self) -> None:
        self.target.populate(self.dataset.frame if self.dataset else pd.DataFrame())

    def _run(self) -> None:
        if not self.dataset:
            return
        mode = self.mode.currentText()
        if mode == "AutoML":
            submit(ml.train_automl, self.dataset.frame, self.target.value(), on_done=self._automl_done,
                   on_error=self.error, on_progress=self._progress, progress_enabled=True)
        else:
            numeric = list(self.dataset.frame.select_dtypes(include=np.number).columns)
            if not numeric:
                return self.error("Sonli ustunlar topilmadi")
            if mode == "Anomaly detection":
                submit(ml.anomaly_detection, self.dataset.frame, numeric,
                       on_done=lambda frame: self._derived(frame, "Anomaly result"), on_error=self.error)
            else:
                submit(ml.cluster, self.dataset.frame, numeric, self.count.value(),
                       on_done=lambda result: self._cluster_done(result), on_error=self.error)

    def _progress(self, text: str, value: int) -> None:
        self.progress.setValue(value); self.progress.setFormat(text + " %p%")

    def _automl_done(self, result: ml.ModelRun) -> None:
        self.state.model_run = result
        self.leaderboard.set_frame(result.leaderboard)
        self.predictions.set_frame(result.predictions.reset_index())
        self.notes.clear(); self.notes.addItems(result.notes or ["Leakage signali topilmadi"])
        self.progress.setValue(100)

    def _derived(self, frame: pd.DataFrame, name: str) -> None:
        self.state.workspace.add(name, frame, source=self.dataset.name if self.dataset else "model", kind="derived")
        self.state.notify_added(); self.predictions.set_frame(frame)

    def _cluster_done(self, result) -> None:
        frame, metrics = result
        self._derived(frame, "Cluster result")
        self.notes.clear(); self.notes.addItem(f"Silhouette: {metrics['silhouette']:.3f}")

    def _save(self) -> None:
        if not self.state.model_run:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Model", str(MODEL_DIR / "model.joblib"), "Joblib (*.joblib)")
        if path:
            ml.save_model(self.state.model_run, path)


class LogLabPage(BasePage):
    def __init__(self, state: AppState) -> None:
        super().__init__(state)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.addWidget(PageHeader("Log Intelligence", "Shablon, entity, level va vaqt portlashlarini aniqlang"))
        toolbar = QHBoxLayout()
        self.message_column = ColumnCombo()
        self.time_column = ColumnCombo(empty=True)
        analyze = button("Log tahlilini boshlash", True)
        analyze.clicked.connect(self._analyze)
        toolbar.addWidget(QLabel("Xabar ustuni")); toolbar.addWidget(self.message_column)
        toolbar.addWidget(QLabel("Vaqt ustuni")); toolbar.addWidget(self.time_column)
        toolbar.addStretch(); toolbar.addWidget(analyze)
        layout.addLayout(toolbar)
        tabs = QTabWidget()
        self.templates = FrameTable(); self.entities = FrameTable(); self.levels = FrameTable(); self.bursts = FrameTable()
        tabs.addTab(self.templates, "Shablonlar")
        tabs.addTab(self.entities, "Entitylar")
        tabs.addTab(self.levels, "Darajalar")
        tabs.addTab(self.bursts, "Burst detection")
        layout.addWidget(tabs, 1)

    def refresh(self) -> None:
        frame = self.dataset.frame if self.dataset else pd.DataFrame()
        self.message_column.populate(frame)
        self.time_column.populate(frame)
        candidates = [c for c in frame.columns if any(x in c.lower() for x in ("message", "msg", "raw", "text"))]
        if candidates:
            self.message_column.setCurrentText(candidates[0])

    def _analyze(self) -> None:
        if not self.dataset or not self.message_column.value():
            return
        frame = self.dataset.frame
        try:
            messages = frame[self.message_column.value()]
            self.templates.set_frame(logs.mine_templates(messages))
            self.entities.set_frame(logs.entity_counts(messages))
            self.levels.set_frame(logs.level_summary(frame))
            if self.time_column.value():
                self.bursts.set_frame(logs.burst_detection(frame, self.time_column.value()))
        except Exception as exc:
            self.error(str(exc))


class ReportPage(BasePage):
    def __init__(self, state: AppState) -> None:
        super().__init__(state)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.addWidget(PageHeader("Report Composer", "Profil, grafik va auditni mustaqil HTML hujjatga yig'ing"))
        card = Card("Hisobot sozlamalari")
        form = QFormLayout()
        self.title = QLineEdit()
        self.notes = QTextEdit(); self.notes.setMaximumHeight(120)
        form.addRow("Sarlavha", self.title); form.addRow("Izoh", self.notes)
        card.layout_.addLayout(form)
        self.gallery = QLabel("Galereya: 0 grafik")
        create = button("HTML hisobot yaratish", True); create.clicked.connect(self._create)
        card.layout_.addWidget(self.gallery); card.layout_.addWidget(create, alignment=Qt.AlignmentFlag.AlignRight)
        layout.addWidget(card)
        self.preview = QPlainTextEdit(); self.preview.setReadOnly(True)
        layout.addWidget(self.preview, 1)

    def refresh(self) -> None:
        self.gallery.setText(f"Galereya: {len(self.state.figures)} grafik")
        if self.dataset and not self.title.text():
            self.title.setText(f"{self.dataset.name} · Analitik hisobot")

    def _create(self) -> None:
        if not self.dataset:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Hisobot", str(EXPORT_DIR / self.dataset.name), "HTML (*.html)")
        if not path:
            return
        content = reporting.build_html_report(self.dataset.frame, self.title.text() or self.dataset.name,
                                              figures=self.state.figures, notes=self.notes.toPlainText(),
                                              audit=self.state.workspace.audit_records())
        saved = reporting.save_html(content, path)
        self.preview.setPlainText(f"Hisobot tayyor:\n{saved}\n\nHajm: {saved.stat().st_size / 1024:.1f} KB")
        self.state.message.emit("HTML hisobot tayyor", "success")


def vars_issue(issue: profiling.QualityIssue) -> dict:
    return {"severity": issue.severity, "title": issue.title, "column": issue.column,
            "detail": issue.detail, "count": issue.count}
