"""Yadro jarayonini topish, oynasiz ishga tushirish va to'xtatish (Qt'siz, bloklovchi).

Bu yerda biznes-mantiq yo'q: faqat yadro jarayonining hayot sikli. To'xtatish yadro
API'si orqali bajariladi. Yadro Windows xizmati bo'lsa, xizmat `sc.exe` bilan
boshqariladi - administrator tasdig'ini (UAC) foydalanuvchining o'zi beradi.
Funksiyalar fon oqimidan chaqiriladi (`server_control.py`).
"""

import contextlib
import ctypes
import os
import re
import subprocess
import sys
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from http import HTTPStatus
from pathlib import Path
from typing import Any, Literal, cast

import httpx
import psutil

from srv1_shell.config import read_token

SERVICE_NAME = "SRV_1"
ENV_SERVICE_NAME = "SRV1_SERVICE_NAME"
LAUNCH_LOG = "core-launch.log"
SERVICE_LOG = "service.log"
POLL_S = 0.3
TOKEN_WAIT_S = 5.0
_SERVICE_NAME_PATTERN = re.compile(r"[A-Za-z0-9_.-]{1,64}")
_SHELL_EXECUTE_OK = 32  # ShellExecuteW: shundan katta qiymat - muvaffaqiyat
_PROBE_TIMEOUT = httpx.Timeout(1.5)
_CALL_TIMEOUT = httpx.Timeout(10.0, connect=2.0)

State = Literal["running", "stopped", "failed"]
ServiceAction = Literal["start", "stop"]
Report = Callable[[str], None]
Elevate = Callable[[ServiceAction, str], bool]


@dataclass(frozen=True, slots=True)
class Outcome:
    """Amal natijasi. `reason` - tarjima kaliti (`server.reason.<reason>`); bo'sh - izoh yo'q."""

    state: State
    reason: str = ""
    detail: str = ""
    token: str = ""


def app_root() -> Path:
    """Dastur papkasi: ichida `core/`, `shell/`, `plugins/` (repo yoki o'rnatilgan nusxa)."""
    return Path(__file__).resolve().parents[2]


def service_name() -> str:
    """Xizmat nomi. `service.ps1 -Name` bilan boshqa nom berilgan bo'lsa: `SRV1_SERVICE_NAME`."""
    name = os.environ.get(ENV_SERVICE_NAME, "").strip()
    return name if _SERVICE_NAME_PATTERN.fullmatch(name) else SERVICE_NAME


def core_python() -> Path:
    """Shell `pythonw.exe` da ishlaydi; yadroga chiqish oqimi bor `python.exe` kerak."""
    return Path(sys.executable).with_name("python.exe")


def elevate_service(action: ServiceAction, name: str) -> bool:
    """`sc.exe start|stop <xizmat>` ni administrator sifatida chaqiradi (UAC oynasi chiqadi)."""
    if _SERVICE_NAME_PATTERN.fullmatch(name) is None:
        return False
    system_root = os.environ.get("SYSTEMROOT", "").strip() or r"C:\Windows"
    sc = Path(system_root) / "System32" / "sc.exe"
    code = ctypes.windll.shell32.ShellExecuteW(None, "runas", str(sc), f"{action} {name}", None, 0)
    return int(code) > _SHELL_EXECUTE_OK


def _last_line(path: Path) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return lines[-1][:300] if lines else ""


class Launcher:
    """Bitta yadro manzili va ma'lumotlar papkasi uchun: tekshirish, ishga tushirish, to'xtatish."""

    def __init__(
        self,
        base_url: str,
        data_dir: Path,
        *,
        service_name: str = SERVICE_NAME,
        start_timeout_s: float = 90.0,
        stop_timeout_s: float = 45.0,
        elevate: Elevate = elevate_service,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._data_dir = data_dir
        self._service_name = service_name
        self._start_timeout_s = start_timeout_s
        self._stop_timeout_s = stop_timeout_s
        self._elevate = elevate
        self._cancel = threading.Event()
        self._process: subprocess.Popen[bytes] | None = None

    # --- yordamchilar -----------------------------------------------------------------
    @property
    def token_file(self) -> Path:
        return self._data_dir / "auth.token"

    @property
    def launch_log(self) -> Path:
        return self._data_dir / "logs" / LAUNCH_LOG

    def cancel(self) -> None:
        """Kutishlarni uzadi (oyna yopilayotganda). Ishga tushgan yadroga tegilmaydi."""
        self._cancel.set()

    def is_up(self) -> bool:
        try:
            reply = httpx.get(
                f"{self._base_url}/api/v1/health", timeout=_PROBE_TIMEOUT, trust_env=False
            )
        except httpx.HTTPError:
            return False
        return reply.status_code == HTTPStatus.OK

    def service(self) -> str:
        """Xizmat holati: `not-installed`, `running`, `stopped`, `start_pending`, ..."""
        try:
            return str(psutil.win_service_get(self._service_name).status())
        except psutil.NoSuchProcess:
            return "not-installed"
        except (psutil.Error, OSError):
            return "unknown"

    def _wait(self, condition: Callable[[], bool], timeout_s: float) -> bool:
        deadline = time.monotonic() + timeout_s
        while not self._cancel.is_set():
            if condition():
                return True
            if time.monotonic() >= deadline:
                return False
            self._cancel.wait(POLL_S)
        return False

    def _running(self) -> Outcome:
        """Yadro javob beryapti: token faylini kutadi (birinchi ishga tushishda endi yoziladi)."""
        token: list[str] = []

        def found() -> bool:
            value = read_token(self.token_file)
            if value:
                token.append(value)
            return bool(value)

        if self._wait(found, TOKEN_WAIT_S):
            return Outcome("running", token=token[-1])
        return Outcome("running", "no_token", str(self.token_file))

    def _call(self, method: str, path: str, token: str) -> tuple[int, Any]:
        """(holat kodi, JSON). Ulanib bo'lmasa kod 0."""
        try:
            reply = httpx.request(
                method,
                self._base_url + path,
                headers={"Authorization": f"Bearer {token}"},
                timeout=_CALL_TIMEOUT,
                trust_env=False,
            )
        except httpx.HTTPError:
            return 0, None
        try:
            return reply.status_code, reply.json()
        except ValueError:
            return reply.status_code, None

    # --- amallar ----------------------------------------------------------------------
    def check(self, report: Report) -> Outcome:
        """Hech narsani o'zgartirmaydi: yadro javob beryaptimi."""
        del report
        return self._running() if self.is_up() else Outcome("stopped")

    def ensure(self, report: Report) -> Outcome:
        """Oyna ochilganda: yadro ishlamayotgan bo'lsa ko'taradi. Xizmat uchun UAC so'ramaydi."""
        report("checking")
        if self.is_up():
            return self._running()
        service = self.service()
        if service in ("running", "start_pending", "continue_pending"):
            return self._await_service(report)
        if service != "not-installed":
            return Outcome("stopped", "service_stopped")
        return self._spawn(report)

    def start(self, report: Report) -> Outcome:
        """«Ishga tushirish» tugmasi: xizmat bo'lsa uni (UAC bilan), bo'lmasa yadroning o'zini."""
        report("starting")
        if self.is_up():
            return self._running()
        service = self.service()
        if service == "not-installed":
            return self._spawn(report)
        if service not in ("running", "start_pending", "continue_pending") and not self._elevate(
            "start", self._service_name
        ):
            return Outcome("stopped", "uac_declined")
        return self._await_service(report)

    def _await_service(self, report: Report) -> Outcome:
        report("starting")
        if self._wait(self.is_up, self._start_timeout_s):
            return self._running()
        if self._cancel.is_set():
            return Outcome("stopped")
        return Outcome("failed", "start_timeout", str(self._data_dir / "logs" / SERVICE_LOG))

    def _spawn(self, report: Report) -> Outcome:
        report("starting")
        python = core_python()
        if not python.is_file():
            return Outcome("failed", "no_python", str(python))
        log = self.launch_log
        environment = dict(os.environ) | {"PYTHONUNBUFFERED": "1", "PYTHONIOENCODING": "utf-8"}
        try:
            log.parent.mkdir(parents=True, exist_ok=True)
            with log.open("wb") as sink:
                # Oynasiz, o'z (ko'rinmas) konsolida: shell yopilsa ham yadro ishlayveradi.
                process = subprocess.Popen(  # noqa: S603 - buyruq qat'iy, tashqi kirish yo'q
                    [str(python), "-m", "srv1_core", "--no-console"],
                    cwd=str(app_root()),
                    env=environment,
                    stdin=subprocess.DEVNULL,
                    stdout=sink,
                    stderr=sink,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
        except OSError as exc:
            return Outcome("failed", "launch_error", str(exc))
        self._process = process
        deadline = time.monotonic() + self._start_timeout_s
        while not self._cancel.is_set():
            if self.is_up():
                return self._running()
            if process.poll() is not None:
                # Port band (kod 3) - boshqa oyna yadroni hozirgina ko'targan bo'lishi mumkin.
                if self.is_up():
                    return self._running()
                return Outcome("failed", "exited", f"{_last_line(log)} ({log.parent})".strip())
            if time.monotonic() >= deadline:
                return Outcome("failed", "start_timeout", str(log))
            self._cancel.wait(POLL_S)
        return Outcome("stopped")

    def stop(self, token: str, report: Report) -> Outcome:
        """Yadroni tartibli to'xtatadi va jarayoni tugaguncha kutadi."""
        report("stopping")
        if not self.is_up():
            return Outcome("stopped")
        _, info = self._call("GET", "/api/v1/system/server", token)
        pid = cast(dict[str, Any], info).get("pid") if isinstance(info, dict) else None
        status, body = self._call("POST", "/api/v1/system/shutdown", token)
        missing = status in (HTTPStatus.NOT_FOUND, HTTPStatus.METHOD_NOT_ALLOWED)
        if status == HTTPStatus.CONFLICT or (missing and self.service() == "running"):
            if not self._elevate("stop", self._service_name):
                return Outcome("running", "uac_declined", token=token)
        elif missing:
            return Outcome("running", "unsupported", token=token)
        elif status not in (0, HTTPStatus.ACCEPTED):
            detail = cast(dict[str, Any], body).get("detail") if isinstance(body, dict) else None
            return Outcome("running", "stop_refused", f"{status} {detail or ''}".strip(), token)

        def gone() -> bool:
            alive = isinstance(pid, int) and psutil.pid_exists(pid)
            return not alive and not self.is_up()

        if not self._wait(gone, self._stop_timeout_s):
            return Outcome("running", "stop_timeout", token=token)
        self._reap()
        return Outcome("stopped")

    def _reap(self) -> None:
        process, self._process = self._process, None
        if process is not None:
            with contextlib.suppress(subprocess.TimeoutExpired):
                process.wait(timeout=2)
