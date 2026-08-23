"""Fon sinxronizatsiyasi — UI'ni bloklamaydigan worker.

PySide6 + SQLite bilan ishlashda qat'iy qoidalar (o'tgan loyihalarda
qimmatga tushgan saboqlar):

1. **Signalni `lambda` ga ulama.** Lambda worker'ga havolani ushlab
   qoladi; obyekt yo'q qilinganda osilgan havola qoladi va ilova
   `0xC0000409` bilan yiqiladi. Faqat bog'langan metod.
2. **`@Slot` dekoratorini tashlab ketma.** Dekoratorsiz metod Qt uchun
   oddiy Python atributi bo'lib qoladi va oqimlararo ulanish noto'g'ri
   navbatga tushadi.
3. **Worker o'zini o'zi to'xtatsin** (`finished` -> `quit`). Tashqaridan
   `terminate()` SQLite tranzaksiyasini yarim yo'lda uzadi.
4. **`_cleanup` da `sender()` ni tekshir.** Eski worker'ning kechikkan
   signali yangi worker holatini o'chirib yubormasin.
5. Har worker **o'z sessiyasini** oladi — SQLAlchemy sessiyasi oqimlar
   orasida bo'lishilmaydi.
"""

from __future__ import annotations

import logging
import traceback
from collections.abc import Callable

from PySide6.QtCore import QObject, QThread, QTimer, Signal, Slot

logger = logging.getLogger(__name__)


class SyncWorker(QObject):
    """Bitta sinxronizatsiya aylanishini fon oqimida bajaradi."""

    #: (yuborilgan, qabul qilingan, navbat, xatolar)
    progressed = Signal(int, int, int, int)
    failed = Signal(str)
    finished = Signal()

    def __init__(self, run_cycle: Callable[[], tuple[int, int, int, int]]) -> None:
        super().__init__()
        self._run_cycle = run_cycle
        self._cancelled = False

    @Slot()
    def cancel(self) -> None:
        self._cancelled = True

    @Slot()
    def run(self) -> None:
        """Ish shu yerda. Istisno HECH QACHON oqimdan tashqariga chiqmaydi."""
        try:
            if not self._cancelled:
                published, received, queued, errors = self._run_cycle()
                if not self._cancelled:
                    self.progressed.emit(published, received, queued, errors)
        except Exception as exc:
            logger.exception("Sinxronizatsiya aylanishi xato bilan tugadi")
            self.failed.emit(f"{type(exc).__name__}: {exc}")
        finally:
            # Worker o'zini o'zi tugatadi — tashqaridan to'xtatilmaydi.
            self.finished.emit()


class SyncController(QObject):
    """Fon sinxronizatsiyasini boshqaradi.

    Bir vaqtda faqat BITTA aylanish ishlaydi. Ikkinchisi so'ralsa —
    o'tkazib yuboriladi, navbatga qo'yilmaydi: eskirgan aylanishlarni
    to'plash foydasiz, keyingi taymer baribir keladi.
    """

    status_changed = Signal(int, int, int, int)
    error_occurred = Signal(str)
    busy_changed = Signal(bool)

    def __init__(
        self,
        run_cycle: Callable[[], tuple[int, int, int, int]],
        *,
        interval_ms: int = 5000,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._run_cycle = run_cycle
        self._thread: QThread | None = None
        self._worker: SyncWorker | None = None

        self._timer = QTimer(self)
        self._timer.setInterval(interval_ms)
        self._timer.timeout.connect(self.trigger)

    @property
    def is_busy(self) -> bool:
        return self._thread is not None

    def start(self) -> None:
        self._timer.start()
        self.trigger()

    def stop(self) -> None:
        self._timer.stop()
        if self._worker is not None:
            self._worker.cancel()
        if self._thread is not None:
            self._thread.quit()
            # Tranzaksiya yakunlanishiga imkon beramiz.
            if not self._thread.wait(5000):
                logger.warning("Fon oqimi 5 soniyada tugamadi")

    @Slot()
    def trigger(self) -> None:
        """Yangi aylanish boshlaydi (agar oldingisi tugagan bo'lsa)."""
        if self._thread is not None:
            return

        thread = QThread()
        worker = SyncWorker(self._run_cycle)
        worker.moveToThread(thread)

        # Faqat bog'langan metodlar — lambda YO'Q (1-qoida).
        thread.started.connect(worker.run)
        worker.progressed.connect(self._on_progress)
        worker.failed.connect(self._on_failed)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(self._cleanup)
        thread.finished.connect(thread.deleteLater)

        self._thread = thread
        self._worker = worker
        self.busy_changed.emit(True)
        thread.start()

    @Slot(int, int, int, int)
    def _on_progress(self, published: int, received: int, queued: int, errors: int) -> None:
        self.status_changed.emit(published, received, queued, errors)

    @Slot(str)
    def _on_failed(self, message: str) -> None:
        self.error_occurred.emit(message)

    @Slot()
    def _cleanup(self) -> None:
        """Oqim tugadi. Eski oqimning kechikkan signalini e'tiborsiz qoldiradi."""
        # 4-qoida: signal JORIY oqimdanmi? Aks holda eski worker yangi
        # holatni o'chirib yuborardi.
        if self.sender() is not self._thread:
            return
        self._thread = None
        self._worker = None
        self.busy_changed.emit(False)


class TaskWorker(QObject):
    """Bir martalik uzoq vazifa (backup, hisobot, snapshot)."""

    completed = Signal(object)
    failed = Signal(str)
    finished = Signal()

    def __init__(self, task: Callable[[], object]) -> None:
        super().__init__()
        self._task = task

    @Slot()
    def run(self) -> None:
        try:
            self.completed.emit(self._task())
        except Exception as exc:
            logger.exception("Fon vazifasi xato bilan tugadi")
            self.failed.emit(f"{type(exc).__name__}: {exc}\n{traceback.format_exc(limit=3)}")
        finally:
            self.finished.emit()


class TaskRunner(QObject):
    """Uzoq vazifani fon oqimida bajaradi va natijani qaytaradi."""

    completed = Signal(object)
    failed = Signal(str)
    busy_changed = Signal(bool)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._thread: QThread | None = None
        self._worker: TaskWorker | None = None

    @property
    def is_busy(self) -> bool:
        return self._thread is not None

    def submit(self, task: Callable[[], object]) -> bool:
        """Vazifani navbatga qo'yadi. Band bo'lsa `False`."""
        if self._thread is not None:
            return False

        thread = QThread()
        worker = TaskWorker(task)
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.completed.connect(self._on_completed)
        worker.failed.connect(self._on_failed)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(self._cleanup)
        thread.finished.connect(thread.deleteLater)

        self._thread = thread
        self._worker = worker
        self.busy_changed.emit(True)
        thread.start()
        return True

    def wait(self, timeout_ms: int = 30000) -> bool:
        if self._thread is None:
            return True
        return self._thread.wait(timeout_ms)

    @Slot(object)
    def _on_completed(self, result: object) -> None:
        self.completed.emit(result)

    @Slot(str)
    def _on_failed(self, message: str) -> None:
        self.failed.emit(message)

    @Slot()
    def _cleanup(self) -> None:
        if self.sender() is not self._thread:
            return
        self._thread = None
        self._worker = None
        self.busy_changed.emit(False)
