"""Import: CSV, Parquet va Excel fayllarni Parquet to'plamiga aylantirish (`polars`).

CSV va Parquet oqim bilan (`scan_*` + `sink_parquet`) o'tadi — fayl xotiraga to'liq
yuklanmaydi. Excel to'liq o'qiladi (varaq 1 048 576 qatordan oshmaydi).
Sinxron kod: `asyncio.to_thread` bilan chaqiriladi.
"""

import os
from dataclasses import dataclass
from pathlib import Path

# polars import bo'lishidan oldin: 4 GB li mashinada oqimlar sonini cheklaymiz.
os.environ.setdefault("POLARS_MAX_THREADS", "2")

import polars as pl

from .models import Column, Encoding

CSV_SUFFIXES = (".csv", ".tsv", ".txt")
EXCEL_SUFFIXES = (".xlsx", ".xlsm", ".xls", ".xlsb", ".ods")
PARQUET_SUFFIXES = (".parquet", ".pq")
SUPPORTED = (*CSV_SUFFIXES, *EXCEL_SUFFIXES, *PARQUET_SUFFIXES)
_SEPARATORS = (",", ";", "\t", "|")
_SNIFF_BYTES = 64 * 1024
_CHUNK = 1024 * 1024


class ImportFailed(Exception):
    """Faylni import qilib bo'lmadi; matni foydalanuvchiga ko'rsatiladi."""


@dataclass(frozen=True, slots=True)
class ImportResult:
    rows: int
    columns: list[Column]
    size: int


def detect_encoding(path: Path) -> str:
    """UTF-8 sifatida o'qilsa — `utf-8`, aks holda `cp1251` (kirill Windows fayllari)."""
    with path.open("rb") as handle:
        sample = handle.read(_SNIFF_BYTES)
    try:
        sample.decode("utf-8")
    except UnicodeDecodeError as exc:
        # Namuna ko'p baytli belgining o'rtasida kesilgan bo'lishi mumkin.
        if exc.start < len(sample) - 4:
            return "cp1251"
    return "utf-8"


def detect_separator(path: Path, encoding: str) -> str:
    """Birinchi qatorlarda eng barqaror uchraydigan ajratgich."""
    with path.open("r", encoding=encoding, errors="replace", newline="") as handle:
        lines = [line for line in handle.read(_SNIFF_BYTES).splitlines() if line.strip()][:20]
    if not lines:
        return ","
    best, best_score = ",", 0
    for separator in _SEPARATORS:
        counts = [line.count(separator) for line in lines]
        if min(counts) > 0 and min(counts) == max(counts) and counts[0] > best_score:
            best, best_score = separator, counts[0]
    if best_score == 0:  # ustunlar soni bir xil emas: sarlavhaga qaraymiz
        best = max(_SEPARATORS, key=lines[0].count)
    return best


def _transcode(source: Path, target: Path, encoding: str) -> None:
    """Faylni UTF-8 ga bo'lak-bo'lak o'tkazadi (polars faqat UTF-8 o'qiydi)."""
    with (
        source.open("r", encoding=encoding, errors="replace", newline="") as reader,
        target.open("w", encoding="utf-8", newline="") as writer,
    ):
        while chunk := reader.read(_CHUNK):
            writer.write(chunk)


def _describe(target: Path) -> ImportResult:
    scan = pl.scan_parquet(target)
    schema = scan.collect_schema()
    rows = int(scan.select(pl.len()).collect().item())
    columns = [Column(name=name, type=str(dtype)) for name, dtype in schema.items()]
    return ImportResult(rows=rows, columns=columns, size=target.stat().st_size)


def _import_csv(source: Path, target: Path, encoding: Encoding, separator: str, tmp: Path) -> None:
    actual = detect_encoding(source) if encoding == "auto" else encoding
    readable = source
    if actual != "utf-8":
        readable = tmp / f"{target.stem}.utf8.csv"
        _transcode(source, readable, actual)
    try:
        delimiter = separator or detect_separator(readable, "utf-8")
        scan = pl.scan_csv(
            readable,
            separator=delimiter,
            try_parse_dates=True,
            infer_schema_length=10_000,
            encoding="utf8-lossy",
            truncate_ragged_lines=True,
        )
        scan.sink_parquet(target, compression="zstd")
    finally:
        if readable is not source:
            readable.unlink(missing_ok=True)


def _import_excel(source: Path, target: Path, sheet: str) -> None:
    if sheet.isdigit():
        frame = pl.read_excel(source, sheet_id=int(sheet), engine="calamine")
    elif sheet:
        frame = pl.read_excel(source, sheet_name=sheet, engine="calamine")
    else:
        frame = pl.read_excel(source, sheet_id=1, engine="calamine")
    frame.write_parquet(target, compression="zstd")


def import_file(
    source: Path,
    target: Path,
    tmp_dir: Path,
    *,
    encoding: Encoding = "auto",
    separator: str = "",
    sheet: str = "",
) -> ImportResult:
    """`source` ni `target` (Parquet) ga yozadi. Xato bo'lsa yarim fayl qoldirmaydi."""
    suffix = source.suffix.lower()
    if suffix not in SUPPORTED:
        raise ImportFailed(f"qo'llab-quvvatlanmaydigan fayl turi: {suffix or '(kengaytmasiz)'}")
    partial = target.with_suffix(".partial")
    try:
        if suffix in CSV_SUFFIXES:
            default = "\t" if suffix == ".tsv" else ""
            _import_csv(source, partial, encoding, separator or default, tmp_dir)
        elif suffix in PARQUET_SUFFIXES:
            pl.scan_parquet(source).sink_parquet(partial, compression="zstd")
        else:
            _import_excel(source, partial, sheet.strip())
        result = _describe(partial)
        if not result.columns:
            raise ImportFailed("faylda ustun topilmadi")
        partial.replace(target)
    except ImportFailed:
        partial.unlink(missing_ok=True)
        raise
    except MemoryError:
        partial.unlink(missing_ok=True)
        raise
    except Exception as exc:
        partial.unlink(missing_ok=True)
        raise ImportFailed(f"{type(exc).__name__}: {str(exc)[:300]}") from exc
    return ImportResult(rows=result.rows, columns=result.columns, size=target.stat().st_size)
