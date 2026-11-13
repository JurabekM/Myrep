"""Reliz yig'ish fayllari (`packaging/`): yig'ishning o'zi bu yerda yuritilmaydi.

To'liq yig'ish (ko'chma Python, ~150 MB o'rnatuvchi) bir necha daqiqa oladi va
`packaging\\build.ps1` bilan qo'lda bajariladi; natijasi `docs/reliz.md` da.
"""

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
PACKAGING = REPO / "packaging"
ISS = PACKAGING / "srv1.iss"
DEFAULT_ISL = Path(os.environ.get("PROGRAMFILES(X86)", "")) / "Inno Setup 6" / "Default.isl"


def _powershell(*arguments: str) -> subprocess.CompletedProcess[str]:
    command = ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass"]
    return subprocess.run(
        [*command, *arguments],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
        check=False,
    )


def _sections(text: str) -> dict[str, list[str]]:
    """`.iss`/`.isl` matnini bo'limlarga ajratadi (izoh va bo'sh satrlarsiz)."""
    found: dict[str, list[str]] = {}
    current = ""
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith(";"):
            continue
        header = re.fullmatch(r"\[(\w+)\]", line)
        if header:
            current = header.group(1)
            continue
        found.setdefault(current, []).append(line)
    return found


def test_packaging_files_are_ascii() -> None:
    """PowerShell 5.1 va Inno Setup BOM'siz UTF-8 ni ANSI deb o'qiydi."""
    for name in ("build.ps1", "srv1.iss"):
        assert (PACKAGING / name).read_bytes().isascii(), name


def test_build_script_parses() -> None:
    check = (
        "$errors = $null; [void][System.Management.Automation.Language.Parser]::ParseFile("
        f"'{PACKAGING / 'build.ps1'}', [ref]$null, [ref]$errors); "
        "$errors | ForEach-Object { $_.Message }; exit $errors.Count"
    )
    result = _powershell("-Command", check)
    assert result.returncode == 0, result.stdout


def test_version_is_the_same_everywhere() -> None:
    pyproject = (REPO / "pyproject.toml").read_text(encoding="utf-8")
    version = re.search(r'^version = "([^"]+)"', pyproject, re.MULTILINE)
    assert version is not None
    for package in ("core/srv1_core", "sdk/srv1_sdk", "shell/srv1_shell"):
        init = (REPO / package / "__init__.py").read_text(encoding="utf-8")
        assert f'__version__ = "{version.group(1)}"' in init, package


def test_installer_uses_the_staged_layout() -> None:
    text = ISS.read_text(encoding="ascii")
    sections = _sections(text)
    # Yorliqlar va xizmat ko'chma Python'ga qaraydi; ma'lumotlar papkasiga tegilmaydi.
    icons = "\n".join(sections["Icons"])
    assert r"{app}\python\pythonw.exe" in icons
    assert "-m srv1_shell" in icons
    assert "-m srv1_core" in icons
    run = "\n".join(sections["Run"])
    assert r'{app}\install\install.ps1"" -SkipSync -NoShortcut' in run
    assert r'{app}\install\service.ps1"" -Action install' in run
    assert 'Verb: "runas"' in run  # xizmat qadami har doim alohida administrator oynasida
    assert "PROGRAMDATA" not in "\n".join(sections.get("UninstallDelete", []))
    assert "commonappdata" not in text.lower()
    # Xizmatga faqat shu nusxaga tegishli bo'lsa tegiladi.
    assert "ServiceIsOurs() and ServiceIsRunning()" in text
    assert "(CurUninstallStep = usUninstall) and ServiceIsOurs()" in text


@pytest.mark.skipif(not DEFAULT_ISL.is_file(), reason="Inno Setup 6 o'rnatilmagan")
def test_translated_messages_exist_in_inno() -> None:
    """Noto'g'ri bo'limga tushgan tarjima jim e'tiborsiz qoladi (yorliq inglizcha chiqadi)."""
    default = _sections(DEFAULT_ISL.read_text(encoding="utf-8-sig", errors="replace"))
    ours = _sections(ISS.read_text(encoding="ascii"))
    for section in ("Messages", "CustomMessages"):
        known = {line.split("=", 1)[0] for line in default[section]}
        used = {line.split("=", 1)[0].removeprefix("uz.") for line in ours[section]}
        assert len(used) >= 4, section
        assert used <= known, (section, sorted(used - known))
    # Sehrgar sahifasidagi tugma `ButtonBrowse` emas, `ButtonWizardBrowse` xabarini oladi.
    assert any(line.startswith("uz.ButtonWizardBrowse=") for line in ours["Messages"])


def test_bundled_python_is_preferred(tmp_path: Path) -> None:
    """O'rnatilgan nusxada (`python\\python.exe` bor) skriptlar `.venv` ni emas, uni ishlatadi."""
    shutil.copytree(REPO / "install", tmp_path / "install")
    bundled = tmp_path / "python" / "python.exe"
    bundled.parent.mkdir()
    bundled.write_bytes(b"")
    result = _powershell(
        "-File", str(tmp_path / "install" / "service.ps1"), "-Action", "plan", "-DataDir", "D:\\x"
    )
    assert result.returncode == 0, result.stderr
    lines = result.stdout.splitlines()
    assert f"nssm install SRV_1 {bundled} -m srv1_core" in lines
    assert f"nssm set SRV_1 AppDirectory {tmp_path}" in lines
