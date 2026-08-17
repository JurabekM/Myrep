"""Universal ma'lumot yuklash qatlami.

Manbalar: lokal fayl, papka (ko'p fayl), URL (internet), SQL baza (SQLite),
xom matn/clipboard. Formatlar: CSV/TSV, JSON/JSONL, Excel, Parquet, XML, YAML,
HTML jadval, SQLite, va istalgan log/matn fayl (``logparse`` orqali).
"""
from __future__ import annotations

import gzip
import io
import json
import os
import sqlite3
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

from ..config import SNIFF_BYTES
from . import logparse

TABULAR_EXT = {".csv", ".tsv", ".psv"}
JSON_EXT = {".json", ".jsonl", ".ndjson"}
EXCEL_EXT = {".xlsx", ".xls", ".xlsm", ".xlsb"}
PARQUET_EXT = {".parquet", ".pq"}
SQLITE_EXT = {".db", ".sqlite", ".sqlite3", ".db3"}
TEXT_EXT = {".log", ".txt", ".out", ".err", ".syslog", ""}
XML_EXT = {".xml"}
YAML_EXT = {".yaml", ".yml"}
HTML_EXT = {".html", ".htm"}

ALL_EXT = (TABULAR_EXT | JSON_EXT | EXCEL_EXT | PARQUET_EXT | SQLITE_EXT
           | TEXT_EXT | XML_EXT | YAML_EXT | HTML_EXT)


@dataclass
class LoadResult:
    """Yuklash natijasi: ma'lumot + qanday o'qilgani haqidagi metama'lumot."""

    df: pd.DataFrame
    name: str
    source: str
    kind: str
    meta: dict[str, Any] = field(default_factory=dict)

    @property
    def summary(self) -> str:
        r, c = self.df.shape
        extra = self.meta.get("format", "")
        return f"{self.name}: {r:,} qator × {c} ustun · {self.kind}" + (f" · {extra}" if extra else "")


# ---------------------------------------------------------------------------
# Yordamchilar
# ---------------------------------------------------------------------------
def detect_encoding(raw: bytes, default: str = "utf-8") -> str:
    """Baytlardan kodlashni aniqlaydi (chardet bo'lsa undan foydalanadi)."""
    if raw.startswith(b"\xef\xbb\xbf"):
        return "utf-8-sig"
    try:
        raw.decode("utf-8")
        return "utf-8"
    except UnicodeDecodeError:
        pass
    try:
        import chardet

        guess = chardet.detect(raw[:SNIFF_BYTES])
        if guess and guess.get("encoding") and (guess.get("confidence") or 0) > 0.6:
            return guess["encoding"]
    except Exception:
        pass
    return default


def _open_bytes(path: Path) -> bytes:
    """Faylni (kerak bo'lsa gzip'dan chiqarib) baytlar sifatida o'qiydi."""
    if path.suffix.lower() == ".gz":
        with gzip.open(path, "rb") as fh:
            return fh.read()
    return path.read_bytes()


def _effective_suffix(path: Path) -> str:
    """`.gz` ni olib tashlab, haqiqiy kengaytmani qaytaradi."""
    suf = path.suffix.lower()
    if suf == ".gz":
        return Path(path.stem).suffix.lower()
    return suf


def sniff_delimiter(text: str) -> str:
    """CSV ajratgichini aniqlaydi."""
    import csv

    head = text[:SNIFF_BYTES]
    try:
        dialect = csv.Sniffer().sniff(head, delimiters=",;\t|")
        return dialect.delimiter
    except Exception:
        first = head.splitlines()[0] if head.splitlines() else ""
        counts = {d: first.count(d) for d in [",", ";", "\t", "|"]}
        best = max(counts, key=counts.get)
        return best if counts[best] > 0 else ","


def looks_tabular(text: str, delim: str) -> bool:
    """Matn haqiqatan jadvalga o'xshaydimi (ustun soni barqarormi)?"""
    lines = [ln for ln in text.splitlines()[:60] if ln.strip()]
    if len(lines) < 2:
        return False
    counts = [ln.count(delim) for ln in lines]
    if counts[0] < 1:
        return False
    stable = sum(1 for c in counts if c == counts[0]) / len(counts)
    return stable > 0.9


# ---------------------------------------------------------------------------
# Asosiy yuklagichlar
# ---------------------------------------------------------------------------
def load_file(path: str | os.PathLike, *, force: str | None = None,
              nrows: int | None = None, **opts: Any) -> LoadResult:
    """Bitta faylni turiga qarab yuklaydi.

    ``force`` — parser'ni majburlash: csv|json|excel|parquet|sqlite|log|xml|yaml|html
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Fayl topilmadi: {p}")

    suf = force or _effective_suffix(p)
    name = p.stem

    if suf == ".zip" or (force is None and p.suffix.lower() == ".zip"):
        return _load_zip(p, nrows=nrows)

    if force in ("excel",) or suf in EXCEL_EXT:
        return _load_excel(p, nrows=nrows, **opts)
    if force in ("parquet",) or suf in PARQUET_EXT:
        df = pd.read_parquet(p)
        if nrows:
            df = df.head(nrows)
        return LoadResult(df, name, str(p), "fayl", {"format": "Parquet"})
    if force in ("sqlite",) or suf in SQLITE_EXT:
        return load_sqlite(p, table=opts.get("table"), query=opts.get("query"), nrows=nrows)
    if force in ("xml",) or suf in XML_EXT:
        df = pd.read_xml(p)
        return LoadResult(df, name, str(p), "fayl", {"format": "XML"})
    if force in ("yaml",) or suf in YAML_EXT:
        return _load_yaml(p)
    if force in ("html",) or suf in HTML_EXT:
        tables = pd.read_html(io.StringIO(p.read_text(encoding="utf-8", errors="replace")))
        df = max(tables, key=len) if tables else pd.DataFrame()
        return LoadResult(df, name, str(p), "fayl",
                          {"format": f"HTML jadval ({len(tables)} ta topildi)"})

    raw = _open_bytes(p)
    enc = detect_encoding(raw)
    text = raw.decode(enc, errors="replace")
    return load_text(text, name=name, source=str(p), force=force,
                     encoding=enc, nrows=nrows, **opts)


def load_text(text: str, *, name: str = "matn", source: str = "<matn>",
              force: str | None = None, encoding: str = "utf-8",
              nrows: int | None = None, **opts: Any) -> LoadResult:
    """Xom matndan (fayl mazmuni, clipboard, HTTP javob) DataFrame quradi."""
    stripped = text.lstrip()

    # 1) To'liq JSON hujjat
    if force == "json" or (force is None and stripped[:1] in "[{"):
        res = _try_json_document(text, name, source)
        if res is not None:
            return res

    # 2) Jadval (CSV/TSV/…)
    if force in ("csv", "tsv") or force is None:
        delim = opts.get("delimiter") or sniff_delimiter(text)
        if force in ("csv", "tsv") or looks_tabular(text, delim):
            try:
                df = pd.read_csv(
                    io.StringIO(text),
                    sep=opts.get("delimiter", delim),
                    nrows=nrows,
                    engine="python",
                    on_bad_lines="skip",
                    skipinitialspace=True,
                )
                if df.shape[1] > 1:
                    df = _post_tabular(df)
                    dn = {",": "vergul", ";": "nuqta-vergul", "\t": "TAB", "|": "quvur"}
                    return LoadResult(
                        df, name, source, "jadval",
                        {"format": f"CSV ({dn.get(delim, delim)})", "encoding": encoding},
                    )
            except Exception:
                pass

    # 3) Log / erkin matn
    lines = text.splitlines()
    if nrows:
        lines = lines[:nrows]
    df, fmt = logparse.parse_lines(lines, parser=opts.get("parser"))
    df = _post_tabular(df)
    return LoadResult(
        df, name, source, "log",
        {"format": fmt.name, "confidence": fmt.confidence,
         "parser": fmt.parser, "encoding": encoding, "lines": len(lines)},
    )


def _try_json_document(text: str, name: str, source: str) -> LoadResult | None:
    try:
        obj = json.loads(text)
    except Exception:
        # JSON Lines bo'lishi mumkin
        lines = [ln for ln in text.splitlines() if ln.strip()]
        if lines and lines[0].lstrip().startswith("{"):
            df, fmt = logparse.parse_lines(lines, parser="json")
            return LoadResult(_post_tabular(df), name, source, "json",
                              {"format": "JSON Lines"})
        return None

    if isinstance(obj, list):
        df = pd.json_normalize(obj)
    elif isinstance(obj, dict):
        # eng katta ro'yxatli kalitni topamiz
        best_key, best_len = None, 0
        for k, v in obj.items():
            if isinstance(v, list) and len(v) > best_len:
                best_key, best_len = k, len(v)
        if best_key is not None:
            df = pd.json_normalize(obj[best_key])
        else:
            df = pd.json_normalize(obj)
    else:
        df = pd.DataFrame({"value": [obj]})
    return LoadResult(_post_tabular(df), name, source, "json", {"format": "JSON"})


def _load_yaml(p: Path) -> LoadResult:
    import yaml

    obj = yaml.safe_load(p.read_text(encoding="utf-8", errors="replace"))
    if isinstance(obj, list):
        df = pd.json_normalize(obj)
    elif isinstance(obj, dict):
        lists = {k: v for k, v in obj.items() if isinstance(v, list)}
        df = pd.json_normalize(max(lists.values(), key=len)) if lists else pd.json_normalize(obj)
    else:
        df = pd.DataFrame({"value": [obj]})
    return LoadResult(_post_tabular(df), p.stem, str(p), "fayl", {"format": "YAML"})


def _load_excel(p: Path, nrows: int | None = None, **opts: Any) -> LoadResult:
    sheet = opts.get("sheet")
    xl = pd.ExcelFile(p)
    sheets = xl.sheet_names
    target = sheet if sheet in sheets else sheets[0]
    df = xl.parse(target, nrows=nrows)
    return LoadResult(_post_tabular(df), f"{p.stem}", str(p), "fayl",
                      {"format": f"Excel · varaq '{target}'", "sheets": sheets})


def _load_zip(p: Path, nrows: int | None = None) -> LoadResult:
    with zipfile.ZipFile(p) as zf:
        members = [m for m in zf.namelist() if not m.endswith("/")]
        if not members:
            raise ValueError("ZIP arxiv bo'sh")
        frames: list[pd.DataFrame] = []
        for m in members[:50]:
            data = zf.read(m)
            enc = detect_encoding(data)
            try:
                res = load_text(data.decode(enc, errors="replace"),
                                name=Path(m).stem, source=f"{p}!{m}", nrows=nrows)
                sub = res.df
                sub["_source"] = m
                frames.append(sub)
            except Exception:
                continue
    df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    return LoadResult(df, p.stem, str(p), "arxiv",
                      {"format": f"ZIP ({len(frames)} fayl)"})


def load_folder(folder: str | os.PathLike, pattern: str = "*",
                recursive: bool = True, nrows: int | None = None,
                max_files: int = 200) -> LoadResult:
    """Papkadagi mos fayllarni birlashtirib yuklaydi (``_source`` ustuni bilan)."""
    base = Path(folder)
    if not base.is_dir():
        raise NotADirectoryError(f"Papka emas: {base}")
    it: Iterable[Path] = base.rglob(pattern) if recursive else base.glob(pattern)
    files = [f for f in it if f.is_file()][:max_files]
    frames, errors = [], []
    for f in files:
        try:
            res = load_file(f, nrows=nrows)
            if res.df.empty:
                continue
            sub = res.df.copy()
            sub["_source"] = f.name
            frames.append(sub)
        except Exception as exc:  # bitta fayl xatosi butun yuklashni to'xtatmasin
            errors.append(f"{f.name}: {exc}")
    if not frames:
        raise ValueError(f"Papkadan hech narsa o'qilmadi ({len(errors)} xato)")
    df = pd.concat(frames, ignore_index=True, sort=False)
    return LoadResult(df, base.name, str(base), "papka",
                      {"format": f"{len(frames)} fayl birlashtirildi",
                       "errors": errors[:20], "files": [f.name for f in files]})


def load_url(url: str, *, timeout: int = 30, nrows: int | None = None,
             headers: dict[str, str] | None = None, **opts: Any) -> LoadResult:
    """Internetdan (HTTP/HTTPS) ma'lumot yuklaydi — API, CSV, log, JSON."""
    import requests

    hdrs = {"User-Agent": "DataForge/1.0"}
    hdrs.update(headers or {})
    resp = requests.get(url, timeout=timeout, headers=hdrs)
    resp.raise_for_status()
    ctype = (resp.headers.get("Content-Type") or "").split(";")[0].strip().lower()
    name = Path(url.split("?")[0]).stem or "url"

    force = None
    if "json" in ctype:
        force = "json"
    elif "csv" in ctype:
        force = "csv"
    elif "html" in ctype:
        try:
            tables = pd.read_html(io.StringIO(resp.text))
            if tables:
                df = max(tables, key=len)
                return LoadResult(_post_tabular(df), name, url, "internet",
                                  {"format": f"HTML jadval ({len(tables)} ta)",
                                   "status": resp.status_code})
        except Exception:
            pass

    res = load_text(resp.text, name=name, source=url, force=force, nrows=nrows, **opts)
    res.kind = "internet"
    res.meta["status"] = resp.status_code
    res.meta["content_type"] = ctype
    return res


def sqlite_tables(path: str | os.PathLike) -> list[str]:
    """SQLite bazasidagi jadval nomlari."""
    with sqlite3.connect(str(path)) as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type IN ('table','view') "
            "AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
    return [r[0] for r in rows]


def load_sqlite(path: str | os.PathLike, table: str | None = None,
                query: str | None = None, nrows: int | None = None) -> LoadResult:
    """SQLite bazasidan jadval yoki SQL so'rov natijasini yuklaydi."""
    p = Path(path)
    with sqlite3.connect(str(p)) as conn:
        if query:
            sql = query
            label = "SQL so'rov"
        else:
            tables = sqlite_tables(p)
            if not tables:
                raise ValueError("Bazada jadval yo'q")
            table = table if table in tables else tables[0]
            sql = f'SELECT * FROM "{table}"'
            if nrows:
                sql += f" LIMIT {int(nrows)}"
            label = f"jadval '{table}'"
        df = pd.read_sql_query(sql, conn)
    return LoadResult(_post_tabular(df), table or p.stem, str(p), "baza",
                      {"format": f"SQLite · {label}"})


# ---------------------------------------------------------------------------
# Yuklashdan keyingi normallashtirish
# ---------------------------------------------------------------------------
def _post_tabular(df: pd.DataFrame) -> pd.DataFrame:
    """Ustun nomlarini tozalaydi va aniq turlarni tiklaydi."""
    if df is None or df.empty:
        return df if df is not None else pd.DataFrame()
    df = df.copy()
    df.columns = [_clean_col(str(c), i) for i, c in enumerate(df.columns)]
    df = _dedupe_columns(df)
    return infer_types(df)


def _clean_col(name: str, idx: int) -> str:
    n = name.strip().replace("\n", " ").replace("﻿", "")
    n = " ".join(n.split())
    return n if n and not n.lower().startswith("unnamed:") else f"col_{idx + 1}"


def _dedupe_columns(df: pd.DataFrame) -> pd.DataFrame:
    seen: dict[str, int] = {}
    cols = []
    for c in df.columns:
        if c in seen:
            seen[c] += 1
            cols.append(f"{c}_{seen[c]}")
        else:
            seen[c] = 0
            cols.append(c)
    df.columns = cols
    return df


def infer_types(df: pd.DataFrame, datetime_threshold: float = 0.85,
                numeric_threshold: float = 0.9) -> pd.DataFrame:
    """Matn ustunlarini avtomatik son / sana / mantiqiy turga keltiradi."""
    out = df.copy()
    for col in out.columns:
        s = out[col]
        if not (s.dtype == object or pd.api.types.is_string_dtype(s)):
            continue
        non_null = s.dropna()
        if non_null.empty:
            continue
        sample = non_null.astype(str).head(4000)

        low = sample.str.lower().str.strip()
        uniq = set(low.unique())
        if uniq and uniq <= {"true", "false", "yes", "no", "1", "0", "t", "f", "ha", "yo'q"}:
            mapping = {"true": True, "yes": True, "1": True, "t": True, "ha": True,
                       "false": False, "no": False, "0": False, "f": False, "yo'q": False}
            out[col] = s.astype(str).str.lower().str.strip().map(mapping)
            continue

        cleaned = sample.str.replace(",", "", regex=False).str.replace(" ", "", regex=False)
        num = pd.to_numeric(cleaned, errors="coerce")
        if num.notna().mean() >= numeric_threshold:
            full = (s.astype(str).str.replace(",", "", regex=False)
                    .str.replace(" ", "", regex=False))
            out[col] = pd.to_numeric(full, errors="coerce")
            continue

        name_hint = any(k in str(col).lower()
                        for k in ("time", "date", "ts", "vaqt", "sana", "stamp"))
        if name_hint or _looks_like_date(sample):
            parsed = logparse.parse_timestamp_series(s)
            if parsed.notna().mean() >= datetime_threshold:
                out[col] = parsed
                continue

        # kam unikal — kategoriya sifatida saqlash tejamkor
        if len(non_null) > 1000 and non_null.nunique() / len(non_null) < 0.05:
            out[col] = s.astype("category")
    return out


def _looks_like_date(sample: pd.Series) -> bool:
    head = sample.head(200)
    hits = head.str.contains(logparse.RE_TS_ANY, regex=True, na=False)
    return bool(hits.mean() > 0.8)


def memory_usage_mb(df: pd.DataFrame) -> float:
    try:
        return float(df.memory_usage(deep=True).sum()) / 1024 / 1024
    except Exception:
        return float(np.nan)


# ---------------------------------------------------------------------------
# Eksport
# ---------------------------------------------------------------------------
def export_df(df: pd.DataFrame, path: str | os.PathLike, fmt: str | None = None) -> str:
    """DataFrame'ni fayl sifatida saqlaydi. Qaytadi: yozilgan yo'l."""
    p = Path(path)
    suf = (fmt or p.suffix.lower().lstrip(".")).lower()
    p.parent.mkdir(parents=True, exist_ok=True)
    if suf in ("csv", ""):
        df.to_csv(p, index=False, encoding="utf-8-sig")
    elif suf == "tsv":
        df.to_csv(p, index=False, sep="\t", encoding="utf-8-sig")
    elif suf in ("xlsx", "xls"):
        df.to_excel(p, index=False)
    elif suf in ("parquet", "pq"):
        df.to_parquet(p, index=False)
    elif suf == "json":
        df.to_json(p, orient="records", force_ascii=False, indent=2, date_format="iso")
    elif suf in ("jsonl", "ndjson"):
        df.to_json(p, orient="records", lines=True, force_ascii=False, date_format="iso")
    elif suf in ("db", "sqlite", "sqlite3"):
        with sqlite3.connect(str(p)) as conn:
            df.to_sql("data", conn, if_exists="replace", index=False)
    elif suf == "html":
        p.write_text(df.to_html(index=False), encoding="utf-8")
    elif suf in ("md", "markdown"):
        p.write_text(df.to_markdown(index=False), encoding="utf-8")
    else:
        raise ValueError(f"Noma'lum eksport formati: {suf}")
    return str(p)
