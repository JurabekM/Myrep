"""Matnni RAG uchun bo'laklarga ajratish.

Ikki strategiya:
  - ``chunk_legal_text`` — qonun matnini modda/bo'lim bo'yicha strukturaviy
    ajratadi, shunda har bir chunk aniq moddaga mos keladi (citation uchun).
  - ``chunk_recursive`` — oddiy hujjatlar uchun rekursiv, ustma-ust (overlap)
    bo'laklovchi.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

# uz/ru aralash matn uchun taxminiy: ~3.5 belgi/token.
_CHARS_PER_TOKEN = 3.5
MAX_CHUNK_TOKENS = 400
OVERLAP_TOKENS = 60

_ARTICLE_RE = re.compile(
    r"(?=^\s*(?:(\d+)[-–]?\s*modda|Статья\s+(\d+))\b)", re.MULTILINE | re.IGNORECASE
)
_SEPARATORS = ["\n\n", "\n", ". ", " "]


@dataclass
class Chunk:
    text: str
    index: int
    metadata: dict[str, Any] = field(default_factory=dict)


def _estimate_tokens(text: str) -> int:
    return int(len(text) / _CHARS_PER_TOKEN)


def chunk_recursive(
    text: str,
    *,
    max_tokens: int = MAX_CHUNK_TOKENS,
    overlap_tokens: int = OVERLAP_TOKENS,
    base_metadata: dict[str, Any] | None = None,
) -> list[Chunk]:
    max_chars = int(max_tokens * _CHARS_PER_TOKEN)
    overlap_chars = int(overlap_tokens * _CHARS_PER_TOKEN)
    text = text.strip()
    if not text:
        return []

    pieces = _split(text, max_chars, _SEPARATORS)
    chunks: list[Chunk] = []
    buffer = ""
    for piece in pieces:
        if len(buffer) + len(piece) <= max_chars:
            buffer += piece
            continue
        if buffer.strip():
            chunks.append(Chunk(buffer.strip(), len(chunks), dict(base_metadata or {})))
        buffer = (buffer[-overlap_chars:] + piece) if overlap_chars else piece
    if buffer.strip():
        chunks.append(Chunk(buffer.strip(), len(chunks), dict(base_metadata or {})))
    return chunks


def _split(text: str, max_chars: int, separators: list[str]) -> list[str]:
    if len(text) <= max_chars or not separators:
        return [text]
    sep, *rest = separators
    parts = text.split(sep)
    result: list[str] = []
    for i, part in enumerate(parts):
        segment = part + (sep if i < len(parts) - 1 else "")
        if len(segment) > max_chars:
            result.extend(_split(segment, max_chars, rest))
        elif segment:
            result.append(segment)
    return result


def chunk_legal_text(text: str, *, law_title: str, url: str | None = None) -> list[Chunk]:
    """Qonunni moddalarga ajratadi; katta moddalar rekursiv bo'linadi."""
    parts = _ARTICLE_RE.split(text)
    blocks: list[str] = []
    current = ""
    for part in parts:
        if part is None or re.fullmatch(r"\d+", part or ""):
            continue  # capture-group qoldig'i (modda raqami)
        if _ARTICLE_RE.match(part or ""):
            if current.strip():
                blocks.append(current)
            current = part
        else:
            current += part or ""
    if current.strip():
        blocks.append(current)

    if len(blocks) <= 1:
        return chunk_recursive(text, base_metadata={"title": law_title, "url": url})

    chunks: list[Chunk] = []
    for block in blocks:
        match = re.search(r"(\d+)[-–]?\s*modda|Статья\s+(\d+)", block, re.IGNORECASE)
        article = None
        if match:
            number = match.group(1) or match.group(2)
            article = f"{number}-modda"
        metadata = {"title": law_title, "url": url, "article": article}
        if _estimate_tokens(block) > MAX_CHUNK_TOKENS:
            for sub in chunk_recursive(block, base_metadata=metadata):
                chunks.append(Chunk(sub.text, len(chunks), sub.metadata))
        else:
            chunks.append(Chunk(block.strip(), len(chunks), metadata))
    return chunks
