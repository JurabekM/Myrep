"""Shared-folder transport (LAN drive, USB, OneDrive/Yandex.Disk folder).

Works with no account and no internet: every device appends numbered JSON files
to one directory. A tiny lock file keeps the sequence strictly monotonic, so all
devices observe the same order — the same guarantee the SQL backends give.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

from app.sync.transports.base import Change, TransportError

LOCK_TIMEOUT = 10.0
STALE_LOCK_SECONDS = 30.0


class FolderTransport:
    """Append-only change log stored as files in a shared directory."""

    key = "folder"

    def __init__(self, path: str | Path, tenant: str = "default") -> None:
        self.root = Path(path)
        self.tenant = tenant or "default"

    # -- helpers -------------------------------------------------------------- #
    @property
    def _dir(self) -> Path:
        return self.root / self.tenant

    @property
    def _seq_file(self) -> Path:
        return self._dir / "_seq.txt"

    @property
    def _lock_file(self) -> Path:
        return self._dir / "_seq.lock"

    def _ensure_dir(self) -> None:
        try:
            self._dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise TransportError(f"Papkani ochib bo'lmadi: {exc}") from exc

    def _acquire_lock(self) -> None:
        deadline = time.monotonic() + LOCK_TIMEOUT
        while True:
            try:
                handle = os.open(self._lock_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(handle, str(os.getpid()).encode())
                os.close(handle)
                return
            except FileExistsError:
                try:
                    age = time.time() - self._lock_file.stat().st_mtime
                    if age > STALE_LOCK_SECONDS:
                        self._lock_file.unlink(missing_ok=True)
                        continue
                except OSError:
                    pass
                if time.monotonic() > deadline:
                    raise TransportError("Sinxronizatsiya papkasi band (lock timeout)") from None
                time.sleep(0.05)
            except OSError as exc:
                raise TransportError(f"Lock xatosi: {exc}") from exc

    def _release_lock(self) -> None:
        self._lock_file.unlink(missing_ok=True)

    def _reserve(self, count: int) -> int:
        """Reserve ``count`` sequence numbers and return the first one."""
        self._acquire_lock()
        try:
            current = 0
            if self._seq_file.exists():
                try:
                    current = int(self._seq_file.read_text(encoding="utf-8").strip() or "0")
                except ValueError:
                    current = 0
            self._seq_file.write_text(str(current + count), encoding="utf-8")
            return current + 1
        finally:
            self._release_lock()

    # -- transport API -------------------------------------------------------- #
    def describe(self) -> str:
        return f"{self.root}  ({self.tenant})"

    def check(self) -> str:
        self._ensure_dir()
        probe = self._dir / ".probe"
        try:
            probe.write_text("ok", encoding="utf-8")
            probe.unlink(missing_ok=True)
        except OSError as exc:
            raise TransportError(f"Papkaga yozib bo'lmadi: {exc}") from exc
        return f"{len(list(self._dir.glob('*.json')))} ta o'zgarish fayli"

    def push(self, changes: list[Change]) -> int:
        if not changes:
            return 0
        self._ensure_dir()
        start = self._reserve(len(changes))
        for offset, change in enumerate(changes):
            seq = start + offset
            body = change.to_wire(self.tenant)
            target = self._dir / f"{seq:012d}.json"
            temporary = self._dir / f".{seq:012d}.tmp"
            try:
                temporary.write_text(json.dumps(body, ensure_ascii=False), encoding="utf-8")
                temporary.replace(target)
            except OSError as exc:
                raise TransportError(f"Faylni yozib bo'lmadi: {exc}") from exc
        return len(changes)

    def pull(self, after: str, limit: int = 500) -> list[Change]:
        self._ensure_dir()
        try:
            last = int(after or 0)
        except ValueError:
            last = 0
        result: list[Change] = []
        for path in sorted(self._dir.glob("*.json")):
            try:
                seq = int(path.stem)
            except ValueError:
                continue
            if seq <= last:
                continue
            try:
                row = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if row.get("tenant") not in (None, self.tenant):
                continue
            result.append(Change.from_wire(row, str(seq)))
            if len(result) >= limit:
                break
        return result
