"""Text chunking for RAG.

Two strategies:
  - `chunk_legal_text` — structure-aware split by modda/bob (law articles),
    keeping each article intact so citations map 1:1 to legal units.
  - `chunk_recursive` — generic recursive splitter with overlap for ordinary
    documents.
"""

import re
from dataclasses import dataclass, field
from typing import Any

# Rough token estimate: ~3.5 chars/token for uz/ru mixed text.
_CHARS_PER_TOKEN = 3.5
MAX_CHUNK_TOKENS = 800
OVERLAP_TOKENS = 100

_ARTICLE_RE = re.compile(
    r"(?=^\s*(?:(\d+)[-–]?\s*modda|Статья\s+(\d+))\b)", re.MULTILINE | re.IGNORECASE
)
_SEPARATORS = ["\n\n", "\n", ". ", " "]


@dataclass(frozen=True)
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
            chunks.append(_make_chunk(buffer, len(chunks), base_metadata))
        # keep tail overlap for context continuity
        buffer = buffer[-overlap_chars:] + piece if overlap_chars else piece
    if buffer.strip():
        chunks.append(_make_chunk(buffer, len(chunks), base_metadata))
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
        else:
            result.append(segment)
    return result


def _make_chunk(text: str, index: int, base_metadata: dict[str, Any] | None) -> Chunk:
    return Chunk(text=text.strip(), index=index, metadata=dict(base_metadata or {}))


def chunk_legal_text(
    text: str, *, law_title: str, url: str | None = None
) -> list[Chunk]:
    """Split a law by articles; oversized articles fall back to recursive split."""
    parts = _ARTICLE_RE.split(text)
    # re.split with capture groups interleaves matches; rebuild article blocks.
    blocks: list[str] = []
    current = ""
    for part in parts:
        if part is None:
            continue
        if re.match(r"^\d+$", part or ""):
            continue  # capture-group artifact (article number)
        if _ARTICLE_RE.match(part or ""):
            if current.strip():
                blocks.append(current)
            current = part
        else:
            current += part or ""
    if current.strip():
        blocks.append(current)
    if len(blocks) <= 1:
        return chunk_recursive(text, base_metadata={"law_title": law_title, "url": url})

    chunks: list[Chunk] = []
    for block in blocks:
        article_match = re.search(
            r"(\d+)[-–]?\s*modda|Статья\s+(\d+)", block, re.IGNORECASE
        )
        article = None
        if article_match:
            number = article_match.group(1) or article_match.group(2)
            article = f"{number}-modda"
        metadata = {"law_title": law_title, "url": url, "article": article}
        if _estimate_tokens(block) > MAX_CHUNK_TOKENS:
            for sub in chunk_recursive(block, base_metadata=metadata):
                chunks.append(Chunk(text=sub.text, index=len(chunks), metadata=sub.metadata))
        else:
            chunks.append(Chunk(text=block.strip(), index=len(chunks), metadata=metadata))
    return chunks
