"""Papkani aylanib chiqish. Simvolik havola va junction'larga kirilmaydi."""

import os
from collections.abc import Iterator
from pathlib import Path

from .index import Entry


def _is_link(entry: os.DirEntry[str]) -> bool:
    return entry.is_symlink() or entry.is_junction()


def make_entry(root_id: int, relpath: str, name: str, stat: os.stat_result, is_dir: bool) -> Entry:
    ext = "" if is_dir or "." not in name else name.rsplit(".", 1)[1].lower()
    return Entry(
        root=root_id,
        relpath=relpath,
        name=name,
        ext=ext,
        size=0 if is_dir else stat.st_size,
        mtime=stat.st_mtime,
        is_dir=is_dir,
    )


def is_link(path: Path) -> bool:
    """Simvolik havola yoki junction (nishoniga qaralmaydi)."""
    try:
        return path.is_symlink() or path.is_junction()
    except OSError:
        return False


def entry_for(root_id: int, root: Path, relpath: str) -> Entry | None:
    """Bitta yo'l uchun yozuv; yo'q, havola yoki o'qib bo'lmasa `None`."""
    path = root / relpath
    try:
        if path.is_symlink() or path.is_junction():
            return None
        stat = path.stat()
    except OSError:
        return None
    return make_entry(root_id, relpath, path.name, stat, path.is_dir())


def iter_entries(root_id: int, root: Path, start: str = "") -> Iterator[Entry]:
    """`root/start` ostidagi hamma fayl va papkalar (o'qib bo'lmaganlari tashlab ketiladi)."""
    stack = [start]
    while stack:
        rel_dir = stack.pop()
        try:
            scanner = os.scandir(root / rel_dir if rel_dir else root)
        except OSError:
            continue
        with scanner:
            for entry in scanner:
                if _is_link(entry):
                    continue
                relpath = f"{rel_dir}/{entry.name}" if rel_dir else entry.name
                try:
                    is_dir = entry.is_dir(follow_symlinks=False)
                    stat = entry.stat(follow_symlinks=False)
                except OSError:
                    continue
                yield make_entry(root_id, relpath, entry.name, stat, is_dir)
                if is_dir:
                    stack.append(relpath)
