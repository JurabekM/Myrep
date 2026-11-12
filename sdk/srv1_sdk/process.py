"""Bola jarayonni Job Object ichida ishga tushirish va kuzatish.

Jarayon to'xtatilgan holda yaratiladi, jobga biriktiriladi va shundan keyingina
davom ettiriladi — shu sabab u tug'diradigan har bir jarayon ham job ichida
bo'ladi (xotira limiti va «ota o'lsa — bola ham o'ladi» kafolati butun daraxtga).
"""

import asyncio
import subprocess
from collections.abc import Callable, Mapping, Sequence
from contextlib import suppress
from pathlib import Path

import psutil

from srv1_sdk.jobobject import MemoryJob, resume_process

_CREATE_SUSPENDED = 0x00000004  # Win32 doimiysi; `subprocess` modulida yo'q
_FLAGS = subprocess.CREATE_NO_WINDOW | _CREATE_SUSPENDED
LineSink = Callable[[str], None]


async def spawn_in_job(
    args: Sequence[str],
    job: MemoryJob,
    *,
    cwd: Path | None = None,
    env: Mapping[str, str] | None = None,
    stdin: int | None = None,
    stdout: int | None = None,
    stderr: int | None = None,
    limit: int = 64 * 1024,
) -> asyncio.subprocess.Process:
    """`args` ni (`shell`siz) ishga tushiradi; jarayon birinchi buyrug'idan oldin jobda bo'ladi."""
    process = await asyncio.create_subprocess_exec(
        *args,
        cwd=cwd,
        env=None if env is None else dict(env),
        stdin=stdin,
        stdout=stdout,
        stderr=stderr,
        limit=limit,
        creationflags=_FLAGS,
    )
    try:
        job.assign(process.pid)
    except Exception:
        process.kill()
        raise
    resume_process(process.pid)
    return process


def tree_memory(pid: int) -> int:
    """Jarayon va uning barcha avlodlari egallagan xotira (Working Set), bayt."""
    try:
        root = psutil.Process(pid)
        members = [root, *root.children(recursive=True)]
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return 0
    total = 0
    for member in members:
        with suppress(psutil.NoSuchProcess, psutil.AccessDenied):
            total += member.memory_info().rss
    return total


class ManagedProcess:
    """Xotira limiti bilan ishlaydigan jarayon; chiqishi satrma-satr `on_line` ga beriladi."""

    def __init__(
        self,
        args: Sequence[str],
        *,
        cwd: Path,
        env: Mapping[str, str],
        memory_limit_mb: int,
        on_line: LineSink,
    ) -> None:
        self.args = tuple(args)
        self._cwd = cwd
        self._env = env
        self._limit_mb = memory_limit_mb
        self._on_line = on_line
        self._job: MemoryJob | None = None
        self._process: asyncio.subprocess.Process | None = None
        self._reader: asyncio.Task[None] | None = None

    @property
    def pid(self) -> int | None:
        return None if self._process is None else self._process.pid

    @property
    def returncode(self) -> int | None:
        return None if self._process is None else self._process.returncode

    @property
    def running(self) -> bool:
        return self._process is not None and self._process.returncode is None

    def memory_bytes(self) -> int:
        return tree_memory(self._process.pid) if self.running and self._process else 0

    async def start(self) -> None:
        self._job = MemoryJob(self._limit_mb * 1024 * 1024)
        try:
            self._process = await spawn_in_job(
                self.args,
                self._job,
                cwd=self._cwd,
                env=self._env,
                stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                limit=1024 * 1024,
            )
        except Exception:
            self._job.close()
            self._job = None
            raise
        self._reader = asyncio.create_task(self._pump())

    async def _pump(self) -> None:
        process = self._process
        if process is None or process.stdout is None:
            return
        while True:
            try:
                line = await process.stdout.readline()
            except (ValueError, asyncio.LimitOverrunError):
                continue  # juda uzun satr: tashlab ketiladi
            if not line:
                break
            self._on_line(line.decode("utf-8", "replace").rstrip("\r\n"))

    async def wait(self) -> int:
        """Jarayon tugashini kutadi va chiqish kodini qaytaradi."""
        if self._process is None:
            raise RuntimeError("jarayon ishga tushirilmagan")
        code = await self._process.wait()
        if self._reader is not None:
            await asyncio.gather(self._reader, return_exceptions=True)
        return code

    async def stop(self) -> None:
        """Butun jarayon daraxtini to'xtatadi (job yopiladi — ichidagi hammasi o'ladi)."""
        process, self._process = self._process, None
        job, self._job = self._job, None
        if process is not None and process.returncode is None:
            with suppress(ProcessLookupError):
                process.kill()
        if job is not None:
            job.close()
        if process is not None:
            await process.wait()
        if self._reader is not None:
            await asyncio.gather(self._reader, return_exceptions=True)
            self._reader = None
