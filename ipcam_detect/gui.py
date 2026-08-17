"""gui.py — ipcam_detect uchun professional dark-tema GUI (PyQt6).

Terminalsiz to'liq boshqaruv: manba, model, pipeline sozlamalari, jonli
preview, resurs monitoringi, deteksiya jadvali, loglar va profillar.

Ishga tushirish:
    python gui.py                 # oddiy
    pythonw gui.py                # konsol oynasisiz (Windows)
    run_gui.bat                   # ikki marta bosib

Arxitektura: `PipelineManager` alohida `QThread` da ishlaydi, kadrlar va
statistika Qt signallari orqali GUI thread'iga uzatiladi (Qt widget'lariga
faqat asosiy thread'dan tegish mumkin).
"""

from __future__ import annotations

import json
import logging
import re
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence

import numpy as np
from PyQt6.QtCore import QObject, QRect, Qt, QThread, QTimer, pyqtSignal
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QImage,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
)
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from ipcam_detect import (  # noqa: E402
    COCO_CLASSES,
    DetectorConfig,
    PipelineConfig,
    PipelineManager,
    StreamConfig,
)
from ipcam_detect.stream_handler import _HAS_AV  # noqa: E402
from ipcam_detect.visualizer import Visualizer  # noqa: E402

APP_NAME = "IPCam Detect Studio"


def _mask_url(url: str) -> str:
    """Log/ekranda parolni yashiradi: rtsp://user:***@host/…"""
    return re.sub(r"(rtsp://[^:/@]+:)[^@]*(@)",
                  lambda m: m.group(1) + "***" + m.group(2), url)

PRESETS_FILE = ROOT / "gui_presets.json"
SNAP_DIR = ROOT / "out" / "snapshots"

# --------------------------------------------------------------- dark tema
C = {
    "bg": "#0f1115",          # eng orqa fon
    "panel": "#161a21",       # panel foni
    "panel2": "#1c212b",      # ichki blok
    "border": "#262c38",
    "text": "#e6e9ef",
    "muted": "#8b93a7",
    "accent": "#4cc38a",      # asosiy urg'u (yashil)
    "accent2": "#3b82f6",     # ikkilamchi (ko'k)
    "warn": "#f0b429",
    "danger": "#ef4444",
}

QSS = f"""
* {{ font-family: "Segoe UI", "Inter", sans-serif; font-size: 13px; }}
QWidget {{ background: {C['bg']}; color: {C['text']}; }}
QMainWindow, QDialog {{ background: {C['bg']}; }}

QGroupBox {{
    background: {C['panel']};
    border: 1px solid {C['border']};
    border-radius: 10px;
    margin-top: 18px;
    padding: 12px 10px 10px 10px;
    font-weight: 600;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 12px; top: 2px;
    padding: 2px 6px;
    color: {C['muted']};
    font-size: 11px;
    letter-spacing: 1px;
}}

QLabel {{ background: transparent; }}
QCheckBox {{ background: transparent; }}
QLabel#hint {{ color: {C['muted']}; font-size: 11px; }}
QLabel#h1 {{ font-size: 17px; font-weight: 700; }}
QLabel#banner {{
    background: rgba(240,180,41,0.12);
    border: 1px solid rgba(240,180,41,0.35);
    border-radius: 8px; padding: 8px 10px; color: {C['warn']};
}}

QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QPlainTextEdit, QListWidget,
QTableWidget {{
    background: {C['panel2']};
    border: 1px solid {C['border']};
    border-radius: 8px;
    padding: 6px 8px;
    selection-background-color: {C['accent2']};
}}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
    border: 1px solid {C['accent']};
}}
QComboBox QAbstractItemView {{
    background: {C['panel2']}; border: 1px solid {C['border']};
    selection-background-color: {C['accent2']}; outline: none;
}}
QSpinBox::up-button, QSpinBox::down-button,
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{ width: 16px; }}

QPushButton {{
    background: {C['panel2']};
    border: 1px solid {C['border']};
    border-radius: 8px;
    padding: 7px 14px;
    font-weight: 600;
}}
QPushButton:hover {{ border-color: {C['accent']}; color: {C['accent']}; }}
QPushButton:pressed {{ background: #11151c; }}
QPushButton:disabled {{ color: #4a5164; border-color: #1e2430; }}

QPushButton#primary {{
    background: {C['accent']}; border: none; color: #06251a;
}}
QPushButton#primary:hover {{ background: #5fd39b; }}
QPushButton#danger {{
    background: {C['danger']}; border: none; color: #2a0707;
}}
QPushButton#danger:hover {{ background: #f16a6a; }}

QCheckBox {{ spacing: 8px; }}
QCheckBox::indicator {{
    width: 16px; height: 16px; border-radius: 4px;
    border: 1px solid {C['border']}; background: {C['panel2']};
}}
QCheckBox::indicator:checked {{ background: {C['accent']}; border-color: {C['accent']}; }}

QHeaderView::section {{
    background: {C['panel']}; color: {C['muted']};
    border: none; border-bottom: 1px solid {C['border']};
    padding: 6px; font-size: 11px; letter-spacing: 0.5px;
}}
QTableWidget {{ gridline-color: {C['border']}; }}
QTableWidget::item {{ padding: 4px; }}

QPlainTextEdit {{ font-family: "Cascadia Mono", Consolas, monospace; font-size: 12px; }}

QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: #2c3444; border-radius: 5px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: #3a4356; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; }}
QScrollBar::handle:horizontal {{ background: #2c3444; border-radius: 5px; }}

QSplitter::handle {{ background: {C['border']}; }}
QStatusBar {{ background: {C['panel']}; border-top: 1px solid {C['border']}; }}
"""


# ============================================================== widgetlar
class SparkLine(QWidget):
    """Yengil jonli grafik — QtCharts'siz, faqat QPainter (kam resurs)."""

    def __init__(self, color: str, maxlen: int = 90, parent=None) -> None:
        super().__init__(parent)
        self._vals: List[float] = []
        self._maxlen = maxlen
        self._color = QColor(color)
        self.setMinimumHeight(38)

    def push(self, value: float) -> None:
        self._vals.append(float(value))
        if len(self._vals) > self._maxlen:
            del self._vals[0]
        self.update()

    def clear(self) -> None:
        self._vals.clear()
        self.update()

    def paintEvent(self, _ev) -> None:
        if len(self._vals) < 2:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        top = max(self._vals) or 1.0
        step = w / (len(self._vals) - 1)

        path = QPainterPath()
        fill = QPainterPath()
        fill.moveTo(0, h)
        for i, v in enumerate(self._vals):
            x = i * step
            y = h - (v / top) * (h - 4) - 2
            if i == 0:
                path.moveTo(x, y)
            else:
                path.lineTo(x, y)
            fill.lineTo(x, y)
        fill.lineTo(w, h)
        fill.closeSubpath()

        grad = QLinearGradient(0, 0, 0, h)
        c = QColor(self._color)
        c.setAlpha(70)
        grad.setColorAt(0.0, c)
        c2 = QColor(self._color)
        c2.setAlpha(0)
        grad.setColorAt(1.0, c2)
        p.fillPath(fill, QBrush(grad))
        p.setPen(QPen(self._color, 1.6))
        p.drawPath(path)
        p.end()


class StatCard(QFrame):
    """Katta raqamli ko'rsatkich + mini grafik."""

    def __init__(self, title: str, unit: str = "", color: str = C["accent"],
                 spark: bool = True, parent=None) -> None:
        super().__init__(parent)
        # DIQQAT: QLabel ham QFrame merosxo'ri — selektorni objectName bilan
        # cheklamasak, ichkaridagi bo'sh label'lar ham ramkali quti bo'lib chiqadi.
        self.setObjectName("card")
        self.setStyleSheet(
            f"QFrame#card {{ background: {C['panel']}; border: 1px solid {C['border']};"
            f" border-radius: 10px; }}"
        )
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 8, 12, 8)
        lay.setSpacing(2)

        t = QLabel(title.upper())
        t.setStyleSheet(f"color:{C['muted']}; font-size:10px; letter-spacing:1px;"
                        " border:none; background:transparent;")
        row = QHBoxLayout()
        row.setSpacing(4)
        self.value = QLabel("0")
        self.value.setStyleSheet(
            f"font-size:22px; font-weight:700; color:{color};"
            " border:none; background:transparent;")
        u = QLabel(unit)
        u.setStyleSheet(f"color:{C['muted']}; font-size:11px; border:none;"
                        " background:transparent;")
        row.addWidget(self.value)
        row.addWidget(u, alignment=Qt.AlignmentFlag.AlignBottom)
        row.addStretch(1)

        lay.addWidget(t)
        lay.addLayout(row)
        self.spark: Optional[SparkLine] = None
        if spark:
            self.spark = SparkLine(color)
            self.spark.setStyleSheet("border:none; background:transparent;")
            lay.addWidget(self.spark)

    def set_value(self, text: str, spark_value: Optional[float] = None) -> None:
        self.value.setText(text)
        if self.spark is not None and spark_value is not None:
            self.spark.push(spark_value)

    def reset(self) -> None:
        self.value.setText("0")
        if self.spark:
            self.spark.clear()


class VideoView(QWidget):
    """Kadrni nisbatni saqlab chizadigan preview maydoni."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._image: Optional[QImage] = None
        self._placeholder = "Oqim ulanmagan\n\n«BOSHLASH» tugmasini bosing"
        self.setMinimumSize(480, 300)
        self.setStyleSheet("background: #0b0d11; border-radius: 10px;")

    def set_frame(self, image: Optional[QImage]) -> None:
        self._image = image
        self.update()

    def clear(self, text: str = "") -> None:
        if text:
            self._placeholder = text
        self._image = None
        self.update()

    def paintEvent(self, _ev) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        p.fillRect(self.rect(), QColor("#0b0d11"))

        if self._image is None:
            p.setPen(QColor(C["muted"]))
            f = QFont("Segoe UI", 11)
            p.setFont(f)
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self._placeholder)
            p.end()
            return

        img = self._image
        aw, ah = self.width(), self.height()
        scale = min(aw / img.width(), ah / img.height())
        w, h = int(img.width() * scale), int(img.height() * scale)
        p.drawImage(QRect((aw - w) // 2, (ah - h) // 2, w, h), img)
        p.end()


class ClassDialog(QDialog):
    """COCO sinflarini tanlash oynasi (qidiruv bilan)."""

    def __init__(self, selected: Sequence[int], parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Sinflarni tanlash")
        self.resize(360, 520)
        lay = QVBoxLayout(self)

        self.search = QLineEdit(placeholderText="Qidirish… (masalan: person)")
        self.search.textChanged.connect(self._filter)
        lay.addWidget(self.search)

        self.list = QListWidget()
        for i, name in enumerate(COCO_CLASSES):
            it = QListWidgetItem(f"{i:>2}  {name}")
            it.setFlags(it.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            it.setCheckState(Qt.CheckState.Checked if i in selected
                             else Qt.CheckState.Unchecked)
            it.setData(Qt.ItemDataRole.UserRole, i)
            self.list.addItem(it)
        lay.addWidget(self.list, 1)

        row = QHBoxLayout()
        for text, fn in (("Hammasi", lambda: self._set_all(True)),
                         ("Hech biri", lambda: self._set_all(False)),
                         ("Faqat odam", self._only_person)):
            b = QPushButton(text)
            b.clicked.connect(fn)
            row.addWidget(b)
        lay.addLayout(row)

        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok |
                              QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)

    def _filter(self, text: str) -> None:
        text = text.lower().strip()
        for i in range(self.list.count()):
            it = self.list.item(i)
            it.setHidden(bool(text) and text not in it.text().lower())

    def _set_all(self, on: bool) -> None:
        state = Qt.CheckState.Checked if on else Qt.CheckState.Unchecked
        for i in range(self.list.count()):
            if not self.list.item(i).isHidden():
                self.list.item(i).setCheckState(state)

    def _only_person(self) -> None:
        self._set_all(False)
        self.list.item(0).setCheckState(Qt.CheckState.Checked)

    def selected(self) -> List[int]:
        return [self.list.item(i).data(Qt.ItemDataRole.UserRole)
                for i in range(self.list.count())
                if self.list.item(i).checkState() == Qt.CheckState.Checked]


# ================================================================== logging
class _Emitter(QObject):
    """Faqat signal tashuvchi yordamchi QObject."""

    message = pyqtSignal(str, int)


class QtLogBridge(logging.Handler):
    """`logging` yozuvlarini Qt signaliga aylantiradi (thread-safe).

    Ataylab QObject'dan MEROS OLINMAYDI: PyQt dastur yopilishida barcha C++
    obyektlarni o'chiradi, keyin esa `logging.shutdown()` atexit da har bir
    handler'ga murojaat qiladi — o'chirilgan sip-wrapper RuntimeError beradi.
    Signal alohida `_Emitter` da saqlanadi, handler esa sof Python obyekti.
    """

    def __init__(self) -> None:
        super().__init__()
        self._emitter = _Emitter()
        self.setFormatter(logging.Formatter(
            "%(asctime)s  %(name)-24s  %(message)s", datefmt="%H:%M:%S"))

    @property
    def message(self):
        """`bridge.message.connect(...)` uchun signalga qisqa yo'l."""
        return self._emitter.message

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self._emitter.message.emit(self.format(record), record.levelno)
        except RuntimeError:
            pass  # oyna yopilgan (Qt obyekti o'chirilgan)


# =================================================================== worker
@dataclass
class Stats:
    fps: float = 0.0
    infer_ms: float = 0.0
    cpu: float = 0.0
    ram: float = 0.0
    read: int = 0
    dropped: int = 0
    reconnects: int = 0
    connected: bool = False
    frames: int = 0
    detections: int = 0
    counts: Dict[str, int] = None  # type: ignore[assignment]


class PipelineWorker(QThread):
    """`PipelineManager` ni fon thread'ida yuritadi."""

    frameReady = pyqtSignal(object)      # np.ndarray (BGR, allaqachon nusxa)
    statsReady = pyqtSignal(object)      # Stats
    failed = pyqtSignal(str)
    started_ok = pyqtSignal()

    def __init__(self, cfg: PipelineConfig, preview_fps: float = 25.0) -> None:
        super().__init__()
        self.cfg = cfg
        self.pipe: Optional[PipelineManager] = None
        self._vis = Visualizer(show=False)
        self._preview_period = 1.0 / preview_fps if preview_fps > 0 else 0.0
        self._last_preview = 0.0
        self._last_stats = 0.0
        self._counts: Dict[str, int] = {}

    # --- pipeline callback'lari (fon thread'ida chaqiriladi) ---
    def _on_frame(self, frame: np.ndarray, dets, is_detection: bool) -> None:
        now = time.monotonic()
        if is_detection:
            self._counts = {}
            for d in dets:
                self._counts[d.label] = self._counts.get(d.label, 0) + 1

        if self._preview_period and (now - self._last_preview) >= self._preview_period:
            self._last_preview = now
            # Kadr StreamHandler slotida qayta ishlatiladi -> NUSXA majburiy.
            canvas = frame.copy()
            self._vis.draw(canvas, dets, stale=not is_detection)
            self.frameReady.emit(canvas)

        if (now - self._last_stats) >= 0.5:
            self._last_stats = now
            self._emit_stats()

    def _emit_stats(self) -> None:
        p = self.pipe
        if p is None:
            return
        snap = p.monitor.sample(p.fps, p.avg_infer_ms)
        st = p.stream.stats
        self.statsReady.emit(Stats(
            fps=p.fps, infer_ms=p.avg_infer_ms,
            cpu=snap.cpu_percent, ram=snap.rss_mb,
            read=st.read, dropped=st.dropped, reconnects=st.reconnects,
            connected=st.connected, frames=p.frames_processed,
            detections=p.detections_run, counts=dict(self._counts),
        ))

    # --- QThread ---
    def run(self) -> None:
        try:
            self.pipe = PipelineManager(self.cfg, on_frame=self._on_frame)
            self.started_ok.emit()
            self.pipe.run()
        except FileNotFoundError as exc:
            self.failed.emit(
                f"{exc}\n\nModelni eksport qiling:\n"
                "python export_model.py --model yolov8n.pt --format onnx --imgsz 640")
        except Exception as exc:  # noqa: BLE001 - GUI ga to'liq xabar kerak
            self.failed.emit(f"{type(exc).__name__}: {exc}")

    def stop(self) -> None:
        if self.pipe is not None:
            self.pipe.stop()


# ============================================================== asosiy oyna
class MainWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(1440, 880)
        self.setMinimumSize(1100, 700)

        self.worker: Optional[PipelineWorker] = None
        self.classes: List[int] = []
        self._last_frame: Optional[np.ndarray] = None
        self._t_start = 0.0

        self._build_ui()
        self._install_logging()
        self._load_presets()
        self._check_model()

        self._uptime = QTimer(self)
        self._uptime.timeout.connect(self._tick)
        self._uptime.start(1000)

    # ------------------------------------------------------------ UI qurish
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 10)
        root.setSpacing(10)
        root.addLayout(self._build_header())

        split = QSplitter(Qt.Orientation.Horizontal)
        split.addWidget(self._build_sidebar())
        split.addWidget(self._build_center())
        split.addWidget(self._build_right())
        split.setStretchFactor(0, 0)
        split.setStretchFactor(1, 1)
        split.setStretchFactor(2, 0)
        split.setSizes([340, 760, 330])
        root.addWidget(split, 1)
        root.addWidget(self._build_statusbar())

    def _build_header(self) -> QHBoxLayout:
        row = QHBoxLayout()
        title = QLabel(f"◉  {APP_NAME}")
        title.setObjectName("h1")
        sub = QLabel("IP kamera · real-time obyekt deteksiyasi")
        sub.setObjectName("hint")

        col = QVBoxLayout()
        col.setSpacing(0)
        col.addWidget(title)
        col.addWidget(sub)
        row.addLayout(col)
        row.addStretch(1)

        self.btn_start = QPushButton("▶  BOSHLASH")
        self.btn_start.setObjectName("primary")
        self.btn_start.setMinimumWidth(150)
        self.btn_start.clicked.connect(self.start_pipeline)

        self.btn_stop = QPushButton("■  TO'XTATISH")
        self.btn_stop.setObjectName("danger")
        self.btn_stop.setMinimumWidth(150)
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self.stop_pipeline)

        self.btn_snap = QPushButton("⛶  Snapshot")
        self.btn_snap.setEnabled(False)
        self.btn_snap.clicked.connect(self.save_snapshot)

        for b in (self.btn_snap, self.btn_start, self.btn_stop):
            row.addWidget(b)
        return row

    def _build_sidebar(self) -> QWidget:
        area = QScrollArea()
        area.setWidgetResizable(True)
        area.setFrameShape(QFrame.Shape.NoFrame)
        host = QWidget()
        lay = QVBoxLayout(host)
        lay.setContentsMargins(0, 0, 8, 0)
        lay.setSpacing(10)

        # --- profillar ---
        g = QGroupBox("PROFIL")
        gl = QHBoxLayout(g)
        self.cmb_preset = QComboBox()
        self.cmb_preset.setEditable(False)
        self.cmb_preset.currentTextChanged.connect(self._apply_preset)
        b_save = QPushButton("💾")
        b_save.setFixedWidth(38)
        b_save.setToolTip("Joriy sozlamalarni profil sifatida saqlash")
        b_save.clicked.connect(self._save_preset)
        b_del = QPushButton("✕")
        b_del.setFixedWidth(38)
        b_del.setToolTip("Profilni o'chirish")
        b_del.clicked.connect(self._delete_preset)
        gl.addWidget(self.cmb_preset, 1)
        gl.addWidget(b_save)
        gl.addWidget(b_del)
        lay.addWidget(g)

        # --- manba ---
        g = QGroupBox("VIDEO MANBA")
        gl = QGridLayout(g)
        gl.setVerticalSpacing(8)
        r = 0
        self.ed_url = QLineEdit()
        self.ed_url.setPlaceholderText("rtsp://admin:parol@192.168.1.10:554/…")
        # uzun yo'l maydonga sig'maydi -> to'liq matn tooltipda ko'rinadi
        self.ed_url.textChanged.connect(lambda s: self.ed_url.setToolTip(s))
        b_file = QPushButton("📁")
        b_file.setFixedWidth(38)
        b_file.setToolTip("Video fayl tanlash (sinov uchun)")
        b_file.clicked.connect(self._pick_video)
        gl.addWidget(QLabel("URL / fayl"), r, 0)
        h = QHBoxLayout()
        h.addWidget(self.ed_url, 1)
        h.addWidget(b_file)
        gl.addLayout(h, r, 1)
        r += 1

        self.btn_discover = QPushButton("🔍  Tarmoqdan kamera qidirish")
        self.btn_discover.setToolTip(
            "ONVIF va port skaneri orqali lokal tarmoqdagi kameralarni topadi — "
            "keyin faqat login/parol kiritish kifoya")
        self.btn_discover.clicked.connect(self.open_discovery)
        gl.addWidget(self.btn_discover, r, 0, 1, 2)
        r += 1

        self.cmb_sbackend = QComboBox()
        # PyAV o'rnatilmagan bo'lsa buni YASHIRMAYMIZ — foydalanuvchi nega
        # opencv ishlayotganini va uni qanday tuzatishni bilishi kerak.
        self.cmb_sbackend.addItems([
            "av (PyAV — tavsiya)" if _HAS_AV else "av (o'rnatilmagan!)",
            "opencv",
        ])
        if not _HAS_AV:
            self.cmb_sbackend.setCurrentText("opencv")
            self.cmb_sbackend.setToolTip(
                "PyAV o'rnatilmagan. RTSP uchun tavsiya etiladi:\n"
                "    pip install av\n"
                "Hozircha OpenCV backend ishlatiladi.")
        gl.addWidget(QLabel("Dekod backend"), r, 0)
        gl.addWidget(self.cmb_sbackend, r, 1)
        r += 1

        self.cmb_transport = QComboBox()
        self.cmb_transport.addItems(["tcp", "udp"])
        gl.addWidget(QLabel("RTSP transport"), r, 0)
        gl.addWidget(self.cmb_transport, r, 1)
        r += 1

        self.cmb_resize = QComboBox()
        self.cmb_resize.addItems(["O'zgarishsiz", "1280x720", "960x540", "640x360"])
        self.cmb_resize.setCurrentText("960x540")
        gl.addWidget(QLabel("Kadrni kichraytirish"), r, 0)
        gl.addWidget(self.cmb_resize, r, 1)
        r += 1

        self.sp_readevery = QSpinBox()
        self.sp_readevery.setRange(1, 10)
        gl.addWidget(QLabel("Har N-kadrni o'qish"), r, 0)
        gl.addWidget(self.sp_readevery, r, 1)
        r += 1

        self.cmb_hwaccel = QComboBox()
        self.cmb_hwaccel.addItems(["yo'q (CPU)", "cuda", "qsv", "d3d11va", "vaapi"])
        gl.addWidget(QLabel("Apparat dekod"), r, 0)
        gl.addWidget(self.cmb_hwaccel, r, 1)
        r += 1

        self.sp_timeout = QDoubleSpinBox()
        self.sp_timeout.setRange(1.0, 60.0)
        self.sp_timeout.setValue(8.0)
        self.sp_timeout.setSuffix("  s")
        gl.addWidget(QLabel("Ulanish timeout"), r, 0)
        gl.addWidget(self.sp_timeout, r, 1)
        r += 1

        self.chk_loop = QCheckBox("Video faylni aylantirish (loop)")
        gl.addWidget(self.chk_loop, r, 0, 1, 2)
        lay.addWidget(g)

        # --- model ---
        g = QGroupBox("MODEL")
        gl = QGridLayout(g)
        gl.setVerticalSpacing(8)
        r = 0
        self.ed_model = QLineEdit(str(ROOT / "models" / "yolov8n_640.onnx"))
        self.ed_model.textChanged.connect(lambda s: self.ed_model.setToolTip(s))
        self.ed_model.setToolTip(self.ed_model.text())
        b_model = QPushButton("📁")
        b_model.setFixedWidth(38)
        b_model.clicked.connect(self._pick_model)
        h = QHBoxLayout()
        h.addWidget(self.ed_model, 1)
        h.addWidget(b_model)
        gl.addWidget(QLabel("Model fayli"), r, 0)
        gl.addLayout(h, r, 1)
        r += 1

        self.cmb_backend = QComboBox()
        self.cmb_backend.addItems(["onnx", "openvino"])
        gl.addWidget(QLabel("Inference backend"), r, 0)
        gl.addWidget(self.cmb_backend, r, 1)
        r += 1

        self.cmb_imgsz = QComboBox()
        self.cmb_imgsz.addItems(["640", "416", "320"])
        gl.addWidget(QLabel("Kirish o'lchami"), r, 0)
        gl.addWidget(self.cmb_imgsz, r, 1)
        r += 1

        self.sp_conf = QDoubleSpinBox()
        self.sp_conf.setRange(0.05, 0.95)
        self.sp_conf.setSingleStep(0.05)
        self.sp_conf.setValue(0.35)
        gl.addWidget(QLabel("Ishonch chegarasi"), r, 0)
        gl.addWidget(self.sp_conf, r, 1)
        r += 1

        self.sp_iou = QDoubleSpinBox()
        self.sp_iou.setRange(0.1, 0.9)
        self.sp_iou.setSingleStep(0.05)
        self.sp_iou.setValue(0.45)
        gl.addWidget(QLabel("NMS IoU"), r, 0)
        gl.addWidget(self.sp_iou, r, 1)
        r += 1

        self.sp_threads = QSpinBox()
        self.sp_threads.setRange(1, 16)
        self.sp_threads.setValue(2)
        gl.addWidget(QLabel("Inference thread"), r, 0)
        gl.addWidget(self.sp_threads, r, 1)
        r += 1

        self.btn_classes = QPushButton("Barcha sinflar (80)")
        self.btn_classes.clicked.connect(self._pick_classes)
        gl.addWidget(QLabel("Qidiriladigan sinflar"), r, 0)
        gl.addWidget(self.btn_classes, r, 1)
        lay.addWidget(g)

        # --- pipeline ---
        g = QGroupBox("PIPELINE")
        gl = QGridLayout(g)
        gl.setVerticalSpacing(8)
        r = 0
        self.sp_every = QSpinBox()
        self.sp_every.setRange(1, 30)
        self.sp_every.setValue(3)
        gl.addWidget(QLabel("Har N-kadrda deteksiya"), r, 0)
        gl.addWidget(self.sp_every, r, 1)
        r += 1

        self.cmb_tracker = QComboBox()
        self.cmb_tracker.addItems(["cache (CPU ~0)", "light (MOSSE/KCF)", "none"])
        gl.addWidget(QLabel("Oraliq kadrlar"), r, 0)
        gl.addWidget(self.cmb_tracker, r, 1)
        r += 1

        self.sp_target = QDoubleSpinBox()
        self.sp_target.setRange(0.0, 60.0)
        self.sp_target.setValue(15.0)
        self.sp_target.setSpecialValueText("cheklanmagan")
        self.sp_target.setSuffix("  FPS")
        gl.addWidget(QLabel("FPS cheklovi"), r, 0)
        gl.addWidget(self.sp_target, r, 1)
        r += 1

        self.chk_events = QCheckBox("Deteksiyalarni JSONL ga yozish")
        self.chk_events.setChecked(True)
        gl.addWidget(self.chk_events, r, 0, 1, 2)
        r += 1
        self.sp_preview = QSpinBox()
        self.sp_preview.setRange(1, 30)
        self.sp_preview.setValue(20)
        self.sp_preview.setSuffix("  FPS")
        self.sp_preview.setToolTip("Preview tezligi — pastroq qiymat GUI CPU sarfini kamaytiradi")
        gl.addWidget(QLabel("Preview tezligi"), r, 0)
        gl.addWidget(self.sp_preview, r, 1)
        lay.addWidget(g)

        lay.addStretch(1)
        area.setWidget(host)
        area.setMinimumWidth(320)
        return area

    def _build_center(self) -> QWidget:
        host = QWidget()
        lay = QVBoxLayout(host)
        lay.setContentsMargins(4, 0, 4, 0)
        lay.setSpacing(8)

        self.banner = QLabel()
        self.banner.setObjectName("banner")
        self.banner.setWordWrap(True)
        self.banner.hide()
        lay.addWidget(self.banner)

        self.video = VideoView()
        lay.addWidget(self.video, 1)

        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(2000)
        self.log.setMinimumHeight(130)
        self.log.setMaximumHeight(210)
        lay.addWidget(self.log)
        return host

    def _build_right(self) -> QWidget:
        host = QWidget()
        lay = QVBoxLayout(host)
        lay.setContentsMargins(8, 0, 0, 0)
        lay.setSpacing(10)

        grid = QGridLayout()
        grid.setSpacing(8)
        self.card_fps = StatCard("FPS", "kadr/s", C["accent"])
        self.card_infer = StatCard("Inference", "ms", C["accent2"])
        self.card_cpu = StatCard("CPU", "%", C["warn"])
        self.card_ram = StatCard("RAM", "MB", "#a78bfa")
        grid.addWidget(self.card_fps, 0, 0)
        grid.addWidget(self.card_infer, 0, 1)
        grid.addWidget(self.card_cpu, 1, 0)
        grid.addWidget(self.card_ram, 1, 1)
        lay.addLayout(grid)

        g = QGroupBox("OQIM HOLATI")
        gl = QGridLayout(g)
        self.lbl_read = QLabel("0")
        self.lbl_drop = QLabel("0")
        self.lbl_recon = QLabel("0")
        self.lbl_det = QLabel("0")
        for i, (name, w) in enumerate((
            ("O'qilgan kadr", self.lbl_read),
            ("Tashlangan", self.lbl_drop),
            ("Qayta ulanish", self.lbl_recon),
            ("Deteksiya soni", self.lbl_det),
        )):
            cap = QLabel(name)
            cap.setObjectName("hint")
            gl.addWidget(cap, i, 0)
            w.setStyleSheet("font-weight:600;")
            gl.addWidget(w, i, 1, alignment=Qt.AlignmentFlag.AlignRight)
        lay.addWidget(g)

        g = QGroupBox("ANIQLANGAN OBYEKTLAR")
        gl = QVBoxLayout(g)
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Sinf", "Soni"])
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        gl.addWidget(self.table)
        lay.addWidget(g, 1)
        return host

    def _build_statusbar(self) -> QWidget:
        bar = QFrame()
        bar.setObjectName("statusbar")
        bar.setStyleSheet(
            f"QFrame#statusbar {{ background:{C['panel']}; border:1px solid"
            f" {C['border']}; border-radius:8px; }}")
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(12, 6, 12, 6)
        self.lbl_state = QLabel("●  To'xtatilgan")
        self.lbl_state.setStyleSheet(f"color:{C['muted']}; border:none;")
        self.lbl_uptime = QLabel("")
        self.lbl_uptime.setObjectName("hint")
        self.lbl_res = QLabel("")
        self.lbl_res.setObjectName("hint")
        lay.addWidget(self.lbl_state)
        lay.addStretch(1)
        lay.addWidget(self.lbl_res)
        lay.addSpacing(16)
        lay.addWidget(self.lbl_uptime)
        return bar

    # ------------------------------------------------------------- logging
    def _install_logging(self) -> None:
        self.bridge = QtLogBridge()
        self.bridge.message.connect(self._append_log)
        root = logging.getLogger()
        root.setLevel(logging.INFO)
        root.addHandler(self.bridge)

    def _append_log(self, text: str, level: int) -> None:
        color = {logging.WARNING: C["warn"], logging.ERROR: C["danger"],
                 logging.CRITICAL: C["danger"]}.get(level, C["muted"])
        self.log.appendHtml(
            f'<span style="color:{color}">{text}</span>')

    # ------------------------------------------------------------- config
    def _resize_tuple(self):
        t = self.cmb_resize.currentText()
        if "x" not in t:
            return None
        w, h = t.split("x")
        return int(w), int(h)

    def build_config(self) -> PipelineConfig:
        url = self.ed_url.text().strip()
        backend = self.cmb_sbackend.currentText().split()[0]
        if backend == "av" and not _HAS_AV:
            backend = "opencv"          # StreamHandler ham buni tekshiradi
        if url.isdigit():
            url = int(url)  # webcam
            backend = "opencv"  # PyAV int indeksni qabul qilmaydi
        hw = self.cmb_hwaccel.currentText()
        events = str(ROOT / "out" / "events.jsonl") if self.chk_events.isChecked() else None
        if events:
            os.makedirs(os.path.dirname(events), exist_ok=True)

        return PipelineConfig(
            stream=StreamConfig(
                url=url,
                backend=backend,
                rtsp_transport=self.cmb_transport.currentText(),
                timeout_sec=self.sp_timeout.value(),
                hwaccel=None if hw.startswith("yo'q") else hw,
                resize_to=self._resize_tuple(),
                read_every=self.sp_readevery.value(),
                loop_source=self.chk_loop.isChecked(),
            ),
            detector=DetectorConfig(
                model_path=self.ed_model.text().strip(),
                backend=self.cmb_backend.currentText(),
                imgsz=int(self.cmb_imgsz.currentText()),
                conf_threshold=self.sp_conf.value(),
                iou_threshold=self.sp_iou.value(),
                class_filter=self.classes or None,
                num_threads=self.sp_threads.value(),
            ),
            detect_every=self.sp_every.value(),
            tracker=self.cmb_tracker.currentText().split()[0],
            show=False,                       # preview'ni GUI o'zi chizadi
            target_fps=self.sp_target.value(),
            stats_interval=0.0,               # statistikani GUI so'raydi
            events_path=events,
        )

    # ------------------------------------------------------------- actions
    def start_pipeline(self) -> None:
        if not self.ed_url.text().strip():
            QMessageBox.warning(self, APP_NAME,
                                "Video manba (URL yoki fayl) ko'rsatilmagan.")
            return
        model = self.ed_model.text().strip()
        if not os.path.exists(model):
            QMessageBox.critical(
                self, APP_NAME,
                f"Model topilmadi:\n{model}\n\nAvval modelni eksport qiling:\n"
                "python export_model.py --model yolov8n.pt --format onnx --imgsz 640")
            return

        self.log.clear()
        self._reset_stats()
        if not _HAS_AV and self.ed_url.text().strip().lower().startswith("rtsp"):
            logging.getLogger("gui").warning(
                "PyAV o'rnatilmagan — OpenCV backend ishlatiladi. RTSP uchun "
                "«pip install av» tavsiya etiladi (aniqroq timeout, past kechikish).")
        try:
            cfg = self.build_config()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, APP_NAME, f"Sozlamalarda xato:\n{exc}")
            return

        self.worker = PipelineWorker(cfg, preview_fps=self.sp_preview.value())
        self.worker.frameReady.connect(self._on_frame)
        self.worker.statsReady.connect(self._on_stats)
        self.worker.failed.connect(self._on_failed)
        self.worker.finished.connect(self._on_finished)
        self.worker.start()

        self._t_start = time.monotonic()
        self._set_running(True)
        self.video.clear("Ulanmoqda…")

    def stop_pipeline(self) -> None:
        if self.worker is not None:
            self.btn_stop.setEnabled(False)
            self.lbl_state.setText("●  To'xtatilmoqda…")
            self.worker.stop()

    def save_snapshot(self) -> None:
        if self._last_frame is None:
            return
        import cv2

        SNAP_DIR.mkdir(parents=True, exist_ok=True)
        path = SNAP_DIR / f"snap_{time.strftime('%Y%m%d_%H%M%S')}.jpg"
        cv2.imwrite(str(path), self._last_frame)
        logging.getLogger("gui").info("Snapshot saqlandi: %s", path)

    # -------------------------------------------------------------- slots
    def _on_frame(self, frame: np.ndarray) -> None:
        self._last_frame = frame
        h, w = frame.shape[:2]
        # Format_BGR888 -> cv2 kadrini konvertatsiyasiz ko'rsatish
        img = QImage(frame.data, w, h, frame.strides[0], QImage.Format.Format_BGR888)
        self.video.set_frame(img.copy())   # copy: numpy buferi qayta ishlatiladi
        self.lbl_res.setText(f"{w}×{h}")
        if not self.btn_snap.isEnabled():
            self.btn_snap.setEnabled(True)

    def _on_stats(self, s: Stats) -> None:
        self.card_fps.set_value(f"{s.fps:.1f}", s.fps)
        self.card_infer.set_value(f"{s.infer_ms:.0f}", s.infer_ms)
        self.card_cpu.set_value(f"{s.cpu:.0f}", s.cpu)
        self.card_ram.set_value(f"{s.ram:.0f}", s.ram)
        self.lbl_read.setText(f"{s.read:,}".replace(",", " "))
        self.lbl_drop.setText(f"{s.dropped:,}".replace(",", " "))
        self.lbl_recon.setText(str(s.reconnects))
        self.lbl_det.setText(str(s.detections))

        color = C["accent"] if s.connected else C["warn"]
        text = "Ulangan" if s.connected else "Qayta ulanmoqda…"
        self.lbl_state.setText(f"●  {text}")
        self.lbl_state.setStyleSheet(f"color:{color}; border:none;")

        counts = s.counts or {}
        self.table.setRowCount(len(counts))
        for i, (label, n) in enumerate(sorted(counts.items(), key=lambda kv: -kv[1])):
            self.table.setItem(i, 0, QTableWidgetItem(label))
            it = QTableWidgetItem(str(n))
            it.setTextAlignment(Qt.AlignmentFlag.AlignRight |
                                Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(i, 1, it)

    def _on_failed(self, message: str) -> None:
        QMessageBox.critical(self, APP_NAME, message)

    def _on_finished(self) -> None:
        self._set_running(False)
        self.video.clear("Oqim to'xtatildi")
        self.lbl_state.setText("●  To'xtatilgan")
        self.lbl_state.setStyleSheet(f"color:{C['muted']}; border:none;")
        if self.worker and self.worker.pipe:
            p = self.worker.pipe
            logging.getLogger("gui").info(
                "Yakun: %d kadr, %d deteksiya, o'rtacha %.1f FPS, peak RAM %.0f MB",
                p.frames_processed, p.detections_run, p.avg_fps,
                p.monitor.peak_rss_mb)
        self.worker = None

    def _tick(self) -> None:
        if self.worker is not None and self._t_start:
            t = int(time.monotonic() - self._t_start)
            self.lbl_uptime.setText(f"⏱  {t // 3600:02d}:{t % 3600 // 60:02d}:{t % 60:02d}")

    def _set_running(self, on: bool) -> None:
        self.btn_start.setEnabled(not on)
        self.btn_stop.setEnabled(on)
        if not on:
            self.btn_snap.setEnabled(self._last_frame is not None)

    def _reset_stats(self) -> None:
        for c in (self.card_fps, self.card_infer, self.card_cpu, self.card_ram):
            c.reset()
        self.table.setRowCount(0)
        for lbl in (self.lbl_read, self.lbl_drop, self.lbl_recon, self.lbl_det):
            lbl.setText("0")

    # ------------------------------------------------------------ helperlar
    def open_discovery(self) -> None:
        """«Kameralarni qidirish» oynasini ochadi va URL ni qabul qiladi."""
        from gui_discovery import DiscoveryDialog

        dlg = DiscoveryDialog(self, colors=C)
        if dlg.exec() and dlg.selected_url:
            self.ed_url.setText(dlg.selected_url)
            # Topilgan kamera - jonli RTSP oqim: mos sozlamalarni qo'yamiz
            self.cmb_sbackend.setCurrentText("av (PyAV — tavsiya)")
            self.cmb_transport.setCurrentText("tcp")
            self.chk_loop.setChecked(False)
            logging.getLogger("gui").info("Kamera tanlandi: %s",
                                          _mask_url(dlg.selected_url))

    def _pick_video(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Video fayl", str(ROOT),
            "Video (*.mp4 *.avi *.mkv *.mov);; Rasm (*.jpg *.png);; Hamma (*.*)")
        if path:
            self.ed_url.setText(path)

    def _pick_model(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Model fayli", str(ROOT / "models"),
            "Model (*.onnx *.xml);; Hamma (*.*)")
        if path:
            self.ed_model.setText(path)
            self._check_model()

    def _pick_classes(self) -> None:
        dlg = ClassDialog(self.classes, self)
        if dlg.exec():
            self.classes = dlg.selected()
            n = len(self.classes)
            if n == 0 or n == len(COCO_CLASSES):
                self.classes = []
                self.btn_classes.setText(f"Barcha sinflar ({len(COCO_CLASSES)})")
            elif n <= 3:
                self.btn_classes.setText(
                    ", ".join(COCO_CLASSES[i] for i in self.classes))
            else:
                self.btn_classes.setText(f"{n} ta sinf tanlandi")

    def _check_model(self) -> None:
        path = self.ed_model.text().strip()
        if os.path.exists(path):
            self.banner.hide()
            return
        self.banner.setText(
            "⚠  Model topilmadi. Eksport qiling (bir marta):\n"
            "python -m venv .venv_export  →  .venv_export/Scripts/pip install "
            "ultralytics onnx onnxslim  →  .venv_export/Scripts/python "
            "export_model.py --model yolov8n.pt --format onnx --imgsz 640")
        self.banner.show()

    # -------------------------------------------------------------- preset
    def _collect(self) -> dict:
        return {
            "url": self.ed_url.text(), "sbackend": self.cmb_sbackend.currentText(),
            "transport": self.cmb_transport.currentText(),
            "resize": self.cmb_resize.currentText(),
            "read_every": self.sp_readevery.value(),
            "hwaccel": self.cmb_hwaccel.currentText(),
            "timeout": self.sp_timeout.value(), "loop": self.chk_loop.isChecked(),
            "model": self.ed_model.text(), "backend": self.cmb_backend.currentText(),
            "imgsz": self.cmb_imgsz.currentText(), "conf": self.sp_conf.value(),
            "iou": self.sp_iou.value(), "threads": self.sp_threads.value(),
            "classes": self.classes, "every": self.sp_every.value(),
            "tracker": self.cmb_tracker.currentText(),
            "target": self.sp_target.value(), "events": self.chk_events.isChecked(),
            "preview": self.sp_preview.value(),
        }

    def _apply(self, d: dict) -> None:
        self.ed_url.setText(d.get("url", ""))
        self.cmb_sbackend.setCurrentText(d.get("sbackend", "av (PyAV — tavsiya)"))
        self.cmb_transport.setCurrentText(d.get("transport", "tcp"))
        self.cmb_resize.setCurrentText(d.get("resize", "960x540"))
        self.sp_readevery.setValue(d.get("read_every", 1))
        self.cmb_hwaccel.setCurrentText(d.get("hwaccel", "yo'q (CPU)"))
        self.sp_timeout.setValue(d.get("timeout", 8.0))
        self.chk_loop.setChecked(d.get("loop", False))
        self.ed_model.setText(d.get("model", ""))
        self.cmb_backend.setCurrentText(d.get("backend", "onnx"))
        self.cmb_imgsz.setCurrentText(str(d.get("imgsz", "640")))
        self.sp_conf.setValue(d.get("conf", 0.35))
        self.sp_iou.setValue(d.get("iou", 0.45))
        self.sp_threads.setValue(d.get("threads", 2))
        self.classes = list(d.get("classes", []))
        self.sp_every.setValue(d.get("every", 3))
        self.cmb_tracker.setCurrentText(d.get("tracker", "cache (CPU ~0)"))
        self.sp_target.setValue(d.get("target", 15.0))
        self.chk_events.setChecked(d.get("events", True))
        self.sp_preview.setValue(d.get("preview", 20))
        n = len(self.classes)
        self.btn_classes.setText(
            f"Barcha sinflar ({len(COCO_CLASSES)})" if n == 0
            else (", ".join(COCO_CLASSES[i] for i in self.classes) if n <= 3
                  else f"{n} ta sinf tanlandi"))
        self._check_model()

    def _load_presets(self) -> None:
        self.presets: Dict[str, dict] = {}
        if PRESETS_FILE.exists():
            try:
                self.presets = json.loads(PRESETS_FILE.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                logging.getLogger("gui").warning("Profillar fayli o'qilmadi")
        self.cmb_preset.blockSignals(True)
        self.cmb_preset.clear()
        self.cmb_preset.addItem("— profil tanlanmagan —")
        self.cmb_preset.addItems(sorted(self.presets))
        self.cmb_preset.blockSignals(False)

    def _apply_preset(self, name: str) -> None:
        if name in self.presets:
            self._apply(self.presets[name])

    def _save_preset(self) -> None:
        name, ok = QInputDialog.getText(self, "Profil", "Profil nomi:")
        if not ok or not name.strip():
            return
        # RTSP URL ichida parol bo'lishi mumkin — profil oddiy JSON faylga
        # ochiq matnda yoziladi, foydalanuvchi buni bilishi shart.
        if re.search(r"rtsp://[^:/@]+:[^@]+@", self.ed_url.text()):
            answer = QMessageBox.warning(
                self, APP_NAME,
                "URL ichida kamera paroli bor. Profil oddiy matnli faylga "
                f"({PRESETS_FILE.name}) shifrlanmagan holda saqlanadi.\n\n"
                "Davom etilsinmi?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No)
            if answer != QMessageBox.StandardButton.Yes:
                return
        self.presets[name.strip()] = self._collect()
        PRESETS_FILE.write_text(json.dumps(self.presets, ensure_ascii=False,
                                           indent=2), encoding="utf-8")
        self._load_presets()
        self.cmb_preset.setCurrentText(name.strip())

    def _delete_preset(self) -> None:
        name = self.cmb_preset.currentText()
        if name in self.presets:
            del self.presets[name]
            PRESETS_FILE.write_text(json.dumps(self.presets, ensure_ascii=False,
                                               indent=2), encoding="utf-8")
            self._load_presets()

    # -------------------------------------------------------------- yopish
    def closeEvent(self, ev) -> None:
        if self.worker is not None:
            self.worker.stop()
            self.worker.wait(4000)
        logging.getLogger().removeHandler(self.bridge)
        self.bridge.close()
        ev.accept()


def build_app() -> QApplication:
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setStyle("Fusion")
    app.setStyleSheet(QSS)
    return app


def main() -> int:
    app = build_app()
    win = MainWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
