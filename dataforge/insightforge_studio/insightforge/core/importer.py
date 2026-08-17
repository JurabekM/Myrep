from __future__ import annotations

import io
import json
import sqlite3
import zipfile
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import pandas as pd

from ..config import (MAX_IMPORT_BYTES, MAX_URL_BYTES, MAX_ZIP_EXPANDED_BYTES,
                      MAX_ZIP_MEMBERS)
from .types import ImportResult

TABLE_EXTENSIONS = {".csv", ".tsv", ".json", ".jsonl", ".ndjson", ".xlsx",
                    ".xls", ".parquet", ".pq", ".feather", ".html", ".htm"}
LOG_EXTENSIONS = {".log", ".txt", ".out"}


def load_file(path: str | Path, *, limit: int | None = None,
              options: dict[str, Any] | None = None) -> ImportResult:
    p = Path(path).resolve()
    if not p.is_file():
        raise FileNotFoundError(p)
    if p.stat().st_size > MAX_IMPORT_BYTES:
        raise ValueError(f"Fayl juda katta: {p.stat().st_size / 1024**2:.1f} MB")
    opts = options or {}
    suffix = p.suffix.lower()

    if suffix == ".zip":
        return _load_zip(p, limit)
    if suffix in {".xlsx", ".xls"}:
        frame = pd.read_excel(p, sheet_name=opts.get("sheet_name", 0), nrows=limit)
    elif suffix in {".parquet", ".pq"}:
        frame = pd.read_parquet(p)
        frame = frame.head(limit) if limit else frame
    elif suffix == ".feather":
        frame = pd.read_feather(p)
        frame = frame.head(limit) if limit else frame
    elif suffix in {".jsonl", ".ndjson"}:
        frame = pd.read_json(p, lines=True, nrows=limit)
    elif suffix == ".json":
        frame = _json_frame(json.loads(_decode(p.read_bytes())))
        frame = frame.head(limit) if limit else frame
    elif suffix in {".html", ".htm"}:
        tables = pd.read_html(io.StringIO(_decode(p.read_bytes())))
        if not tables:
            raise ValueError("HTML ichida jadval topilmadi")
        frame = max(tables, key=len)
        frame = frame.head(limit) if limit else frame
    elif suffix in {".db", ".sqlite", ".sqlite3"}:
        return load_sqlite(p, table=opts.get("table"), limit=limit)
    elif suffix in LOG_EXTENSIONS:
        from .logs import parse_log_lines
        frame, detected = parse_log_lines(_decode(p.read_bytes()).splitlines())
        frame = frame.head(limit) if limit else frame
        return ImportResult(frame, p.stem, str(p), "log", {"parser": detected})
    else:
        frame = _read_delimited(_decode(p.read_bytes()), suffix, limit, opts)

    frame = normalize_frame(frame)
    return ImportResult(frame, p.stem, str(p), "table", {"format": suffix.lstrip(".")})


def load_text(text: str, name: str = "Pasted data") -> ImportResult:
    stripped = text.lstrip()
    if stripped.startswith(("[", "{")):
        try:
            frame = _json_frame(json.loads(text))
            return ImportResult(normalize_frame(frame), name, "clipboard", "table",
                                {"format": "json"})
        except json.JSONDecodeError:
            pass
    frame = _read_delimited(text, ".csv", None, {})
    return ImportResult(normalize_frame(frame), name, "clipboard", "table",
                        {"format": "delimited"})


def load_url(url: str, *, headers: dict[str, str] | None = None,
             timeout: int = 25) -> ImportResult:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Faqat to'g'ri HTTP/HTTPS URL qabul qilinadi")
    if parsed.hostname.lower() in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError("Lokal manzildan URL import xavfsizlik sabab bloklangan")

    import requests
    with requests.get(url, headers=headers or {}, timeout=timeout, stream=True) as response:
        response.raise_for_status()
        length = int(response.headers.get("Content-Length") or 0)
        if length > MAX_URL_BYTES:
            raise ValueError("URL javobi ruxsat etilgan hajmdan katta")
        chunks: list[bytes] = []
        size = 0
        for chunk in response.iter_content(1024 * 256):
            size += len(chunk)
            if size > MAX_URL_BYTES:
                raise ValueError("URL javobi ruxsat etilgan hajmdan katta")
            chunks.append(chunk)
        body = b"".join(chunks)
        ctype = response.headers.get("Content-Type", "").lower()
    text = _decode(body)
    name = Path(parsed.path).stem or parsed.hostname
    if "json" in ctype or text.lstrip().startswith(("[", "{")):
        frame = _json_frame(json.loads(text))
    else:
        frame = _read_delimited(text, Path(parsed.path).suffix, None, {})
    return ImportResult(normalize_frame(frame), name, url, "remote", {"bytes": size})


def sqlite_tables(path: str | Path) -> list[str]:
    uri = f"file:{Path(path).resolve().as_posix()}?mode=ro"
    with sqlite3.connect(uri, uri=True) as connection:
        rows = connection.execute(
            "SELECT name FROM sqlite_master WHERE type IN ('table','view') "
            "AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
    return [str(row[0]) for row in rows]


def load_sqlite(path: str | Path, table: str | None = None,
                limit: int | None = None) -> ImportResult:
    p = Path(path).resolve()
    tables = sqlite_tables(p)
    if not tables:
        raise ValueError("SQLite bazasida jadval topilmadi")
    chosen = table if table in tables else tables[0]
    escaped = chosen.replace('"', '""')
    query = f'SELECT * FROM "{escaped}"'
    if limit:
        query += f" LIMIT {max(1, int(limit))}"
    uri = f"file:{p.as_posix()}?mode=ro"
    with sqlite3.connect(uri, uri=True) as connection:
        frame = pd.read_sql_query(query, connection)
    return ImportResult(normalize_frame(frame), f"{p.stem}.{chosen}", str(p), "database",
                        {"table": chosen, "tables": tables, "readonly": True})


def export_frame(frame: pd.DataFrame, path: str | Path) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    suffix = p.suffix.lower()
    if suffix == ".csv":
        frame.to_csv(p, index=False)
    elif suffix == ".xlsx":
        frame.to_excel(p, index=False)
    elif suffix in {".parquet", ".pq"}:
        frame.to_parquet(p, index=False)
    elif suffix == ".json":
        frame.to_json(p, orient="records", force_ascii=False, indent=2, date_format="iso")
    elif suffix in {".jsonl", ".ndjson"}:
        frame.to_json(p, orient="records", lines=True, force_ascii=False, date_format="iso")
    elif suffix in {".html", ".htm"}:
        frame.to_html(p, index=False)
    else:
        raise ValueError(f"Qo'llab-quvvatlanmaydigan eksport formati: {suffix}")
    return p


def normalize_frame(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    names: list[str] = []
    used: set[str] = set()
    for index, raw in enumerate(out.columns):
        base = " ".join(str(raw).replace("\n", " ").split()) or f"column_{index + 1}"
        name, counter = base, 2
        while name in used:
            name = f"{base}_{counter}"
            counter += 1
        used.add(name)
        names.append(name)
    out.columns = names
    for col in out.select_dtypes(include="object").columns:
        series = out[col]
        non_null = series.dropna().astype(str)
        if non_null.empty:
            continue
        numeric = pd.to_numeric(non_null.str.replace(",", "", regex=False), errors="coerce")
        if numeric.notna().mean() >= 0.96:
            out[col] = pd.to_numeric(series.astype(str).str.replace(",", "", regex=False),
                                     errors="coerce")
            continue
        if any(token in col.lower() for token in ("date", "time", "sana", "vaqt", "timestamp")):
            parsed = pd.to_datetime(series, errors="coerce")
            if parsed.notna().mean() >= 0.80:
                out[col] = parsed
    return out


def _read_delimited(text: str, suffix: str, limit: int | None,
                    opts: dict[str, Any]) -> pd.DataFrame:
    separator = opts.get("separator")
    if not separator:
        separator = "\t" if suffix == ".tsv" else None
    return pd.read_csv(io.StringIO(text), sep=separator, engine="python",
                       nrows=limit, on_bad_lines="warn")


def _json_frame(obj: Any) -> pd.DataFrame:
    if isinstance(obj, list):
        return pd.json_normalize(obj)
    if isinstance(obj, dict):
        candidates = [value for value in obj.values() if isinstance(value, list)]
        return pd.json_normalize(max(candidates, key=len) if candidates else [obj])
    return pd.DataFrame({"value": [obj]})


def _load_zip(path: Path, limit: int | None) -> ImportResult:
    frames: list[pd.DataFrame] = []
    warnings: list[str] = []
    with zipfile.ZipFile(path) as archive:
        members = [m for m in archive.infolist() if not m.is_dir()]
        if len(members) > MAX_ZIP_MEMBERS:
            raise ValueError(f"Arxivda juda ko'p fayl: {len(members)}")
        expanded = sum(m.file_size for m in members)
        if expanded > MAX_ZIP_EXPANDED_BYTES:
            raise ValueError("Arxivning ochilgan hajmi limitdan katta")
        for member in members:
            if Path(member.filename).suffix.lower() not in TABLE_EXTENSIONS | LOG_EXTENSIONS:
                warnings.append(f"O'tkazib yuborildi: {member.filename}")
                continue
            try:
                result = load_text(_decode(archive.read(member)), Path(member.filename).stem)
                part = result.frame.head(limit) if limit else result.frame
                part["_source_file"] = member.filename
                frames.append(part)
            except Exception as exc:
                warnings.append(f"{member.filename}: {exc}")
    if not frames:
        raise ValueError("Arxivdan o'qiladigan jadval topilmadi")
    return ImportResult(pd.concat(frames, ignore_index=True, sort=False), path.stem,
                        str(path), "archive", {"members": len(frames)}, warnings)


def _decode(data: bytes) -> str:
    if data.startswith(b"\xef\xbb\xbf"):
        return data.decode("utf-8-sig")
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        import chardet
        encoding = chardet.detect(data[:262144]).get("encoding") or "utf-8"
        return data.decode(encoding, errors="replace")

