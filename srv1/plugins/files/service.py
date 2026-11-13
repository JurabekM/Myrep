"""Fayllar xizmati: indeksni yuritish, papkalarni kuzatish, amallar va savat."""

import asyncio
import itertools
import shutil
import time
from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from pathlib import Path
from typing import Any

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer
from watchdog.observers.api import BaseObserver

from srv1_sdk.context import PluginContext
from srv1_sdk.pathsafe import PathTraversalError, check_component, safe_join
from srv1_sdk.types import PermissionDenied

from .index import Entry, FileIndex
from .scanner import entry_for, is_link, iter_entries

SCAN_BATCH = 2000
FLUSH_DELAY_S = 0.5
EVENT_SAMPLE = 20
LIBRARY_DIR = "library"
TRASH_DIR = "trash"
INDEX_FILE = "index.db"


class FileOpError(Exception):
    """Amal bajarilmadi; `status` — klientga qaytadigan HTTP kodi."""

    def __init__(self, status: int, detail: str) -> None:
        super().__init__(detail)
        self.status = status
        self.detail = detail


class _Watcher(FileSystemEventHandler):
    """watchdog oqimida ishlaydi: o'zgargan yo'llarni `sink` ga uzatadi."""

    def __init__(self, root_id: int, root: Path, sink: Callable[[int, str], None]) -> None:
        self._root_id = root_id
        self._root = root
        self._sink = sink

    def on_any_event(self, event: FileSystemEvent) -> None:
        for raw in (event.src_path, event.dest_path):
            text = raw.decode("utf-8", "replace") if isinstance(raw, bytes) else str(raw)
            if not text:
                continue
            try:
                relative = Path(text).relative_to(self._root).as_posix()
            except ValueError:
                continue
            if relative != ".":
                self._sink(self._root_id, relative)


def _take(entries: Iterator[Entry], count: int) -> list[Entry]:
    return list(itertools.islice(entries, count))


class FilesService:
    def __init__(self, ctx: PluginContext) -> None:
        self.ctx = ctx
        self.library = ctx.data_path(LIBRARY_DIR)
        self.trash_dir = ctx.data_path(TRASH_DIR)
        self.roots: list[Path] = [
            self.library,
            *(p.resolve() for p in ctx.manifest.permissions.paths),
        ]
        self._db_thread = ThreadPoolExecutor(max_workers=1, thread_name_prefix="files-db")
        self._index: FileIndex | None = None
        self._observer: BaseObserver | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._pending: set[tuple[int, str]] = set()
        self._flush_handle: asyncio.TimerHandle | None = None
        self._tasks: set[asyncio.Task[Any]] = set()
        self._scan_lock = asyncio.Lock()
        self._gen = 0
        self.scanning = False
        self.last_scan_ts: float | None = None
        self.last_scan_seconds: float | None = None
        self.watching = 0

    # --- hayot sikli ------------------------------------------------------
    def prepare(self) -> None:
        """Papkalarni yaratadi (sinxron; event loop'dan oldin chaqiriladi)."""
        self.library.mkdir(parents=True, exist_ok=True)
        self.trash_dir.mkdir(parents=True, exist_ok=True)

    async def start(self) -> None:
        self._loop = asyncio.get_running_loop()
        self._index = await self._db(FileIndex, self.ctx.data_path(INDEX_FILE))
        self._gen = await self._db(self.index.max_gen)
        self._start_watching()
        self._spawn(self.rescan())

    async def stop(self) -> None:
        if self._flush_handle is not None:
            self._flush_handle.cancel()
        observer, self._observer = self._observer, None
        if observer is not None:
            observer.stop()
            await asyncio.to_thread(observer.join, 5)
        for task in list(self._tasks):
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        if self._index is not None:
            await self._db(self._index.close)
            self._index = None
        self._db_thread.shutdown(wait=False)

    @property
    def index(self) -> FileIndex:
        if self._index is None:
            raise FileOpError(503, "indeks hali tayyor emas")
        return self._index

    async def _db[T](self, func: Callable[..., T], *args: Any) -> T:  # noqa: ANN401
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self._db_thread, partial(func, *args))

    def _spawn(self, coro: Any) -> None:  # noqa: ANN401
        task: asyncio.Task[Any] = asyncio.ensure_future(coro)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    # --- skanerlash ---------------------------------------------------------
    async def rescan(self) -> dict[str, Any]:
        """Hamma ildizni to'liq aylanib chiqadi. Bir vaqtda faqat bitta skanerlash."""
        async with self._scan_lock:
            self.scanning = True
            started = time.monotonic()
            try:
                self._gen += 1
                seen = 0
                for root_id, root in enumerate(self.roots):
                    seen += await self._scan_root(root_id, root, self._gen)
                await self._db(self.index.drop_other_roots, len(self.roots))
            finally:
                self.scanning = False
            self.last_scan_ts = time.time()
            self.last_scan_seconds = round(time.monotonic() - started, 3)
        summary = {"entries": seen, "seconds": self.last_scan_seconds}
        self.ctx.publish("scan", summary)
        return summary

    async def _scan_root(self, root_id: int, root: Path, gen: int) -> int:
        seen = 0
        if await asyncio.to_thread(root.is_dir):
            entries = iter_entries(root_id, root)
            while batch := await asyncio.to_thread(_take, entries, SCAN_BATCH):
                seen += await self._db(self.index.upsert_many, batch, gen)
        await self._db(self.index.drop_stale, root_id, gen)
        return seen

    # --- kuzatuv ------------------------------------------------------------
    def _start_watching(self) -> None:
        observer = Observer()
        for root_id, root in enumerate(self.roots):
            if root.is_dir():
                observer.schedule(
                    _Watcher(root_id, root, self._from_thread), str(root), recursive=True
                )
                self.watching += 1
        observer.daemon = True
        observer.start()
        self._observer = observer

    def _from_thread(self, root_id: int, relpath: str) -> None:
        loop = self._loop
        if loop is not None and not loop.is_closed():
            loop.call_soon_threadsafe(self._enqueue, root_id, relpath)

    def _enqueue(self, root_id: int, relpath: str) -> None:
        """O'zgarishlarni to'playdi: bir yo'ldagi ko'p hodisa bitta yangilanishga birlashadi."""
        self._pending.add((root_id, relpath))
        if self._flush_handle is None and self._loop is not None:
            self._flush_handle = self._loop.call_later(FLUSH_DELAY_S, self._start_flush)

    def _start_flush(self) -> None:
        self._flush_handle = None
        pending, self._pending = self._pending, set()
        if pending:
            self._spawn(self._flush(pending))

    async def _flush(self, pending: set[tuple[int, str]]) -> None:
        for root_id, relpath in sorted(pending):
            await self.reindex(root_id, relpath)
        sample = [f"{root_id}:{relpath}" for root_id, relpath in sorted(pending)[:EVENT_SAMPLE]]
        self.ctx.publish("changed", {"count": len(pending), "paths": sample})

    async def reindex(self, root_id: int, relpath: str) -> None:
        """Bitta yo'lni diskdagi holatga keltiradi (yo'q bo'lsa indeksdan o'chiradi)."""
        if not relpath:
            return
        root = self.roots[root_id]
        entry = await asyncio.to_thread(entry_for, root_id, root, relpath)
        if entry is None:
            await self._db(self.index.delete_path, root_id, relpath)
            return
        entries = [entry]
        if entry.is_dir and not await self._db(self.index.contains, root_id, relpath):
            # Ko'chirib keltirilgan papka: ichidagilar uchun alohida hodisa kelmaydi.
            entries += await asyncio.to_thread(list, iter_entries(root_id, root, relpath))
        await self._db(self.index.upsert_many, entries, self._gen)

    # --- yo'llar ------------------------------------------------------------
    def resolve(self, root_id: int, relpath: str) -> tuple[Path, str]:
        """(mutlaq yo'l, ildizga nisbatan yo'l). Ildizdan chiqsa `PermissionDenied`."""
        if not 0 <= root_id < len(self.roots):
            raise FileOpError(404, f"bunday ildiz yo'q: {root_id}")
        root = self.roots[root_id]
        parts = [part for part in relpath.replace("\\", "/").split("/") if part]
        try:
            path = safe_join(root, *parts) if parts else root
        except PathTraversalError as exc:
            self.ctx.log("warning", "permission_denied", kind="path", target=relpath)
            raise PermissionDenied(f"yo'l ruxsat etilgan papkadan tashqarida: {relpath}") from exc
        relative = path.relative_to(root).as_posix()
        return path, "" if relative == "." else relative

    # --- o'qish -------------------------------------------------------------
    async def status(self) -> dict[str, Any]:
        files, dirs = await self._db(self.index.counts)
        trash = await self._db(self.index.trash_list)
        return {
            "files": files,
            "dirs": dirs,
            "roots": len(self.roots),
            "watching": self.watching,
            "trash": len(trash),
            "scanning": self.scanning,
            "last_scan": self.last_scan_ts,
            "last_scan_seconds": self.last_scan_seconds,
        }

    async def list_roots(self) -> list[dict[str, Any]]:
        counts = await self._db(self.index.count_by_root)
        exists = await asyncio.to_thread(lambda: [root.is_dir() for root in self.roots])
        return [
            {
                "root": root_id,
                "label": LIBRARY_DIR if root_id == 0 else root.name or str(root),
                "path": str(root),
                "files": counts.get(root_id, 0),
                "exists": exists[root_id],
            }
            for root_id, root in enumerate(self.roots)
        ]

    async def list_dir(self, root_id: int, relpath: str) -> list[dict[str, Any]]:
        path, relative = self.resolve(root_id, relpath)

        def read() -> tuple[list[Entry], list[str]]:
            if not path.is_dir():
                raise FileOpError(404, f"papka topilmadi: {relpath}")
            children = sorted(path.iterdir(), key=lambda child: child.name)
            links = [child.name for child in children if is_link(child)]
            found = (
                entry_for(root_id, self.roots[root_id], f"{relative}/{child.name}".lstrip("/"))
                for child in children
            )
            return [entry for entry in found if entry is not None], links

        entries, links = await asyncio.to_thread(read)
        entries.sort(key=lambda entry: (not entry.is_dir, entry.name.lower()))
        rows = [entry.as_dict() | {"link": False} for entry in entries]
        # Havolalar ichiga kirilmaydi va indeksga tushmaydi; faqat borligi ko'rsatiladi.
        for name in links:
            rows.append(
                {
                    "root": root_id,
                    "path": f"{relative}/{name}".lstrip("/"),
                    "name": name,
                    "folder": relative,
                    "ext": "",
                    "size": None,
                    "mtime": None,
                    "is_dir": False,
                    "link": True,
                }
            )
        return rows

    async def search(self, query: str, **filters: Any) -> list[dict[str, Any]]:  # noqa: ANN401
        entries = await self._db(partial(self.index.search, query, **filters))
        return [entry.as_dict() for entry in entries]

    # --- amallar ------------------------------------------------------------
    async def mkdir(self, root_id: int, relpath: str) -> dict[str, Any]:
        path, relative = self.resolve(root_id, relpath)
        if not relative:
            raise FileOpError(400, "papka nomi berilmagan")

        def create() -> None:
            if path.exists():
                raise FileOpError(409, f"allaqachon bor: {relative}")
            if not path.parent.is_dir():
                raise FileOpError(404, f"ota papka topilmadi: {relative}")
            path.mkdir()

        await asyncio.to_thread(create)
        await self.reindex(root_id, relative)
        return {"root": root_id, "path": relative}

    async def rename(self, root_id: int, relpath: str, new_name: str) -> dict[str, Any]:
        path, relative = self.resolve(root_id, relpath)
        name = new_name.strip()
        if not relative:
            raise FileOpError(400, "ildiz papkaning nomini o'zgartirib bo'lmaydi")
        try:
            if not name or name in (".", "..") or any(char in name for char in '/\\:*?"<>|'):
                raise PathTraversalError(name)
            check_component(name)
        except PathTraversalError as exc:
            raise FileOpError(400, f"yaroqsiz nom: {new_name!r}") from exc
        target, target_rel = self.resolve(root_id, f"{relative}/../{name}")

        def move() -> None:
            if not path.exists():
                raise FileOpError(404, f"topilmadi: {relative}")
            if target.exists():
                raise FileOpError(409, f"allaqachon bor: {target_rel}")
            path.rename(target)

        await asyncio.to_thread(move)
        await self.ctx.audit("file.rename", str(path), detail={"to": str(target)})
        await self.reindex(root_id, relative)
        await self.reindex(root_id, target_rel)
        return {"root": root_id, "path": target_rel}

    async def transfer(
        self, root_id: int, relpath: str, dest_root: int, dest_path: str, *, copy: bool
    ) -> dict[str, Any]:
        """Fayl yoki papkani `dest_path` papkasi ichiga ko'chiradi yoki nusxalaydi."""
        source, relative = self.resolve(root_id, relpath)
        dest_dir, dest_rel = self.resolve(dest_root, dest_path)
        if not relative:
            raise FileOpError(400, "ildiz papkani ko'chirib bo'lmaydi")
        target, target_rel = self.resolve(dest_root, f"{dest_rel}/{source.name}")

        def run() -> None:
            if not source.exists():
                raise FileOpError(404, f"topilmadi: {relative}")
            if not dest_dir.is_dir():
                raise FileOpError(404, f"manzil papka topilmadi: {dest_path}")
            if target.exists():
                raise FileOpError(409, f"manzilda allaqachon bor: {target_rel}")
            if source.is_dir() and target.is_relative_to(source):
                raise FileOpError(400, "papkani o'zining ichiga ko'chirib bo'lmaydi")
            if not copy:
                shutil.move(source, target)
            elif source.is_dir():
                shutil.copytree(source, target, symlinks=True)
            else:
                shutil.copy2(source, target)

        await asyncio.to_thread(run)
        action = "file.copy" if copy else "file.move"
        await self.ctx.audit(action, str(source), detail={"to": str(target)})
        if not copy:
            await self.reindex(root_id, relative)
        await self.reindex(dest_root, target_rel)
        return {"root": dest_root, "path": target_rel}

    # --- savat --------------------------------------------------------------
    async def trash(self, root_id: int, relpath: str) -> dict[str, Any]:
        path, relative = self.resolve(root_id, relpath)
        if not relative:
            raise FileOpError(400, "ildiz papkani o'chirib bo'lmaydi")
        entry = await asyncio.to_thread(entry_for, root_id, self.roots[root_id], relative)
        if entry is None:
            raise FileOpError(404, f"topilmadi: {relative}")
        trash_id = await self._db(self.index.trash_add, entry, time.time())
        slot = self.trash_dir / str(trash_id)

        def move() -> None:
            slot.mkdir()
            shutil.move(path, slot / entry.name)

        try:
            await asyncio.to_thread(move)
        except OSError as exc:
            await self._db(self.index.trash_remove, trash_id)
            await self.ctx.audit("file.trash", str(path), ok=False, detail={"error": str(exc)})
            raise FileOpError(500, f"savatga ko'chirib bo'lmadi: {exc}") from exc
        await self.ctx.audit("file.trash", str(path), detail={"trash_id": trash_id})
        await self.reindex(root_id, relative)
        return {"id": trash_id}

    async def unlink(self, root_id: int, relpath: str) -> dict[str, Any]:
        """Simvolik havola yoki junction'ning O'ZINI olib tashlaydi; nishoniga tegilmaydi.

        Savatga tushmaydi (havolani ko'chirish nishonni ko'chirib yuborishi mumkin).
        """
        parts = [part for part in relpath.replace("\\", "/").split("/") if part]
        if not parts:
            raise FileOpError(400, "havola yo'li berilmagan")
        # Ota papka odatdagidek tekshiriladi (ildiz ichida, o'zi havola orqali emas);
        # oxirgi bo'lak esa ochilmaydi — aynan havolaning o'zi kerak.
        parent, parent_rel = self.resolve(root_id, "/".join(parts[:-1]))
        name = parts[-1]
        if name in (".", "..") or any(sep in name for sep in ("/", "\\", ":")):
            raise FileOpError(400, f"yaroqsiz nom: {name}")
        link = parent / name
        relative = f"{parent_rel}/{name}".lstrip("/")

        def remove() -> None:
            if not is_link(link):
                raise FileOpError(400, f"bu havola emas: {relative}")
            try:
                link.unlink()
            except (PermissionError, IsADirectoryError):
                link.rmdir()  # papka havolasi va junction: faqat havola yozuvi ketadi

        try:
            await asyncio.to_thread(remove)
        except OSError as exc:
            await self.ctx.audit("file.unlink", str(link), ok=False, detail={"error": str(exc)})
            raise FileOpError(500, f"havolani olib tashlab bo'lmadi: {exc}") from exc
        await self.ctx.audit("file.unlink", str(link))
        return {"path": relative, "removed": True}

    async def list_trash(self) -> list[dict[str, Any]]:
        return [item.as_dict() for item in await self._db(self.index.trash_list)]

    async def restore(self, trash_id: int) -> dict[str, Any]:
        item = await self._db(self.index.trash_get, trash_id)
        if item is None:
            raise FileOpError(404, f"savatda yo'q: {trash_id}")
        target, relative = self.resolve(item.root, item.relpath)
        slot = self.trash_dir / str(trash_id)

        def move() -> None:
            if target.exists():
                raise FileOpError(409, f"asl joyida allaqachon bor: {relative}")
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(slot / item.name, target)
            shutil.rmtree(slot, ignore_errors=True)

        await asyncio.to_thread(move)
        await self._db(self.index.trash_remove, trash_id)
        await self.ctx.audit("file.restore", str(target), detail={"trash_id": trash_id})
        await self.reindex(item.root, relative)
        return {"root": item.root, "path": relative}

    async def purge(self, trash_id: int | None) -> dict[str, Any]:
        """Savatdan butunlay o'chiradi (`None` — hammasini). Qaytarib bo'lmaydi."""
        items = await self._db(self.index.trash_list)
        chosen = [item for item in items if trash_id is None or item.id == trash_id]
        if trash_id is not None and not chosen:
            raise FileOpError(404, f"savatda yo'q: {trash_id}")
        for item in chosen:
            await asyncio.to_thread(shutil.rmtree, self.trash_dir / str(item.id), True)
            await self._db(self.index.trash_remove, item.id)
            original = (
                self.roots[item.root] / item.relpath
                if item.root < len(self.roots)
                else item.relpath
            )
            await self.ctx.audit("file.delete", str(original), detail={"trash_id": item.id})
        return {"purged": len(chosen)}
