"""Serverni ishga tushirish va to'xtatish: yadro API'si, `Launcher`, oyna tugmasi, `stop-core.ps1`.

Windows xizmati yo'li (UAC) haqiqatan sinalmaydi: administrator tasdig'i kerak. Uning
o'rniga `elevate` soxta funksiya bilan almashtiriladi va faqat qaror mantiqi tekshiriladi.
"""

import asyncio
import contextlib
import json
import os
import socket
import subprocess
import sys
import threading
import time
from collections.abc import Callable, Generator, Iterator
from pathlib import Path

import httpx
import psutil
import pytest
from PyQt6.QtCore import QEventLoop, QTimer
from PyQt6.QtWidgets import QApplication
from sqlalchemy import select
from websockets.sync.client import connect

from conftest import Served, free_port
from srv1_core import __version__
from srv1_core.db import AuditLog
from srv1_core.lifecycle import managed_by, port_in_use, set_exit_hook
from srv1_shell.app import apply_theme
from srv1_shell.config import ShellConfig
from srv1_shell.launcher import (
    Launcher,
    Outcome,
    ServiceAction,
    app_root,
    core_python,
    elevate_service,
    service_name,
)
from srv1_shell.main_window import MainWindow
from srv1_shell.pages.system_page import SystemPage
from srv1_shell.server_control import ServerControl

REPO = Path(__file__).resolve().parents[1]
# Bu mashinada haqiqiy `SRV_1` xizmati o'rnatilgan bo'lishi mumkin: testlar unga qaramasin.
NO_SERVICE = "SRV1-test-yoq-xizmat"


def _quiet(_state: str) -> None:
    return None


async def _audit(served: Served, action: str) -> list[AuditLog]:
    async with served.core.db.session() as session:
        rows = await session.scalars(select(AuditLog).where(AuditLog.action == action))
        return list(rows)


def _core_env(data_dir: Path, port: int) -> dict[str, str]:
    env = {key: value for key, value in os.environ.items() if not key.startswith("SRV1_")}
    return env | {
        "SRV1_DATA_DIR": str(data_dir),
        "SRV1_SERVER__PORT": str(port),
        "SRV1_PLUGINS__LOAD_BUILTIN": "false",
    }


def _healthy(port: int) -> bool:
    try:
        return httpx.get(f"http://127.0.0.1:{port}/api/v1/health", timeout=1.0).status_code == 200
    except httpx.HTTPError:
        return False


def _wait(condition: Callable[[], bool], timeout_s: float, what: str) -> None:
    deadline = time.monotonic() + timeout_s
    while not condition():
        if time.monotonic() > deadline:
            pytest.fail(f"{what}: {timeout_s:g} s ichida yuz bermadi")
        time.sleep(0.1)


@contextlib.contextmanager
def _foreign_listener(port: int = 0) -> Generator[int]:
    """SRV_1 bo'lmagan dastur portni band qilgan: ulanishni qabul qiladi va darhol yopadi."""
    listener = socket.socket()
    listener.bind(("127.0.0.1", port))
    listener.listen(16)
    listener.settimeout(0.2)
    done = threading.Event()

    def serve() -> None:
        while not done.is_set():
            with contextlib.suppress(OSError):
                listener.accept()[0].close()

    thread = threading.Thread(target=serve, daemon=True)
    thread.start()
    try:
        yield int(listener.getsockname()[1])
    finally:
        done.set()
        thread.join(timeout=5)
        listener.close()


def _kill(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is None:
        process.kill()
    process.wait(timeout=10)


def _kill_core_on(port: int) -> None:
    """Test yiqilsa ham oynasiz yadro qolib ketmasin."""
    for conn in psutil.net_connections(kind="tcp"):
        listening = conn.status == psutil.CONN_LISTEN and conn.laddr and conn.laddr.port == port
        if listening and conn.pid and conn.pid != os.getpid():
            with contextlib.suppress(psutil.Error):
                psutil.Process(conn.pid).kill()


# --- yadro API'si -----------------------------------------------------------------------------
async def test_server_info_and_shutdown_need_token(served: Served) -> None:
    async with served.client(authorized=False) as client:
        assert (await client.get("/api/v1/system/server")).status_code == 401
        assert (await client.post("/api/v1/system/shutdown")).status_code == 401
    assert await _audit(served, "core.shutdown") == []


async def test_shutdown_without_exit_hook_is_refused_and_audited(served: Served) -> None:
    async with served.client() as client:
        info = (await client.get("/api/v1/system/server")).json()
        assert info["version"] == __version__
        assert info["pid"] == os.getpid()
        assert info["managed_by"] == "standalone"
        assert info["can_shutdown"] is False
        reply = await client.post("/api/v1/system/shutdown")
    assert reply.status_code == 409
    rows = await _audit(served, "core.shutdown")
    assert [(row.ok, row.detail) for row in rows] == [(False, {"reason": "no_exit_hook"})]


async def test_shutdown_calls_exit_hook_after_reply(served: Served) -> None:
    called: list[float] = []
    set_exit_hook(served.app, lambda: called.append(time.monotonic()))
    async with served.client() as client:
        assert (await client.get("/api/v1/system/server")).json()["can_shutdown"] is True
        reply = await client.post("/api/v1/system/shutdown")
        assert reply.status_code == 202
        assert reply.json() == {"status": "stopping"}
        assert called == [], "javob to'xtatishdan oldin qaytishi kerak"
    await asyncio.sleep(0.6)
    assert len(called) == 1
    rows = await _audit(served, "core.shutdown")
    assert [(row.ok, row.actor, row.target) for row in rows] == [(True, "core", "api")]


async def test_shutdown_is_refused_under_windows_service(
    served: Served, monkeypatch: pytest.MonkeyPatch
) -> None:
    called: list[int] = []
    set_exit_hook(served.app, lambda: called.append(1))
    monkeypatch.setattr("srv1_core.api.system.managed_by", lambda: "service")
    async with served.client() as client:
        info = (await client.get("/api/v1/system/server")).json()
        assert (info["managed_by"], info["can_shutdown"]) == ("service", False)
        reply = await client.post("/api/v1/system/shutdown")
    assert reply.status_code == 409
    assert "xizmat" in reply.json()["detail"]
    await asyncio.sleep(0.5)
    assert called == []
    rows = await _audit(served, "core.shutdown")
    assert [(row.ok, row.detail) for row in rows] == [(False, {"reason": "service"})]


def test_managed_by_and_port_probe() -> None:
    assert managed_by() == "standalone"  # pytest NSSM ostida emas
    with _foreign_listener() as port:
        assert port_in_use("127.0.0.1", port)
        assert port_in_use("0.0.0.0", port)  # noqa: S104 - faqat tekshiruv manzili
    assert not port_in_use("127.0.0.1", port)


# --- haqiqiy jarayon: `python -m srv1_core --no-console` ---------------------------------------
def test_live_core_shuts_down_cleanly_with_open_websocket(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    port = free_port()
    output = tmp_path / "output.txt"
    with output.open("wb") as sink:
        core = subprocess.Popen(
            [sys.executable, "-m", "srv1_core", "--no-console"],
            env=_core_env(data_dir, port),
            stdout=sink,
            stderr=sink,
        )
    try:
        _wait(lambda: _healthy(port), 30, "yadro ishga tushishi")
        token = (data_dir / "auth.token").read_text(encoding="ascii").strip()
        headers = {"Authorization": f"Bearer {token}"}
        # Shell kabi ochiq WebSocket: u to'xtashni ushlab qolmasligi kerak.
        with connect(f"ws://127.0.0.1:{port}/ws/events?topics=*", additional_headers=headers):
            reply = httpx.post(
                f"http://127.0.0.1:{port}/api/v1/system/shutdown", headers=headers, timeout=5
            )
            assert reply.status_code == 202
            started = time.monotonic()
            core.wait(timeout=20)
            took = time.monotonic() - started
    finally:
        _kill(core)
    assert core.returncode == 0
    assert took < 15, f"to'xtash {took:.1f} s oldi"
    assert not _healthy(port)
    text = output.read_text(encoding="utf-8", errors="replace")
    assert "Traceback" not in text, text[-2000:]
    # `--no-console`: jurnal konsolga emas, faqat faylga yoziladi.
    assert "core_started" not in text
    logs = "".join(
        path.read_text(encoding="utf-8", errors="replace")
        for path in (data_dir / "logs").glob("*.log*")
    )
    assert "core_started" in logs
    assert "core_stopped" in logs
    assert "core.shutdown" in logs


def test_second_core_exits_before_starting_plugins(tmp_path: Path) -> None:
    """Port band bo'lsa yadro darhol chiqadi (kod 3): bazani ham, plaginlarni ham ochmaydi."""
    data_dir = tmp_path / "data"
    with _foreign_listener() as port:
        result = subprocess.run(
            [sys.executable, "-m", "srv1_core", "--no-console"],
            env=_core_env(data_dir, port),
            capture_output=True,
            timeout=30,
            check=False,
        )
    assert result.returncode == 3
    assert b"band" in result.stderr
    assert not (data_dir / "srv1.db").exists()
    assert not (data_dir / "auth.token").exists()


# --- Launcher --------------------------------------------------------------------------------
@pytest.fixture
def launch_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[tuple[Path, int]]:
    """Launcher ishga tushiradigan yadro shu muhitni meros oladi: toza papka, bo'sh port."""
    data_dir = tmp_path / "toza-data"
    port = free_port()
    monkeypatch.setenv("SRV1_DATA_DIR", str(data_dir))
    monkeypatch.setenv("SRV1_SERVER__PORT", str(port))
    yield data_dir, port
    _kill_core_on(port)


def _launcher(data_dir: Path, port: int, **options: object) -> Launcher:
    settings: dict[str, object] = {"service_name": NO_SERVICE, "start_timeout_s": 40.0}
    return Launcher(f"http://127.0.0.1:{port}", data_dir, **(settings | options))  # type: ignore[arg-type]


def test_paths_point_into_the_repo() -> None:
    assert app_root() == REPO
    assert (app_root() / "core" / "srv1_core" / "__main__.py").is_file()
    assert core_python().name == "python.exe"
    assert core_python().is_file()


def test_launcher_starts_core_without_token_then_stops_and_restarts(
    launch_env: tuple[Path, int],
) -> None:
    data_dir, port = launch_env
    assert not data_dir.exists(), "boshqa kompyuterdagi holat: papka ham, token ham yo'q"
    launcher = _launcher(data_dir, port)
    states: list[str] = []
    assert launcher.check(_quiet) == Outcome("stopped")

    first = launcher.ensure(states.append)
    assert first.state == "running", first
    assert states == ["checking", "starting"]
    token = (data_dir / "auth.token").read_text(encoding="ascii").strip()
    assert first == Outcome("running", token=token)
    assert launcher.launch_log.is_file()
    headers = {"Authorization": f"Bearer {token}"}
    info = httpx.get(f"http://127.0.0.1:{port}/api/v1/system/server", headers=headers).json()
    assert info["can_shutdown"] is True
    core = psutil.Process(info["pid"])
    assert core.cmdline()[-3:] == ["-m", "srv1_core", "--no-console"]
    # Ikkinchi chaqiruv yangi jarayon ochmaydi.
    assert launcher.ensure(_quiet) == first
    assert launcher.start(_quiet) == first

    assert launcher.stop("x" * 43, _quiet).reason == "stop_refused"
    assert core.is_running()
    assert launcher.stop(token, states.append) == Outcome("stopped")
    assert states[-1] == "stopping"
    assert not core.is_running()
    assert not _healthy(port)
    assert launcher.stop(token, _quiet) == Outcome("stopped")  # allaqachon to'xtagan

    again = launcher.start(_quiet)
    assert again == first  # token o'zgarmaydi
    assert launcher.stop(token, _quiet) == Outcome("stopped")
    # Yadro konsolga yozmaydi: ishga tushirish jurnali bo'sh (faqat yiqilish izi tushadi).
    assert launcher.launch_log.read_text(encoding="utf-8") == ""


def test_launcher_reports_core_that_exits(launch_env: tuple[Path, int]) -> None:
    data_dir, port = launch_env
    with _foreign_listener(port):  # port band, lekin u yerda SRV_1 emas
        outcome = _launcher(data_dir, port).ensure(_quiet)
    assert outcome.state == "failed"
    assert outcome.reason == "exited"
    assert "band" in outcome.detail
    assert str(data_dir / "logs") in outcome.detail


def test_launcher_start_timeout_and_cancel(
    launch_env: tuple[Path, int], monkeypatch: pytest.MonkeyPatch
) -> None:
    data_dir, port = launch_env
    # Yadro boshqa portda ko'tariladi (shell sozlamasi bilan mos emas) - javob kelmaydi.
    other = free_port()
    monkeypatch.setenv("SRV1_SERVER__PORT", str(other))
    launcher = _launcher(data_dir, port, start_timeout_s=8.0)
    try:
        outcome = launcher.ensure(_quiet)
        assert (outcome.state, outcome.reason) == ("failed", "start_timeout")
        assert outcome.detail == str(launcher.launch_log)
    finally:
        _wait(lambda: _healthy(other), 30, "boshqa portdagi yadro")
        token = (data_dir / "auth.token").read_text(encoding="ascii").strip()
        assert _launcher(data_dir, other).stop(token, _quiet) == Outcome("stopped")
    # Oyna yopilsa, kutish darhol uziladi (xizmat ko'tarilishini kutayotgan holat).
    waiting = _launcher(data_dir, port, start_timeout_s=60.0)
    monkeypatch.setattr(waiting, "service", lambda: "start_pending")
    waiting.cancel()
    started = time.monotonic()
    assert waiting.ensure(_quiet) == Outcome("stopped")
    assert time.monotonic() - started < 5


class _Elevation:
    def __init__(self, *, accept: bool) -> None:
        self.accept = accept
        self.calls: list[tuple[ServiceAction, str]] = []

    def __call__(self, action: ServiceAction, name: str) -> bool:
        self.calls.append((action, name))
        return self.accept


def test_stopped_service_is_not_started_without_the_button(
    launch_env: tuple[Path, int], monkeypatch: pytest.MonkeyPatch
) -> None:
    data_dir, port = launch_env
    declined = _Elevation(accept=False)
    launcher = _launcher(data_dir, port, service_name="SRV_1", elevate=declined)
    monkeypatch.setattr(launcher, "service", lambda: "stopped")
    # Oyna ochilganda UAC so'ralmaydi va xizmat o'rniga alohida yadro ham ko'tarilmaydi.
    assert launcher.ensure(_quiet) == Outcome("stopped", "service_stopped")
    assert declined.calls == []
    assert not data_dir.exists()
    # Tugma: UAC rad etildi.
    assert launcher.start(_quiet) == Outcome("stopped", "uac_declined")
    assert declined.calls == [("start", "SRV_1")]
    # Tugma: UAC tasdiqlandi, lekin xizmat ko'tarilmadi.
    accepted = _Elevation(accept=True)
    slow = _launcher(data_dir, port, service_name="SRV_1", elevate=accepted, start_timeout_s=1.5)
    monkeypatch.setattr(slow, "service", lambda: "stopped")
    outcome = slow.start(_quiet)
    assert (outcome.state, outcome.reason) == ("failed", "start_timeout")
    assert outcome.detail.endswith("service.log")
    assert accepted.calls == [("start", "SRV_1")]
    assert not data_dir.exists()


async def test_service_managed_core_is_stopped_through_elevation(
    served: Served, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Yadro 409 qaytarsa (xizmat ostida) - `sc stop` yo'li; rad etilsa hech narsa o'zgarmaydi."""
    monkeypatch.setattr("srv1_core.api.system.managed_by", lambda: "service")
    declined = _Elevation(accept=False)
    launcher = Launcher(served.http_url, served.core.paths.root, elevate=declined)
    outcome = await asyncio.to_thread(launcher.stop, served.token, _quiet)
    assert outcome == Outcome("running", "uac_declined", token=served.token)
    assert declined.calls == [("stop", "SRV_1")]
    accepted = _Elevation(accept=True)
    waiting = Launcher(
        served.http_url, served.core.paths.root, elevate=accepted, stop_timeout_s=1.5
    )
    outcome = await asyncio.to_thread(waiting.stop, served.token, _quiet)
    assert (outcome.state, outcome.reason) == ("running", "stop_timeout")  # soxta UAC to'xtatmaydi
    assert accepted.calls == [("stop", "SRV_1")]


def test_service_name_comes_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    assert service_name() == "SRV_1"
    monkeypatch.setenv("SRV1_SERVICE_NAME", "SRV_1-sinov")
    assert service_name() == "SRV_1-sinov"
    monkeypatch.setenv("SRV1_SERVICE_NAME", "yomon nom & calc")
    assert service_name() == "SRV_1"


def test_elevation_rejects_unsafe_service_names() -> None:
    """Noto'g'ri nom `sc.exe` ga yetib bormaydi (UAC oynasi ham chiqmaydi)."""
    for name in ("", "SRV_1 & calc", "a b", "x" * 65, 'q"uote'):
        assert elevate_service("stop", name) is False


# --- oyna: tugma va holat ----------------------------------------------------------------------
def _spin(ms: int) -> None:
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


def _pump(condition: Callable[[], bool], timeout_s: float, what: str) -> None:
    deadline = time.monotonic() + timeout_s
    while not condition():
        if time.monotonic() > deadline:
            pytest.fail(f"kutilgan holat yuz bermadi: {what}")
        _spin(20)


@pytest.fixture(scope="module")
def qapp() -> QApplication:
    existing = QApplication.instance()
    app = existing if isinstance(existing, QApplication) else QApplication([])
    apply_theme(app)
    return app


def test_window_starts_stops_and_restarts_the_server(
    qapp: QApplication, launch_env: tuple[Path, int]
) -> None:
    data_dir, port = launch_env
    control = ServerControl(_launcher(data_dir, port))
    config = ShellConfig(language="uz", host="127.0.0.1", port=port)
    main = MainWindow(config, "", control=control)
    asked: list[int] = []
    main.show()
    try:
        assert main.server_button.isVisible()
        assert not main.events.running, "token yo'q: hodisalar oqimi hali boshlanmaydi"
        assert control.ensure()
        assert not control.ensure(), "amal tugamaguncha ikkinchisi boshlanmaydi"
        assert main.connection.text() == "● Server tekshirilmoqda…"
        assert not main.server_button.isEnabled()
        _pump(lambda: control.state == "starting", 10, "ishga tushish holati")
        assert main.connection.text() == "● Server ishga tushmoqda…"
        assert main.connection.objectName() == "ConnWait"
        _pump(lambda: main.events.connected, 40, "yadro ko'tarilib, oyna ulanishi")
        assert control.state == "running"
        assert (data_dir / "auth.token").is_file()
        assert main.connection.text() == f"● Ulangan — Yadro 127.0.0.1:{port}"
        assert main.connection.objectName() == "ConnOk"
        assert main.server_button.text() == "Serverni toʻxtatish"
        assert main.server_button.objectName() == "Danger"
        assert main.server_button.isEnabled()
        assert main.server_note.isHidden()
        before = main.page("system")
        assert isinstance(before, SystemPage)
        _pump(lambda: before.core.value.text() != "—", 10, "tizim sahifasi ma'lumoti")

        # Tasdiqlanmasa to'xtamaydi.
        main.confirm_stop = lambda: bool(asked.append(1))
        main.server_button.click()
        _spin(200)
        assert asked == [1]
        assert control.state == "running" and not control.busy

        main.confirm_stop = lambda: True
        main.server_button.click()
        assert main.connection.text() == "● Server toʻxtatilmoqda…"
        assert not main.server_button.isEnabled()
        _pump(lambda: control.state == "stopped", 40, "server to'xtashi")
        assert not _healthy(port)
        _pump(lambda: not main.events.connected, 5, "ulanish uzilishi")
        assert main.connection.text() == "● Server toʻxtatilgan"
        assert main.connection.objectName() == "ConnBad"
        assert main.server_button.text() == "Serverni ishga tushirish"
        assert main.server_button.objectName() == "Primary"
        assert main.server_button.isEnabled()
        assert main.server_note.isHidden()
        # To'xtatilgan server sahifalarida eski raqamlar qolmaydi; plagin bo'limlari yopiladi.
        after = main.page("system")
        assert isinstance(after, SystemPage)
        assert after is not before
        assert after.core.value.text() == "—"
        _pump(lambda: after.error.text() != "", 10, "ulanish xatosi")
        assert after.error.text() == "Yadroga ulanib boʻlmadi"
        assert main.page_keys() == ["system", "plugins", "logs", "memory"]

        main.server_button.click()
        assert main.connection.text() == "● Server ishga tushmoqda…"
        _pump(lambda: main.events.connected, 40, "qayta ishga tushish")
        assert control.state == "running"
        assert main.server_button.text() == "Serverni toʻxtatish"

        # Oyna yopilsa, server ishlashda davom etadi.
        main.shutdown()
        _spin(300)
        assert _healthy(port)
    finally:
        main.shutdown()
        main.close()
        main.deleteLater()
        _spin(20)
    token = (data_dir / "auth.token").read_text(encoding="ascii").strip()
    assert _launcher(data_dir, port).stop(token, _quiet) == Outcome("stopped")


def test_window_shows_why_the_server_did_not_start(
    qapp: QApplication, launch_env: tuple[Path, int]
) -> None:
    data_dir, port = launch_env
    with _foreign_listener(port):  # port band: yadro ishga tushmay chiqadi
        control = ServerControl(_launcher(data_dir, port))
        config = ShellConfig(language="uz", host="127.0.0.1", port=port)
        main = MainWindow(config, "", control=control)
        main.show()
        try:
            control.ensure()
            _pump(lambda: control.state == "failed", 30, "xato holati")
            assert main.connection.text() == "● Server ishga tushmadi"
            assert main.server_note.isVisible()
            assert main.server_note.text().startswith("Yadro ishga tushmay toʻxtadi: ")
            assert str(data_dir / "logs") in main.server_note.text()
            assert main.server_button.text() == "Serverni ishga tushirish"
            assert main.server_button.isEnabled()
            # Til almashsa izoh ham o'giriladi.
            main.set_language("en")
            assert main.connection.text() == "● Server failed to start"
            assert main.server_note.text().startswith("The core exited before it started: ")
            assert main.server_button.text() == "Start server"
        finally:
            main.shutdown()
            main.close()
            main.deleteLater()
            _spin(20)


def test_header_fits_the_minimum_window_in_every_language() -> None:
    """Server tugmasi qo'shilgach ham sarlavha eng tor oynaga sig'adi (uch til, hamma holat)."""
    env = dict(os.environ) | {"QT_QPA_PLATFORM": "windows"}
    result = subprocess.run(
        [sys.executable, str(Path(__file__).with_name("header_probe.py"))],
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    if result.returncode != 0:
        pytest.skip(f"haqiqiy ekran platformasi yo'q: {result.stderr[-300:]}")
    report = json.loads(result.stdout.strip().splitlines()[-1])
    assert report["platform"] == "windows"
    assert len(report["widths"]) == 3 * 6 * 2
    too_wide = {key: width for key, width in report["widths"].items() if width > report["minimum"]}
    assert too_wide == {}, f"oyna eng kichik kengligi {report['minimum']}"


def test_server_control_follows_the_connection(qapp: QApplication) -> None:
    """Yadro tashqaridan ko'tarilsa yoki o'lsa, holat hodisalar oqimiga qarab to'g'rilanadi."""
    port = free_port()
    control = ServerControl(_launcher(Path("yoq-papka"), port))
    seen: list[tuple[str, str]] = []
    control.changed.connect(lambda: seen.append((control.state, control.reason)))
    try:
        control.connection_changed(True)
        assert (control.state, control.busy) == ("running", False)
        control.connection_changed(False)  # yadro javob bermayapti - tekshiriladi
        assert control.busy
        assert not control.start(), "tekshiruv paytida boshqa amal boshlanmaydi"
        _pump(lambda: not control.busy, 15, "tekshiruv tugashi")
        assert (control.state, control.reason) == ("stopped", "lost")
        assert control.detail == control.log_dir
        control.connection_changed(True)
        assert (control.state, control.reason) == ("running", "")
        assert seen == [("running", ""), ("stopped", "lost"), ("running", "")]
    finally:
        control.shutdown()
    assert not control.ensure(), "yopilgandan keyin amal qabul qilinmaydi"


# --- install\stop-core.ps1 ---------------------------------------------------------------------
def _stop_core(*arguments: str) -> subprocess.CompletedProcess[str]:
    command = ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass"]
    script = REPO / "install" / "stop-core.ps1"
    return subprocess.run(
        [*command, "-File", str(script), *arguments],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=90,
        check=False,
    )


def test_stop_core_script_stops_a_running_core(tmp_path: Path) -> None:
    """O'rnatuvchi yangilashdan oldin shuni chaqiradi; port `config.toml` dan o'qiladi."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    port = free_port()
    config = f'[server]\nhost = "127.0.0.1"\nport = {port}\n\n[plugins]\nload_builtin = false\n'
    (data_dir / "config.toml").write_text(config, encoding="utf-8")
    env = {key: value for key, value in os.environ.items() if not key.startswith("SRV1_")}
    env["SRV1_DATA_DIR"] = str(data_dir)
    assert _stop_core("-DataDir", str(data_dir)).returncode == 0  # yadro yo'q - xato emas
    core = subprocess.Popen(
        [sys.executable, "-m", "srv1_core", "--no-console"],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        _wait(lambda: _healthy(port), 30, "yadro ishga tushishi")
        token_file = data_dir / "auth.token"
        token = token_file.read_text(encoding="ascii")
        token_file.write_text("x" * 43, encoding="ascii")
        refused = _stop_core("-DataDir", str(data_dir), "-WaitSeconds", "3")
        assert refused.returncode == 1, refused.stdout + refused.stderr
        assert core.poll() is None
        token_file.write_text(token, encoding="ascii")
        result = _stop_core("-DataDir", str(data_dir))
        assert result.returncode == 0, result.stdout + result.stderr
        assert core.poll() == 0, "skript qaytganda yadro jarayoni tugagan bo'lishi kerak"
    finally:
        _kill(core)
    assert not _healthy(port)
