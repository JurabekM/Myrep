"""Server holati: `Launcher` amallarini fon oqimida yuritadi, natijani signal bilan beradi.

Holatlar: `checking`, `starting`, `running`, `stopping`, `stopped`, `failed`.
"""

import httpx
import psutil
from PyQt6.QtCore import QObject, QThread, pyqtSignal, pyqtSlot

from srv1_shell.launcher import Launcher, Outcome

TRANSITIONAL = frozenset({"checking", "starting", "stopping"})


class _Worker(QObject):
    """Fon oqimida yashaydi; bir vaqtda bitta amal."""

    progress = pyqtSignal(str)
    finished = pyqtSignal(str, object)

    def __init__(self, launcher: Launcher) -> None:
        super().__init__()
        self._launcher = launcher

    @pyqtSlot(str, str)
    def run(self, operation: str, token: str) -> None:
        report = self.progress.emit
        try:
            if operation == "ensure":
                outcome = self._launcher.ensure(report)
            elif operation == "start":
                outcome = self._launcher.start(report)
            elif operation == "stop":
                outcome = self._launcher.stop(token, report)
            else:
                outcome = self._launcher.check(report)
        except (OSError, httpx.HTTPError, psutil.Error) as exc:
            # Oqim har doim javob berishi shart, aks holda tugma abadiy o'chiq qoladi.
            outcome = Outcome("failed", "launch_error", str(exc))
        self.finished.emit(operation, outcome)


class ServerControl(QObject):
    """`changed` - holat yoki izoh o'zgardi; `ready(token)` - yadro ishlayapti va token o'qildi."""

    changed = pyqtSignal()
    ready = pyqtSignal(str)
    _run = pyqtSignal(str, str)

    def __init__(self, launcher: Launcher, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._launcher = launcher
        self.state = "checking"
        self.reason = ""
        self.detail = ""
        self._busy = False
        self._closed = False
        self._thread = QThread(self)
        self._worker = _Worker(launcher)
        self._worker.moveToThread(self._thread)
        self._run.connect(self._worker.run)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._thread.start()

    @property
    def busy(self) -> bool:
        return self._busy

    @property
    def log_dir(self) -> str:
        return str(self._launcher.launch_log.parent)

    # --- amallar ----------------------------------------------------------------------
    def ensure(self) -> bool:
        """Oyna ochilganda: yadro ishlamayotgan bo'lsa ishga tushiradi."""
        return self._begin("ensure", "checking")

    def start(self) -> bool:
        return self._begin("start", "starting")

    def stop(self, token: str) -> bool:
        return self._begin("stop", "stopping", token)

    def connection_changed(self, connected: bool) -> None:
        """Hodisalar oqimi ulandi yoki uzildi (asosiy oyna xabar beradi)."""
        if self._busy or self._closed:
            return
        if connected:
            # Yadro tashqaridan ko'tarilgan (konsol, xizmat) - holatni to'g'rilaymiz.
            self._set("running", "", "")
        elif self.state == "running":
            self._busy = True
            self._run.emit("check", "")

    def _begin(self, operation: str, state: str, token: str = "") -> bool:
        if self._busy or self._closed:
            return False
        self._busy = True
        self._set(state, "", "")
        self._run.emit(operation, token)
        return True

    def _set(self, state: str, reason: str, detail: str) -> None:
        if (state, reason, detail) == (self.state, self.reason, self.detail):
            return
        self.state, self.reason, self.detail = state, reason, detail
        self.changed.emit()

    @pyqtSlot(str)
    def _on_progress(self, state: str) -> None:
        if self._busy and state in TRANSITIONAL:
            self._set(state, "", "")

    @pyqtSlot(str, object)
    def _on_finished(self, operation: str, outcome: object) -> None:
        self._busy = False
        if self._closed or not isinstance(outcome, Outcome):
            return
        reason, detail = outcome.reason, outcome.detail
        if operation == "check" and outcome.state == "stopped":
            reason, detail = "lost", self.log_dir
        self._set(outcome.state, reason, detail)
        if outcome.state == "running" and outcome.token:
            self.ready.emit(outcome.token)

    def shutdown(self) -> None:
        """Oyna yopilishidan oldin: kutishlar uziladi, oqim to'xtaydi. Yadro ishlayveradi."""
        if self._closed:
            return
        self._closed = True
        self._launcher.cancel()
        self._thread.quit()
        self._thread.wait(5000)
