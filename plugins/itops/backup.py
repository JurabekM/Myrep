"""Zaxira nusxa: ma'lumotlar papkasini zip arxivga yig'adi (bloklovchi — alohida oqimda).

SQLite bazalari oddiy nusxalanmaydi (yozilayotgan baza yarim holatda tushishi
mumkin) — ular SQLite'ning o'z `backup` usuli bilan izchil holatda olinadi.
Token va vaqtinchalik fayllar arxivga kirmaydi.
"""

import json
import os
import sqlite3
import time
import zipfile
from collections.abc import Iterator
from contextlib import closing, suppress
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

PREFIX = "srv1-backup-"
MANIFEST_NAME = "backup.json"
_SQLITE_MAGIC = b"SQLite format 3\x00"
# Sirlar va qayta yaratiladigan fayllar.
_SKIP_NAMES = frozenset({"auth.token"})
_SKIP_SUFFIXES = (".token", ".tmp", "-wal", "-shm", "-journal")
_SKIP_DIRS = frozenset({"tmp", "__pycache__"})


@dataclass
class BackupOptions:
    projects: bool = False
    logs: bool = False
    # Arxivga kirmaydigan papkalar (zaxiralar papkasining o'zi).
    exclude: tuple[Path, ...] = ()


@dataclass
class BackupResult:
    path: Path
    files: int = 0
    source_bytes: int = 0
    databases: list[str] = field(default_factory=list[str])
    skipped: list[str] = field(default_factory=list[str])
    seconds: float = 0.0

    def describe(self) -> dict[str, Any]:
        return {
            "name": self.path.name,
            "size": self.path.stat().st_size if self.path.is_file() else 0,
            "files": self.files,
            "source_bytes": self.source_bytes,
            "databases": len(self.databases),
            "skipped": len(self.skipped),
            "seconds": round(self.seconds, 2),
        }


def is_sqlite(path: Path) -> bool:
    try:
        with path.open("rb") as fh:
            return fh.read(len(_SQLITE_MAGIC)) == _SQLITE_MAGIC
    except OSError:
        return False


def _excluded_top(options: BackupOptions) -> set[str]:
    names: set[str] = set()
    if not options.projects:
        names.add("projects")
    if not options.logs:
        names.add("logs")
    return names


def iter_files(root: Path, options: BackupOptions) -> Iterator[Path]:
    """Arxivga kiradigan fayllar. Havolalar (symlink/junction) kuzatilmaydi."""
    excluded = {path.resolve() for path in options.exclude}
    top = _excluded_top(options)
    for current, dirs, files in os.walk(root, followlinks=False):
        here = Path(current)
        keep: list[str] = []
        for name in sorted(dirs):
            path = here / name
            if name.lower() in _SKIP_DIRS or path.is_symlink() or path.is_junction():
                continue
            if here == root and name in top:
                continue
            if path.resolve() in excluded:
                continue
            keep.append(name)
        dirs[:] = keep
        for name in sorted(files):
            lowered = name.lower()
            if lowered in _SKIP_NAMES or lowered.endswith(_SKIP_SUFFIXES):
                continue
            path = here / name
            if not path.is_symlink():
                yield path


def _snapshot_sqlite(source: Path, target: Path) -> None:
    """Bazaning izchil nusxasi (WAL'dagi yozuvlar bilan birga)."""
    uri = f"{source.as_uri()}?mode=ro"
    with (
        closing(sqlite3.connect(uri, uri=True, timeout=10)) as src,
        closing(sqlite3.connect(target)) as dst,
    ):
        src.backup(dst)


def create_backup(root: Path, destination: Path, options: BackupOptions) -> BackupResult:
    """Arxiv yaratadi: avval `.tmp` ga yozadi, tekshiradi, so'ng nomini almashtiradi."""
    started = time.monotonic()
    destination.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    final = destination / f"{PREFIX}{stamp}.zip"
    serial = 1
    while final.exists():  # bir soniyada ikkinchi nusxa
        serial += 1
        final = destination / f"{PREFIX}{stamp}-{serial}.zip"
    partial = final.with_suffix(".zip.tmp")
    scratch = destination / f"{final.stem}.sqlite.tmp"
    result = BackupResult(final)
    try:
        with zipfile.ZipFile(partial, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            for path in iter_files(root, options):
                name = path.relative_to(root).as_posix()
                if name == MANIFEST_NAME:
                    continue  # tiklangan papkada qolgan eski tavsif; yangisi pastda yoziladi
                try:
                    if is_sqlite(path):
                        _snapshot_sqlite(path, scratch)
                        archive.write(scratch, name)
                        result.databases.append(name)
                    else:
                        archive.write(path, name)
                    result.source_bytes += path.stat().st_size
                    result.files += 1
                except (OSError, sqlite3.Error) as exc:
                    result.skipped.append(f"{name}: {exc}")
            manifest = {
                "created": time.time(),
                "files": result.files,
                "source_bytes": result.source_bytes,
                "databases": result.databases,
                "skipped": result.skipped,
                "projects": options.projects,
                "logs": options.logs,
            }
            archive.writestr(MANIFEST_NAME, json.dumps(manifest, ensure_ascii=False, indent=2))
        with zipfile.ZipFile(partial) as archive:
            broken = archive.testzip()
        if broken is not None:
            raise OSError(f"arxiv buzuq chiqdi: {broken}")
        partial.replace(final)
    finally:
        for leftover in (partial, scratch):
            with suppress(OSError):
                leftover.unlink(missing_ok=True)
    result.seconds = time.monotonic() - started
    return result


def _order(name: str) -> tuple[str, int]:
    """Saralash kaliti: (vaqt tamg'asi, shu soniyadagi tartib raqami)."""
    stamp, _, serial = name.removeprefix(PREFIX).removesuffix(".zip").partition("-")
    day, _, number = serial.partition("-")
    return f"{stamp}-{day}", int(number) if number.isdigit() else 1


def list_backups(destination: Path) -> list[dict[str, Any]]:
    """Mavjud arxivlar, yangisi birinchi."""
    if not destination.is_dir():
        return []
    rows: list[dict[str, Any]] = []
    for path in destination.glob(f"{PREFIX}*.zip"):
        stat = path.stat()
        rows.append({"name": path.name, "size": stat.st_size, "created": stat.st_mtime})
    rows.sort(key=lambda row: _order(str(row["name"])), reverse=True)
    return rows


def prune(destination: Path, keep: int) -> list[str]:
    """Eng yangi `keep` tasidan boshqasini o'chiradi; o'chirilgan nomlarni qaytaradi."""
    removed: list[str] = []
    for row in list_backups(destination)[keep:]:
        with suppress(OSError):
            (destination / row["name"]).unlink()
            removed.append(row["name"])
    return removed
