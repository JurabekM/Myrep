"""Juftlash bilan qo'shilgan qurilma: do'kon ma'lumoti (snapshot) kelguncha kutish.

Juftlashdan keyin lokal bazada foydalanuvchilar yo'q, shuning uchun login mumkin emas. Ma'lumot faqat MQTT
orqali keladi: avval ulanamiz, so'ng snapshot so'raymiz va u kelguncha kutamiz. Login oynasi shu paytgacha
ochilmaydi (`login.run_login(..., bootstrap=...)`).
"""

from typing import Any

from PySide6.QtCore import QObject, QTimer
from PySide6.QtWidgets import QApplication, QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from ..offline.store import LocalStore
from ..sync import ops as o
from .tasks import BackgroundRunner

POLL_INTERVAL_MS = 500
REQUEST_INTERVAL_MS = 15_000
RETRY_INTERVAL_MS = 5_000
HINT_AFTER_MS = 60_000  # shuncha kutilgandan keyin egasi qurilmasini tekshirish eslatmasi chiqadi
DEFAULT_LABEL = "Desktop kassa"


def is_store_ready(local: LocalStore) -> bool:
    """Do'kon holati to'liq: egasi (do'konni yaratgan) yoki egasi snapshot'i orqali."""
    return local.is_bootstrapped()


def _is_approved(local: LocalStore) -> bool:
    row = local.device_row(local.device_id())
    return row is not None and bool(row["active"])


def _app_object() -> QObject:
    """Fon ishi signallari ilova ob'ektiga bog'lanadi: dialog yopilgach ham natija xavfsiz qaytadi."""
    app = QApplication.instance()
    if app is None:
        raise RuntimeError("QApplication yaratilmagan")
    return app


class SnapshotWaitDialog(QDialog):
    def __init__(
        self,
        local: LocalStore,
        mqtt: Any,
        parent: QWidget | None = None,
        *,
        runner: Any | None = None,
        poll_interval_ms: int = POLL_INTERVAL_MS,
        request_interval_ms: int = REQUEST_INTERVAL_MS,
        retry_interval_ms: int = RETRY_INTERVAL_MS,
        label: str = DEFAULT_LABEL,
    ) -> None:
        super().__init__(parent)
        self._label = label
        self.setWindowTitle("OmborAI — do'kon ma'lumoti")
        self.setModal(True)
        self.setMinimumWidth(420)
        self._local = local
        self._mqtt = mqtt
        self._runner = runner or BackgroundRunner(_app_object())
        self._poll_interval_ms = poll_interval_ms
        self._waited_ms = 0

        self.status = QLabel("MQTT'ga ulanmoqda...")
        self.status.setWordWrap(True)
        self.hint = QLabel(
            "Bu qurilmani do'kon egasi qurilmasi tasdiqlashi va do'kon ma'lumotini yuborishi kerak. "
            "Egasi qurilmasi internetga ulangan va OmborAI ochiq turishi kerak."
        )
        self.hint.setWordWrap(True)
        cancel = QPushButton("Bekor qilish")
        cancel.clicked.connect(self.reject)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        buttons.addWidget(cancel)
        layout = QVBoxLayout(self)
        layout.addWidget(self.status)
        layout.addWidget(self.hint)
        layout.addLayout(buttons)

        self._poll = QTimer(self)
        self._poll.setInterval(poll_interval_ms)
        self._poll.timeout.connect(self._check)
        self._request = QTimer(self)
        self._request.setInterval(request_interval_ms)
        self._request.timeout.connect(self._request_snapshot)
        self._retry = QTimer(self)
        self._retry.setSingleShot(True)
        self._retry.setInterval(retry_interval_ms)
        self._retry.timeout.connect(self._connect)
        QTimer.singleShot(0, self._connect)

    def done(self, result: int) -> None:
        for timer in (self._poll, self._request, self._retry):
            timer.stop()
        super().done(result)

    def _connect(self) -> None:
        if self._mqtt.connected:
            self._on_connected(None)
            return
        self.status.setText("MQTT'ga ulanmoqda...")
        self._runner.run(self._attempt, self._on_connected, self._on_connect_failed)

    def _attempt(self) -> None:
        # Avvalgi urinish yarim qolgan bo'lishi mumkin: avval tozalab, so'ng qayta ulanamiz
        self._mqtt.stop()
        self._mqtt.start()

    def _on_connected(self, _result: Any) -> None:
        self.status.setText("Ulandi. Do'kon ma'lumoti so'ralmoqda...")
        if not self._poll.isActive():
            self._poll.start()
            self._request.start()
        self._request_snapshot()

    def _on_connect_failed(self, exc: Exception) -> None:
        self.status.setText(f"MQTT ulanmadi: {exc}. Qayta urinilmoqda...")
        self._retry.start()

    def _request_snapshot(self) -> None:
        store_id = self._local.get_state("store_id")
        if not self._mqtt.connected or not store_id:
            return
        if _is_approved(self._local):
            self.status.setText("Tasdiqlandi. Do'kon ma'lumoti so'ralmoqda...")
            request = self._local.new_op(o.SNAPSHOT_REQUEST, {})
        else:
            self.status.setText("Egasi qurilmasi bu qurilmani tasdiqlashi kutilmoqda...")
            request = self._local.join_request(self._label)
        self._runner.run(lambda: self._mqtt.send(request), lambda _r: None, lambda _e: None)

    def _check(self) -> None:
        if is_store_ready(self._local):
            self.accept()
            return
        self._waited_ms += self._poll_interval_ms
        if self._waited_ms >= HINT_AFTER_MS:
            self.status.setText(
                "Hali tasdiq yoki ma'lumot kelmadi. Egasi qurilmasi yoqilganini, internetga ulanganini "
                "va OmborAI ochiq ekanini tekshiring."
            )


def wait_for_store(
    local: LocalStore,
    mqtt: Any,
    parent: QWidget | None = None,
    *,
    runner: Any | None = None,
    poll_interval_ms: int = POLL_INTERVAL_MS,
    request_interval_ms: int = REQUEST_INTERVAL_MS,
    retry_interval_ms: int = RETRY_INTERVAL_MS,
    label: str = DEFAULT_LABEL,
) -> bool:
    """Egasi tasdig'i va do'kon ma'lumoti kelguncha kutadi. True: tayyor; False: foydalanuvchi bekor qildi."""
    dialog = SnapshotWaitDialog(
        local,
        mqtt,
        parent,
        runner=runner,
        poll_interval_ms=poll_interval_ms,
        request_interval_ms=request_interval_ms,
        retry_interval_ms=retry_interval_ms,
        label=label,
    )
    accepted = dialog.exec() == QDialog.DialogCode.Accepted
    dialog.deleteLater()
    return accepted
