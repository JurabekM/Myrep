"""`PluginContext` — plaginning yadro bilan yagona aloqa nuqtasi."""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, Protocol

from srv1_sdk.manifest import PluginManifest
from srv1_sdk.pathsafe import PathTraversalError, resolve_within, safe_join
from srv1_sdk.types import PermissionDenied

if TYPE_CHECKING:
    from srv1_sdk.process import ManagedProcess

LogLevel = Literal["debug", "info", "warning", "error"]
_TOPIC_RE = re.compile(r"[a-z0-9_.-]{1,64}")


def plugin_topic_prefix(name: str) -> str:
    return f"plugin.{name}."


class Backend(Protocol):
    """Kontekst ortidagi transport: jarayon ichida — to'g'ridan-to'g'ri, bolada — stdio."""

    def publish(self, topic: str, data: Mapping[str, Any]) -> None: ...

    async def audit(
        self, action: str, target: str, ok: bool, detail: Mapping[str, Any]
    ) -> None: ...

    def log(self, level: LogLevel, event: str, fields: Mapping[str, Any]) -> None: ...


class PluginContext:
    """Ruxsat tekshiruvli resurslar, hodisa nashri, audit va jurnal."""

    def __init__(
        self,
        manifest: PluginManifest,
        data_dir: Path,
        backend: Backend,
        projects_dir: Path | None = None,
    ) -> None:
        self.manifest = manifest
        self.name = manifest.name
        self.data_dir = data_dir
        self._backend = backend
        self._projects_dir = projects_dir

    @property
    def projects_dir(self) -> Path:
        """Umumiy loyihalar papkasi; manifestda `permissions.projects = true` bo'lishi shart."""
        if not self.manifest.permissions.projects or self._projects_dir is None:
            raise self._denied("projects", "projects")
        return self._projects_dir

    def _roots(self) -> tuple[Path, ...]:
        roots = (self.data_dir, *self.manifest.permissions.paths)
        if self.manifest.permissions.projects and self._projects_dir is not None:
            roots = (*roots, self._projects_dir)
        return roots

    # --- fayllar ---------------------------------------------------------
    def data_path(self, *parts: str) -> Path:
        """Plaginning o'z papkasi ichidagi yo'l (har doim ruxsat etilgan)."""
        return safe_join(self.data_dir, *parts)

    def resolve_path(self, path: str | Path) -> Path:
        """Yo'lni tekshiradi: faqat o'z papkasi va manifestdagi `permissions.paths` ichida."""
        candidate = Path(path)
        if not candidate.is_absolute():
            candidate = self.data_dir / candidate
        try:
            return resolve_within(candidate, self._roots())
        except PathTraversalError as exc:
            raise self._denied("path", str(path)) from exc

    # --- portlar va serial ------------------------------------------------
    def check_port(self, port: int) -> int:
        if not any(port in allowed for allowed in self.manifest.permissions.ports):
            raise self._denied("port", str(port))
        return port

    def check_serial(self, device: str) -> str:
        normalised = device.strip().upper()
        if normalised not in self.manifest.permissions.serial:
            raise self._denied("serial", device)
        return normalised

    # --- jarayonlar -------------------------------------------------------
    async def spawn(
        self,
        args: Sequence[str],
        *,
        cwd: Path,
        env: Mapping[str, str],
        memory_limit_mb: int,
        on_line: Callable[[str], None],
    ) -> ManagedProcess:
        """Jarayonni xotira limiti bilan ishga tushiradi (`shell`siz) va auditga yozadi.

        Manifestda `permissions.spawn = true` bo'lishi shart; `cwd` ruxsat etilgan
        papkalardan birida bo'lishi kerak.
        """
        if not self.manifest.permissions.spawn:
            raise self._denied("spawn", args[0] if args else "")
        # Kech import: psutil/pywin32 faqat jarayon ishga tushiradigan plaginda yuklanadi.
        from srv1_sdk.process import ManagedProcess

        workdir = self.resolve_path(cwd)
        process = ManagedProcess(
            args, cwd=workdir, env=env, memory_limit_mb=memory_limit_mb, on_line=on_line
        )
        detail = {"argv": list(args), "cwd": str(workdir), "limit_mb": memory_limit_mb}
        try:
            await process.start()
        except OSError as exc:
            await self.audit(
                "process.spawn", args[0], ok=False, detail={**detail, "error": str(exc)}
            )
            raise
        await self.audit("process.spawn", args[0], detail={**detail, "pid": process.pid})
        return process

    # --- hodisalar, audit, jurnal ----------------------------------------
    def publish(self, topic: str, data: Mapping[str, Any] | None = None) -> None:
        """`plugin.<nom>.<topic>` ga nashr qiladi; boshqa mavzuga yoza olmaydi."""
        if _TOPIC_RE.fullmatch(topic) is None:
            raise ValueError(f"yaroqsiz mavzu: {topic!r}")
        self._backend.publish(plugin_topic_prefix(self.name) + topic, data or {})

    async def audit(
        self, action: str, target: str, *, ok: bool = True, detail: Mapping[str, Any] | None = None
    ) -> None:
        """Xavfli amalni audit jurnaliga yozadi. `detail` ga sir yozilmaydi."""
        await self._backend.audit(action, target, ok, detail or {})

    def log(self, level: LogLevel, event: str, **fields: Any) -> None:  # noqa: ANN401
        self._backend.log(level, event, fields)

    def _denied(self, kind: str, target: str) -> PermissionDenied:
        self._backend.log("warning", "permission_denied", {"kind": kind, "target": target})
        return PermissionDenied(f"plagin {self.name!r}: {kind} uchun ruxsat yo'q: {target}")
