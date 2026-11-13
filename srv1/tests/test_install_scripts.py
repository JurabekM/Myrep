"""O'rnatish skriptlari: administratorsiz qismi haqiqatan yuguriladi.

Xizmatni haqiqatan o'rnatish sinalmaydi (administrator huquqi va parol kerak);
`plan` rejimi va rad etish tekshiriladi. NSSM hech qachon chaqirilmaydi: u
konsolsiz ishga tushsa xabar oynasi ochib, testni osib qo'yadi.
"""

import ctypes
import os
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
INSTALL = REPO / "install"
SCRIPTS = sorted(INSTALL.glob("*.ps1"))
IS_ADMIN = bool(ctypes.windll.shell32.IsUserAnAdmin())


def _powershell(*arguments: str, timeout: float = 120) -> subprocess.CompletedProcess[str]:
    command = ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass"]
    return subprocess.run(
        [*command, *arguments],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
    )


def _script(name: str, *arguments: str) -> subprocess.CompletedProcess[str]:
    return _powershell("-File", str(INSTALL / name), *arguments)


def test_scripts_exist_and_are_ascii() -> None:
    """PowerShell 5.1 BOM'siz UTF-8 ni ANSI deb o'qiydi — shuning uchun faqat ASCII."""
    assert [path.name for path in SCRIPTS] == [
        "common.ps1",
        "install.ps1",
        "service.ps1",
        "uninstall.ps1",
    ]
    for path in SCRIPTS:
        assert path.read_bytes().isascii(), path.name


@pytest.mark.parametrize("path", SCRIPTS, ids=lambda path: path.name)
def test_script_parses(path: Path) -> None:
    check = (
        "$errors = $null; [void][System.Management.Automation.Language.Parser]::ParseFile("
        f"'{path}', [ref]$null, [ref]$errors); $errors | ForEach-Object {{ $_.Message }}; "
        "exit $errors.Count"
    )
    result = _powershell("-Command", check)
    assert result.returncode == 0, result.stdout


def test_service_plan_changes_nothing(tmp_path: Path) -> None:
    data = tmp_path / "data"
    result = _script("service.ps1", "-Action", "plan", "-DataDir", str(data), "-Account", "PC\\ali")
    assert result.returncode == 0, result.stderr
    lines = result.stdout.splitlines()
    python = REPO / ".venv" / "Scripts" / "python.exe"
    assert f"nssm install SRV_1 {python} -m srv1_core" in lines
    assert f"nssm set SRV_1 AppDirectory {REPO}" in lines
    assert f"nssm set SRV_1 AppEnvironmentExtra SRV1_DATA_DIR={data} PYTHONUNBUFFERED=1" in lines
    assert "nssm set SRV_1 Start SERVICE_DELAYED_AUTO_START" in lines
    assert "nssm set SRV_1 AppExit Default Restart" in lines
    assert "nssm set SRV_1 AppStopMethodConsole 20000" in lines
    # Parol rejaga hech qachon tushmaydi.
    assert "nssm set SRV_1 ObjectName PC\\ali <parol so'raladi>" in lines
    assert not data.exists()


# NSSM 2.24 (tools/ dagi barqaror versiya) qabul qiladigan parametrlar — uning o'z xabaridan.
# 2026-11-13: `AppKillProcessTree` (faqat 2.25 sinov yig'ilishida bor) o'rnatishni yiqitgan.
NSSM_224_PARAMETERS = frozenset(
    """Application AppParameters AppDirectory AppExit AppAffinity AppEnvironment
    AppEnvironmentExtra AppNoConsole AppPriority AppRestartDelay AppStdin AppStdinShareMode
    AppStdinCreationDisposition AppStdinFlagsAndAttributes AppStdout AppStdoutShareMode
    AppStdoutCreationDisposition AppStdoutFlagsAndAttributes AppStderr AppStderrShareMode
    AppStderrCreationDisposition AppStderrFlagsAndAttributes AppStopMethodSkip
    AppStopMethodConsole AppStopMethodWindow AppStopMethodThreads AppThrottle AppRotateFiles
    AppRotateOnline AppRotateSeconds AppRotateBytes AppRotateBytesHigh DependOnGroup
    DependOnService Description DisplayName ImagePath ObjectName Name Start Type""".split()  # noqa: SIM905
)


def test_service_plan_uses_only_nssm_224_parameters(tmp_path: Path) -> None:
    result = _script("service.ps1", "-Action", "plan", "-DataDir", str(tmp_path / "data"))
    assert result.returncode == 0, result.stderr
    used = {line.split()[3] for line in result.stdout.splitlines() if line.startswith("nssm set ")}
    assert len(used) > 10
    assert used <= NSSM_224_PARAMETERS, sorted(used - NSSM_224_PARAMETERS)


def test_service_status_without_service() -> None:
    result = _script("service.ps1", "-Action", "status", "-Name", "SRV_1_sinov_yoq")
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "SRV_1_sinov_yoq: not-installed"


@pytest.mark.skipif(IS_ADMIN, reason="administrator bilan bu amal haqiqatan bajariladi")
@pytest.mark.parametrize("action", ["install", "remove", "start", "stop", "restart"])
def test_service_changes_need_administrator(action: str, tmp_path: Path) -> None:
    # Yo'q nssm: rad etish NSSM chaqirilishidan oldin bo'lishi shart.
    result = _script(
        "service.ps1", "-Action", action, "-Name", "SRV_1_sinov_yoq", "-Nssm", str(tmp_path / "x")
    )
    assert result.returncode == 1
    assert "administrator huquqi kerak" in result.stdout


def _acl(path: Path) -> str:
    icacls = Path(os.environ["SYSTEMROOT"]) / "System32" / "icacls.exe"
    return subprocess.run(
        [str(icacls), str(path)], capture_output=True, text=True, errors="replace", check=True
    ).stdout


def test_install_creates_data_dir_and_shortcut(tmp_path: Path) -> None:
    data, links = tmp_path / "data", tmp_path / "links"
    arguments = ("-DataDir", str(data), "-ShortcutDir", str(links), "-SkipSync")
    result = _script("install.ps1", *arguments)
    assert result.returncode == 0, result.stdout + result.stderr
    assert all((data / name).is_dir() for name in ("logs", "projects", "plugins"))

    # Faqat uch yozuv (foydalanuvchi, SYSTEM, administratorlar), meros yo'q.
    entries = [line for line in _acl(data).splitlines() if "(F)" in line]
    assert len(entries) == 3, entries
    assert "(I)" not in _acl(data)
    assert "SRV1_DATA_DIR" in result.stdout  # standart bo'lmagan papka haqida ogohlantirish

    read_link = (
        f"$l = (New-Object -ComObject WScript.Shell).CreateShortcut('{links / 'SRV_1.lnk'}'); "
        "$l.TargetPath; $l.Arguments; $l.WorkingDirectory; $l.IconLocation"
    )
    target, args, cwd, icon = _powershell("-Command", read_link).stdout.splitlines()
    assert Path(target) == REPO / ".venv" / "Scripts" / "pythonw.exe"
    assert (args, Path(cwd)) == ("-m srv1_shell", REPO)
    assert Path(icon.split(",")[0]).is_file()

    # Qayta yugurish mavjud papkaning ichiga va ruxsatlariga tegmaydi.
    (data / "config.toml").write_text("# meniki\n", encoding="utf-8")
    again = _script("install.ps1", *arguments)
    assert again.returncode == 0
    assert "allaqachon bor" in again.stdout
    assert (data / "config.toml").read_text(encoding="utf-8") == "# meniki\n"

    removed = _script("uninstall.ps1", "-ShortcutDir", str(links))
    assert removed.returncode == 0
    assert not (links / "SRV_1.lnk").exists()
    assert (data / "config.toml").is_file()  # ma'lumotlarga tegilmaydi


def test_icon_file_matches_code() -> None:
    """`srv1.ico` — `python -m srv1_shell.icon` natijasi; yorliq va oyna bir xil belgi."""
    from PyQt6.QtGui import QGuiApplication, QImage

    from srv1_shell.icon import ICON_FILE, draw_icon

    _app = QGuiApplication.instance() or QGuiApplication([])
    stored = QImage(str(ICON_FILE))
    assert stored.size().width() == 256
    drawn = draw_icon(256).convertToFormat(stored.format())
    assert stored == drawn
