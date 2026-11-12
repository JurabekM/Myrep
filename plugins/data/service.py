"""`data` xizmati: to'plamlarni import qilish, so'rovlar, hisobot (profil), eksport."""

import asyncio
import re
import time
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

from srv1_sdk.context import PluginContext

from .models import STORE_FILE, Dataset, Encoding, Store, load_store, save_store

if TYPE_CHECKING:
    from .engine import Engine

INBOX_DIR = "inbox"
DATASETS_DIR = "datasets"
EXPORTS_DIR = "exports"
TMP_DIR = "tmp"
_NAME_CLEAN = re.compile(r"[^a-z0-9_]+")


class DataError(Exception):
    """Amal bajarilmadi; `status` — klientga qaytadigan HTTP kodi."""

    def __init__(self, status: int, detail: str) -> None:
        super().__init__(detail)
        self.status = status
        self.detail = detail


def name_from_file(path: Path) -> str:
    """Fayl nomidan to'plam nomi: `Sotuvlar 2026.csv` -> `sotuvlar_2026`."""
    cleaned = _NAME_CLEAN.sub("_", path.stem.lower()).strip("_")[:48]
    if not cleaned or not cleaned[0].isalpha():
        cleaned = ("d_" + cleaned).rstrip("_")[:48]
    return cleaned


class DataService:
    def __init__(self, ctx: PluginContext) -> None:
        self.ctx = ctx
        self._store_file = ctx.data_path(STORE_FILE)
        self.inbox = ctx.data_path(INBOX_DIR)
        self.datasets_dir = ctx.data_path(DATASETS_DIR)
        self.exports_dir = ctx.data_path(EXPORTS_DIR)
        self.tmp_dir = ctx.data_path(TMP_DIR)
        self.store = Store()
        self.datasets: dict[str, Dataset] = {}
        self._engine: Engine | None = None
        self._query_lock = asyncio.Lock()
        self._imports: set[asyncio.Task[None]] = set()

    # --- hayot sikli ------------------------------------------------------
    def prepare(self) -> None:
        for directory in (self.inbox, self.datasets_dir, self.exports_dir, self.tmp_dir):
            directory.mkdir(parents=True, exist_ok=True)
        for leftover in self.tmp_dir.iterdir():
            if leftover.is_file():
                leftover.unlink(missing_ok=True)
        self.store = load_store(self._store_file)
        for dataset in self.store.datasets:
            if dataset.state == "importing":  # import paytida jarayon to'xtagan
                dataset.state, dataset.error = "failed", "import tugamasdan plagin to'xtadi"
            self.datasets[dataset.name] = dataset

    async def start(self) -> None:
        """DuckDB shu yerda yuklanmaydi — birinchi so'rovda (`engine`)."""

    async def stop(self) -> None:
        for task in list(self._imports):
            task.cancel()
        await asyncio.gather(*self._imports, return_exceptions=True)
        if self._engine is not None:
            self._engine.interrupt()
            async with self._query_lock:
                await asyncio.to_thread(self._engine.close)
            self._engine = None

    async def engine(self) -> "Engine":
        """Mexanizmni birinchi murojaatda yaratadi va tayyor to'plamlarni ro'yxatga oladi."""
        if self._engine is None:
            from .engine import Engine  # kech import: DuckDB faqat kerak bo'lganda yuklanadi

            def build() -> Engine:
                engine = Engine(
                    self.store.config, self.datasets_dir, self.exports_dir, self.tmp_dir
                )
                for dataset in self.datasets.values():
                    if dataset.state == "ready" and engine.dataset_file(dataset.name).is_file():
                        engine.register(dataset.name)
                return engine

            self._engine = await asyncio.to_thread(build)
        return self._engine

    async def _save(self) -> None:
        self.store.datasets = list(self.datasets.values())
        await asyncio.to_thread(save_store, self._store_file, self.store)

    # --- to'plamlar ---------------------------------------------------------
    def describe(self, dataset: Dataset) -> dict[str, Any]:
        return {
            "name": dataset.name,
            "state": dataset.state,
            "rows": dataset.rows,
            "columns": len(dataset.columns),
            "size": dataset.size,
            "source": dataset.source,
            "imported": dataset.imported or None,
            "seconds": dataset.seconds,
            "error": dataset.error,
        }

    def list_datasets(self) -> list[dict[str, Any]]:
        return [self.describe(self.datasets[name]) for name in sorted(self.datasets)]

    def _dataset(self, name: str, *, ready: bool = True) -> Dataset:
        dataset = self.datasets.get(name)
        if dataset is None:
            raise DataError(404, f"bunday to'plam yo'q: {name}")
        if ready and dataset.state != "ready":
            raise DataError(409, f"to'plam tayyor emas (holat: {dataset.state})")
        return dataset

    def schema(self, name: str) -> list[dict[str, str]]:
        return [column.model_dump() for column in self._dataset(name).columns]

    async def list_inbox(self) -> list[dict[str, Any]]:
        """`inbox` papkasidagi import qilsa bo'ladigan fayllar."""
        from .importer import SUPPORTED

        def scan() -> list[dict[str, Any]]:
            files = sorted(p for p in self.inbox.iterdir() if p.is_file())
            return [
                {"path": file.name, "size": file.stat().st_size, "modified": file.stat().st_mtime}
                for file in files
                if file.suffix.lower() in SUPPORTED
            ]

        return await asyncio.to_thread(scan)

    async def start_import(
        self, path: str, name: str, encoding: Encoding, separator: str, sheet: str
    ) -> dict[str, Any]:
        """Importni fonda boshlaydi va darhol qaytadi; holat to'plamlar ro'yxatida."""
        from .importer import SUPPORTED

        candidate = Path(path.strip())
        source = self.ctx.resolve_path(
            candidate if candidate.is_absolute() else self.inbox / candidate
        )
        if not await asyncio.to_thread(source.is_file):
            raise DataError(404, f"fayl topilmadi: {path}")
        if source.suffix.lower() not in SUPPORTED:
            raise DataError(400, f"qo'llab-quvvatlanmaydigan fayl turi: {source.suffix or '—'}")
        dataset_name = name.strip() or name_from_file(source)
        existing = self.datasets.get(dataset_name)
        if existing is not None and existing.state == "importing":
            raise DataError(409, f"to'plam hozir import qilinmoqda: {dataset_name}")
        dataset = Dataset(name=dataset_name, source=str(source))
        self.datasets[dataset_name] = dataset
        await self._save()
        task = asyncio.create_task(self._import(dataset, source, encoding, separator, sheet))
        self._imports.add(task)
        task.add_done_callback(self._imports.discard)
        return self.describe(dataset)

    async def _import(
        self, dataset: Dataset, source: Path, encoding: Encoding, separator: str, sheet: str
    ) -> None:
        from .importer import ImportFailed, import_file

        started = time.perf_counter()
        target = self.datasets_dir / f"{dataset.name}.parquet"
        try:
            # Eski nusxa DuckDB'da ochiq bo'lishi mumkin: avval ro'yxatdan chiqariladi.
            if self._engine is not None:
                async with self._query_lock:
                    await asyncio.to_thread(self._engine.unregister, dataset.name)
            result = await asyncio.to_thread(
                import_file,
                source,
                target,
                self.tmp_dir,
                encoding=encoding,
                separator=separator,
                sheet=sheet,
            )
        except ImportFailed as exc:
            dataset.state, dataset.error = "failed", str(exc)
        except OSError as exc:
            dataset.state, dataset.error = "failed", f"{type(exc).__name__}: {exc}"
        else:
            dataset.state, dataset.error = "ready", None
            dataset.rows, dataset.columns, dataset.size = result.rows, result.columns, result.size
            dataset.imported = time.time()
            if self._engine is not None:
                async with self._query_lock:
                    await asyncio.to_thread(self._engine.register, dataset.name)
        dataset.seconds = round(time.perf_counter() - started, 3)
        await self._save()
        self.ctx.publish(
            "imported",
            {
                "name": dataset.name,
                "state": dataset.state,
                "rows": dataset.rows,
                "error": dataset.error,
            },
        )

    async def remove(self, name: str) -> dict[str, Any]:
        dataset = self._dataset(name, ready=False)
        if dataset.state == "importing":
            raise DataError(409, "import tugashini kuting")
        target = self.datasets_dir / f"{name}.parquet"
        if self._engine is not None:
            async with self._query_lock:
                await asyncio.to_thread(self._engine.unregister, name)
        await asyncio.to_thread(target.unlink, True)
        del self.datasets[name]
        await self._save()
        await self.ctx.audit("file.delete", str(target), detail={"dataset": name})
        return {"removed": name}

    # --- so'rovlar ----------------------------------------------------------
    async def _guarded[T](
        self,
        engine: "Engine",
        work: Callable[..., T],
        *args: Any,  # noqa: ANN401
    ) -> T:
        """Ishni alohida oqimda bajaradi; vaqt chegarasidan oshsa so'rovni to'xtatadi."""
        from .engine import QueryError

        async with self._query_lock:
            task = asyncio.create_task(asyncio.to_thread(work, *args))
            try:
                return await asyncio.wait_for(
                    asyncio.shield(task), self.store.config.query_timeout_s
                )
            except TimeoutError:
                engine.interrupt()
                try:
                    await task
                except QueryError as exc:
                    raise DataError(exc.status, exc.detail) from exc
                raise DataError(408, "so'rov vaqt chegarasidan oshdi") from None
            except QueryError as exc:
                raise DataError(exc.status, exc.detail) from exc

    async def query(self, sql: str, limit: int, offset: int) -> dict[str, Any]:
        engine = await self.engine()
        capped = min(limit, self.store.config.max_rows)
        result = await self._guarded(engine, engine.query, sql, capped, offset)
        return result.as_dict()

    async def preview(self, name: str, limit: int) -> dict[str, Any]:
        self._dataset(name)
        # `name` NAME_PATTERN bo'yicha tekshirilgan va mavjud to'plam nomi.
        return await self.query(f'SELECT * FROM "{name}"', limit, 0)  # noqa: S608

    async def profile(self, name: str) -> dict[str, Any]:
        """Hisobot: har ustun uchun tur, min/max, noyob qiymatlar, o'rtacha, bo'shlar ulushi."""
        self._dataset(name)
        return await self.query(f'SUMMARIZE "{name}"', 1000, 0)

    async def export(self, sql: str, name: str) -> dict[str, Any]:
        """So'rov natijasini `exports/<name>.csv` ga yozadi."""
        engine = await self.engine()
        target = self.ctx.data_path(EXPORTS_DIR, f"{name}.csv")
        rows = await self._guarded(engine, self._copy, engine, sql, target, False)
        size = (await asyncio.to_thread(target.stat)).st_size
        return {"file": str(target), "rows": rows, "size": size}

    async def save_as(self, sql: str, name: str) -> dict[str, Any]:
        """So'rov natijasini yangi to'plam sifatida saqlaydi."""
        if name in self.datasets:
            raise DataError(409, f"bunday to'plam bor: {name}")
        engine = await self.engine()
        target = engine.dataset_file(name)
        rows = await self._guarded(engine, self._copy, engine, sql, target, True)

        from .importer import _describe  # pyright: ignore[reportPrivateUsage]

        described = await asyncio.to_thread(_describe, target)
        dataset = Dataset(
            name=name,
            state="ready",
            source="(so'rov natijasi)",
            rows=rows,
            columns=described.columns,
            size=described.size,
            imported=time.time(),
        )
        self.datasets[name] = dataset
        async with self._query_lock:
            await asyncio.to_thread(engine.register, name)
        await self._save()
        return self.describe(dataset)

    @staticmethod
    def _copy(engine: "Engine", sql: str, target: Path, parquet: bool) -> int:
        from .engine import QueryError

        try:
            return engine.copy_to(sql, target, parquet=parquet)
        except QueryError:
            target.unlink(missing_ok=True)
            raise

    # --- holat --------------------------------------------------------------
    async def status(self) -> dict[str, Any]:
        ready = [dataset for dataset in self.datasets.values() if dataset.state == "ready"]
        return {
            "datasets": len(self.datasets),
            "ready": len(ready),
            "importing": sum(d.state == "importing" for d in self.datasets.values()),
            "failed": sum(d.state == "failed" for d in self.datasets.values()),
            "rows": sum(dataset.rows for dataset in ready),
            "size": sum(dataset.size for dataset in ready),
            "engine_loaded": self._engine is not None,
            "memory_limit": self.store.config.memory_limit,
            "query_timeout_s": self.store.config.query_timeout_s,
            "inbox": str(self.inbox),
        }
