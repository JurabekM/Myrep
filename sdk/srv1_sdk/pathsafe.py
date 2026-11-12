"""Xavfsiz yo'l birlashtirish (path traversal va Windows nom tuzoqlaridan himoya)."""

from collections.abc import Iterable
from pathlib import Path


class PathTraversalError(ValueError):
    """So'ralgan yo'l ruxsat etilgan papkadan tashqariga chiqadi."""


_RESERVED_NAMES = frozenset(
    {"CON", "PRN", "AUX", "NUL", "CONIN$", "CONOUT$"}
    | {f"COM{n}" for n in range(1, 10)}
    | {f"LPT{n}" for n in range(1, 10)}
)


def safe_join(base: Path, *parts: str) -> Path:
    """`base` ichidagi yo'lni qaytaradi; tashqariga chiqsa `PathTraversalError`."""
    for part in parts:
        _check_part(part)
    resolved_base = base.resolve()
    candidate = resolved_base.joinpath(*parts).resolve()
    if not candidate.is_relative_to(resolved_base):
        raise PathTraversalError(f"yo'l ruxsat etilgan papkadan tashqarida: {'/'.join(parts)}")
    return candidate


def resolve_within(path: Path, roots: Iterable[Path]) -> Path:
    """Mutlaq `path` ni hal qiladi; hech bir `roots` ichida bo'lmasa `PathTraversalError`."""
    for component in path.parts[1:] if path.anchor else path.parts:
        if ":" in component or "\x00" in component:
            raise PathTraversalError(f"yaroqsiz yo'l bo'lagi: {component!r}")
        check_component(component)
    resolved = path.resolve()
    if not any(resolved.is_relative_to(root.resolve()) for root in roots):
        raise PathTraversalError(f"yo'l ruxsat etilgan papkalardan tashqarida: {path}")
    return resolved


def _check_part(part: str) -> None:
    # ':' — disk harfi (C:foo) va NTFS muqobil oqimlari (a.txt:stream) ni yopadi.
    if not part or "\x00" in part or ":" in part:
        raise PathTraversalError(f"yaroqsiz yo'l bo'lagi: {part!r}")
    for component in part.replace("\\", "/").split("/"):
        check_component(component)


def check_component(component: str) -> None:
    if component in ("", ".", ".."):
        return  # '..' ni yakuniy `is_relative_to` tekshiruvi hal qiladi
    # Windows oxiridagi nuqta/bo'shliqni jimgina olib tashlaydi: "a.txt." == "a.txt".
    if component[-1] in ". ":
        raise PathTraversalError(f"nom nuqta yoki bo'shliq bilan tugaydi: {component!r}")
    # Qurilma nomlari kengaytma bilan ham qurilma bo'lib qoladi: "NUL.txt".
    if component.split(".", 1)[0].rstrip(" ").upper() in _RESERVED_NAMES:
        raise PathTraversalError(f"Windows qurilma nomi: {component!r}")
