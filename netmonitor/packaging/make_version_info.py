"""PyInstaller uchun Windows versiya manbasini (`--version-file`) yozadi.

Foydalanish: python packaging/make_version_info.py <chiqish fayli>
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

SOURCE = Path(__file__).resolve().parent.parent / "netmonitor.py"

TEMPLATE = """VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={numbers},
    prodvers={numbers},
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable('040904B0', [
        StringStruct('FileDescription', 'NetMonitor - tarmoq kuzatuvi'),
        StringStruct('FileVersion', '{version}'),
        StringStruct('InternalName', 'NetMonitor'),
        StringStruct('OriginalFilename', 'NetMonitor.exe'),
        StringStruct('ProductName', 'NetMonitor'),
        StringStruct('ProductVersion', '{version}')
      ])
    ]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"""


def read_version() -> str:
    found = re.search(r'^__version__ = "(\d+)\.(\d+)\.(\d+)"$', SOURCE.read_text(encoding="utf-8"), re.MULTILINE)
    if found is None:
        raise SystemExit("netmonitor.py da __version__ topilmadi")
    return ".".join(found.groups())


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    version = read_version()
    numbers = tuple(int(part) for part in version.split(".")) + (0,)
    Path(sys.argv[1]).write_text(TEMPLATE.format(numbers=numbers, version=version), encoding="utf-8")
    print(version)


if __name__ == "__main__":
    main()
