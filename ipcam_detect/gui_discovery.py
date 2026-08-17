"""gui_discovery.py — «Kameralarni qidirish» oynasi (PyQt6).

Foydalanuvchi uchun oqim:
  1. «Qidirish» — ONVIF WS-Discovery + tarmoq skaneri fon thread'ida ishlaydi.
  2. Jadvalda topilgan qurilmalar chiqadi (IP, nomi, portlar, manba).
  3. Kamerani tanlab, faqat **login va parol** kiritiladi.
  4. «Ulanishni tekshirish» — ONVIF `GetStreamUri`, bo'lmasa 19 ta vendor
     shabloni avtomatik sinaladi va ishlaydigan RTSP URL topiladi.
  5. «Tanlash» — URL asosiy oynaga o'tadi.

Barcha tarmoq amallari `QThread` da: interfeys hech qachon muzlamaydi.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ipcam_detect import discovery as D

logger = logging.getLogger(__name__)


# ================================================================ threadlar
class DiscoverThread(QThread):
    """Tarmoqni skanerlaydi (ONVIF + portlar)."""

    progress = pyqtSignal(str, float)
    finishedWith = pyqtSignal(object)      # List[Camera]

    def __init__(self, use_onvif: bool, subnets: Optional[List[str]],
                 ports, onvif_timeout: float) -> None:
        super().__init__()
        self.use_onvif = use_onvif
        self.subnets = subnets
        self.ports = ports
        self.onvif_timeout = onvif_timeout
        self._stop = False

    def run(self) -> None:
        try:
            cams = D.discover(
                use_onvif=self.use_onvif,
                subnets=self.subnets,
                ports=self.ports,
                onvif_timeout=self.onvif_timeout,
                progress=lambda t, p: self.progress.emit(t, p),
                stop_flag=lambda: self._stop,
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Qidiruv xatosi")
            self.progress.emit(f"Xato: {exc}", 1.0)
            cams = []
        self.finishedWith.emit(cams)

    def stop(self) -> None:
        self._stop = True


class VerifyThread(QThread):
    """Bitta kamera uchun login/parol bilan RTSP URL ni topadi."""

    progress = pyqtSignal(str, float)
    finishedWith = pyqtSignal(object)      # Camera

    def __init__(self, cam: D.Camera, user: str, password: str,
                 channel: int = 1) -> None:
        super().__init__()
        self.cam = cam
        self.user = user
        self.password = password
        self.channel = channel
        self._stop = False

    def run(self) -> None:
        try:
            cam = D.find_stream_url(
                self.cam, self.user, self.password, channel=self.channel,
                progress=lambda t, p: self.progress.emit(t, p),
                stop_flag=lambda: self._stop,
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Tekshirish xatosi")
            self.cam.note = f"Xato: {exc}"
            cam = self.cam
        self.finishedWith.emit(cam)

    def stop(self) -> None:
        self._stop = True


# =================================================================== oyna
class DiscoveryDialog(QDialog):
    """Kameralarni topish va ulanish ma'lumotlarini kiritish oynasi."""

    COLUMNS = ("IP manzil", "Qurilma", "Portlar", "Topilish usuli", "Holat")

    def __init__(self, parent=None, colors: Optional[dict] = None) -> None:
        super().__init__(parent)
        self.C = colors or {}
        self.setWindowTitle("Tarmoqdagi kameralarni qidirish")
        self.resize(940, 640)

        self.cameras: List[D.Camera] = []
        self.selected_url: str = ""
        self.discover_thread: Optional[DiscoverThread] = None
        self.verify_thread: Optional[VerifyThread] = None

        self._build()
        self._fill_subnets()

    # ------------------------------------------------------------- qurilish
    def _build(self) -> None:
        lay = QVBoxLayout(self)
        lay.setSpacing(10)

        head = QLabel("Tarmoqdagi IP kameralarni avtomatik topish")
        head.setStyleSheet("font-size:15px; font-weight:700;")
        hint = QLabel(
            "ONVIF qurilmalari o'zini e'lon qiladi; qolganlari port skaneri "
            "bilan topiladi. Keyin faqat login va parol kiriting — RTSP "
            "manzilini dastur o'zi aniqlaydi.")
        hint.setWordWrap(True)
        hint.setObjectName("hint")
        lay.addWidget(head)
        lay.addWidget(hint)

        # --- qidiruv sozlamalari ---
        g = QGroupBox("QIDIRUV")
        gl = QGridLayout(g)
        self.chk_onvif = QCheckBox("ONVIF (WS-Discovery)")
        self.chk_onvif.setChecked(True)
        self.chk_onvif.setToolTip("Kameralar o'zini e'lon qiladi — eng tez va aniq usul")
        self.chk_scan = QCheckBox("Tarmoqni portlar bo'yicha skanerlash")
        self.chk_scan.setChecked(True)
        self.chk_scan.setToolTip("ONVIF o'chirilgan yoki eski kameralar uchun")
        gl.addWidget(self.chk_onvif, 0, 0)
        gl.addWidget(self.chk_scan, 0, 1)

        gl.addWidget(QLabel("Tarmoq"), 1, 0)
        self.cmb_subnet = QComboBox()
        self.cmb_subnet.setEditable(True)
        self.cmb_subnet.setToolTip("Masalan: 192.168.1.0/24")
        gl.addWidget(self.cmb_subnet, 1, 1)

        gl.addWidget(QLabel("Portlar"), 2, 0)
        self.ed_ports = QLineEdit(",".join(str(p) for p in D.CAMERA_PORTS))
        self.ed_ports.setToolTip("Vergul bilan ajratilgan portlar ro'yxati")
        gl.addWidget(self.ed_ports, 2, 1)

        self.btn_scan = QPushButton("🔍  QIDIRISH")
        self.btn_scan.setObjectName("primary")
        self.btn_scan.clicked.connect(self.start_discovery)
        self.btn_cancel = QPushButton("To'xtatish")
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self.cancel_discovery)
        row = QHBoxLayout()
        row.addWidget(self.btn_scan)
        row.addWidget(self.btn_cancel)
        row.addStretch(1)
        gl.addLayout(row, 3, 0, 1, 2)
        lay.addWidget(g)

        # --- natijalar jadvali ---
        self.table = QTableWidget(0, len(self.COLUMNS))
        self.table.setHorizontalHeaderLabels(self.COLUMNS)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        for i in (0, 2, 3, 4):
            hh.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        self.table.itemSelectionChanged.connect(self._on_select)
        lay.addWidget(self.table, 1)

        self.bar = QProgressBar()
        self.bar.setTextVisible(True)
        self.bar.setFormat("%p%  —  tayyor")
        lay.addWidget(self.bar)

        # --- ulanish ma'lumotlari ---
        g = QGroupBox("ULANISH MA'LUMOTLARI")
        form = QFormLayout(g)
        self.ed_user = QLineEdit()
        self.ed_user.setPlaceholderText("admin")
        self.ed_pass = QLineEdit()
        self.ed_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self.ed_pass.setPlaceholderText("kamera paroli")
        self.btn_eye = QPushButton("👁")
        self.btn_eye.setFixedWidth(38)
        self.btn_eye.setCheckable(True)
        self.btn_eye.setToolTip("Parolni ko'rsatish")
        self.btn_eye.toggled.connect(
            lambda on: self.ed_pass.setEchoMode(
                QLineEdit.EchoMode.Normal if on else QLineEdit.EchoMode.Password))
        prow = QHBoxLayout()
        prow.addWidget(self.ed_pass, 1)
        prow.addWidget(self.btn_eye)

        self.sp_channel = QSpinBox()
        self.sp_channel.setRange(1, 32)
        self.sp_channel.setToolTip("NVR uchun kanal raqami (oddiy kamerada 1)")

        form.addRow("Login", self.ed_user)
        form.addRow("Parol", self._wrap(prow))
        form.addRow("Kanal (NVR)", self.sp_channel)

        self.btn_verify = QPushButton("🔑  ULANISHNI TEKSHIRISH")
        self.btn_verify.setEnabled(False)
        self.btn_verify.clicked.connect(self.verify_selected)
        form.addRow(self.btn_verify)

        self.lbl_url = QLineEdit()
        self.lbl_url.setReadOnly(True)
        self.lbl_url.setPlaceholderText("topilgan RTSP manzili shu yerda chiqadi")
        form.addRow("RTSP URL", self.lbl_url)
        lay.addWidget(g)

        # --- pastki tugmalar ---
        row = QHBoxLayout()
        self.lbl_status = QLabel("")
        self.lbl_status.setObjectName("hint")
        self.lbl_status.setWordWrap(True)
        row.addWidget(self.lbl_status, 1)
        self.btn_use = QPushButton("✓  TANLASH")
        self.btn_use.setObjectName("primary")
        self.btn_use.setEnabled(False)
        self.btn_use.clicked.connect(self._accept_url)
        b_close = QPushButton("Yopish")
        b_close.clicked.connect(self.reject)
        row.addWidget(self.btn_use)
        row.addWidget(b_close)
        lay.addLayout(row)

    @staticmethod
    def _wrap(layout) -> QWidget:
        w = QWidget()
        layout.setContentsMargins(0, 0, 0, 0)
        w.setLayout(layout)
        return w

    def _fill_subnets(self) -> None:
        nets = D.local_subnets()
        self.cmb_subnet.addItems(nets)
        if nets:
            # Eng ehtimolli tarmoq: 192.168.* (virtual adapterlar emas)
            for n in nets:
                if n.startswith("192.168.") and not n.startswith("192.168.56."):
                    self.cmb_subnet.setCurrentText(n)
                    break

    # -------------------------------------------------------------- qidiruv
    def start_discovery(self) -> None:
        if not self.chk_onvif.isChecked() and not self.chk_scan.isChecked():
            self._status("Kamida bitta qidiruv usulini tanlang.", warn=True)
            return

        try:
            ports = tuple(int(p) for p in self.ed_ports.text().replace(" ", "").split(",") if p)
        except ValueError:
            self._status("Portlar ro'yxati noto'g'ri.", warn=True)
            return

        subnets = [self.cmb_subnet.currentText().strip()] if self.chk_scan.isChecked() else []
        self.table.setRowCount(0)
        self.cameras.clear()
        self.btn_use.setEnabled(False)
        self.lbl_url.clear()
        self._status("Qidirilmoqda…")

        self._reap(self.discover_thread)      # oldingisi tugaganiga ishonch hosil qilamiz
        self.discover_thread = DiscoverThread(
            self.chk_onvif.isChecked(), subnets, ports,
            onvif_timeout=4.0 if self.chk_onvif.isChecked() else 0.0)
        self.discover_thread.progress.connect(self._on_progress)
        self.discover_thread.finishedWith.connect(self._on_found)
        # DIQQAT: havolani QThread.finished da bo'shatamiz. `finishedWith`
        # signal `run()` ichidan kelgani uchun o'sha payt thread hali
        # tugamagan bo'ladi; havolani darhol almashtirsak, PyQt hali ishlab
        # turgan QThread obyektini o'chirib yuboradi (dastur qotib qoladi).
        self.discover_thread.finished.connect(self._discover_done)
        self.discover_thread.start()
        self.btn_scan.setEnabled(False)
        self.btn_cancel.setEnabled(True)

    def cancel_discovery(self) -> None:
        if self.discover_thread:
            self.discover_thread.stop()
            self._status("To'xtatilmoqda…")

    def _on_progress(self, text: str, frac: float) -> None:
        self.bar.setValue(int(frac * 100))
        self.bar.setFormat(f"%p%  —  {text}")

    def _on_found(self, cams: List[D.Camera]) -> None:
        self.cameras = cams
        self.table.setRowCount(len(cams))
        for r, cam in enumerate(cams):
            self._set_row(r, cam)
        self.btn_scan.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        if cams:
            self._status(f"{len(cams)} ta qurilma topildi. Kamerani tanlab, "
                         "login va parolni kiriting.")
            self.table.selectRow(0)
        else:
            self._status(
                "Qurilma topilmadi. Tekshiring: kamera va kompyuter bir "
                "tarmoqdami, tarmoq boshqa (masalan 192.168.0.0/24) emasmi, "
                "Windows Firewall UDP 3702 ni bloklamayaptimi.", warn=True)

    def _set_row(self, r: int, cam: D.Camera) -> None:
        state = {True: "✓ ulanadi", False: "✗ login/parol",
                 None: "— tekshirilmagan"}[cam.auth_ok]
        values = (cam.ip, cam.title,
                  ", ".join(str(p) for p in cam.ports) or "—",
                  "ONVIF" if cam.source == "onvif" else "skaner",
                  state)
        for c, v in enumerate(values):
            item = QTableWidgetItem(v)
            if c == 4 and cam.auth_ok is True:
                item.setForeground(Qt.GlobalColor.green)
            self.table.setItem(r, c, item)

    # ---------------------------------------------------------- tekshirish
    def _current(self) -> Optional[D.Camera]:
        rows = self.table.selectionModel().selectedRows() if self.table.selectionModel() else []
        if not rows:
            return None
        idx = rows[0].row()
        return self.cameras[idx] if 0 <= idx < len(self.cameras) else None

    def _on_select(self) -> None:
        cam = self._current()
        self.btn_verify.setEnabled(cam is not None)
        if cam is None:
            return
        self.lbl_url.setText(cam.rtsp_url)
        self.btn_use.setEnabled(bool(cam.rtsp_url))
        detail = f"{cam.ip} · {cam.title}"
        if cam.onvif_url:
            detail += f" · ONVIF: {cam.onvif_url}"
        self._status(detail)

    def verify_selected(self) -> None:
        cam = self._current()
        if cam is None:
            return
        if not self.ed_user.text().strip():
            self._status("Login kiritilmagan (odatda «admin»).", warn=True)
            return

        self.btn_verify.setEnabled(False)
        self.btn_use.setEnabled(False)
        self.lbl_url.clear()
        self._status(f"{cam.ip} tekshirilmoqda…")
        self._reap(self.verify_thread)
        self.verify_thread = VerifyThread(
            cam, self.ed_user.text().strip(), self.ed_pass.text(),
            self.sp_channel.value())
        self.verify_thread.progress.connect(self._on_progress)
        self.verify_thread.finishedWith.connect(self._on_verified)
        self.verify_thread.finished.connect(self._verify_done)
        self.verify_thread.start()

    def _on_verified(self, cam: D.Camera) -> None:
        self.btn_verify.setEnabled(True)
        for r, c in enumerate(self.cameras):
            if c.ip == cam.ip:
                self._set_row(r, cam)
                break
        if cam.rtsp_url:
            self.lbl_url.setText(cam.rtsp_url)
            self.btn_use.setEnabled(True)
            self._status(f"✓ Ulanish muvaffaqiyatli — {cam.rtsp_template}. "
                         "«TANLASH» tugmasini bosing.")
        else:
            self._status(f"✗ {cam.note}", warn=True)

    @staticmethod
    def _reap(thread: Optional[QThread]) -> None:
        """Eski thread'ni to'xtatib, tugashini kutadi (havolani almashtirishdan oldin)."""
        if thread is not None and thread.isRunning():
            if hasattr(thread, "stop"):
                thread.stop()
            thread.wait(5000)

    def _discover_done(self) -> None:
        self.discover_thread = None

    def _verify_done(self) -> None:
        self.verify_thread = None

    def _accept_url(self) -> None:
        self.selected_url = self.lbl_url.text().strip()
        if self.selected_url:
            self.accept()

    def _status(self, text: str, warn: bool = False) -> None:
        color = self.C.get("warn", "#f0b429") if warn else self.C.get("muted", "#8b93a7")
        self.lbl_status.setStyleSheet(f"color:{color};")
        self.lbl_status.setText(text)

    # -------------------------------------------------------------- yopish
    def closeEvent(self, ev) -> None:
        for th in (self.discover_thread, self.verify_thread):
            if th is not None:
                th.stop()
                th.wait(3000)
        ev.accept()
