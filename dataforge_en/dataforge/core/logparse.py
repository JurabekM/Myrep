"""Automatic log recognition and conversion into structured tables.

This module is GUI-free and provides:

* ``detect_format``  — detects the log format from a sample of lines
* ``parse_lines``    — turns lines into a DataFrame (ts / level / message + extras)
* ``mine_templates`` — Drain-like simplified log template mining
* ``enrich``         — extracts entities such as IP, status, duration, URL from text
"""
from __future__ import annotations

import re
import warnings
from dataclasses import dataclass, field
from typing import Any, Callable

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Common regular expressions
# ---------------------------------------------------------------------------
RE_IPV4 = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
RE_IPV6 = re.compile(r"\b(?:[0-9A-Fa-f]{1,4}:){2,7}[0-9A-Fa-f]{1,4}\b")
RE_MAC = re.compile(r"\b(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}\b")
RE_UUID = re.compile(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
                     r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b")
RE_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
RE_URL = re.compile(r"\bhttps?://[^\s\"'<>]+")
# Session/trace ids are often 12–16 hex chars — they must be masked too
RE_HEX = re.compile(r"\b0x[0-9a-fA-F]+\b|\b[0-9a-fA-F]{12,}\b")
# Numbers: matched when not preceded by a letter, so units (ms, kb) stay intact
RE_NUM = re.compile(r"(?<![A-Za-z0-9_.])[-+]?\d[\d,]*(?:\.\d+)?")
RE_PATH = re.compile(r"(?:[A-Za-z]:\\|/)[\w./\\-]{2,}")
RE_QUOTED = re.compile(r"\"[^\"]*\"|'[^']*'")

LEVEL_WORDS = (
    "TRACE", "DEBUG", "INFO", "INFORMATION", "NOTICE", "WARN", "WARNING",
    "ERROR", "ERR", "CRITICAL", "CRIT", "FATAL", "ALERT", "EMERG", "SEVERE",
)
RE_LEVEL = re.compile(r"\b(" + "|".join(LEVEL_WORDS) + r")\b", re.IGNORECASE)

_LEVEL_CANON = {
    "INFORMATION": "INFO", "WARNING": "WARN", "ERR": "ERROR",
    "CRIT": "CRITICAL", "SEVERE": "ERROR", "EMERG": "FATAL",
}

# Various timestamp shapes
TS_PATTERNS = [
    # 2024-05-01T12:33:44.123456+05:00 / 2024-05-01 12:33:44,123
    r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:[.,]\d{1,9})?(?:Z|[+-]\d{2}:?\d{2})?",
    # 01/May/2024:12:33:44 +0500  (Apache)
    r"\d{2}/[A-Za-z]{3}/\d{4}:\d{2}:\d{2}:\d{2}\s*[+-]\d{4}",
    # May  1 12:33:44  (syslog)
    r"[A-Z][a-z]{2}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}",
    # 2024/05/01 12:33:44
    r"\d{4}/\d{2}/\d{2}[ T]\d{2}:\d{2}:\d{2}(?:[.,]\d+)?",
    # 01-05-2024 12:33:44
    r"\d{2}[-/]\d{2}[-/]\d{4}[ T]\d{2}:\d{2}:\d{2}(?:[.,]\d+)?",
    # epoch (10 or 13 digits) at line start
    r"^\d{10}(?:\.\d{1,6})?\b|^\d{13}\b",
]
RE_TS_ANY = re.compile("|".join(f"(?:{p})" for p in TS_PATTERNS))


# ---------------------------------------------------------------------------
# Format detectors
# ---------------------------------------------------------------------------
RE_APACHE_COMBINED = re.compile(
    r'^(?P<host>\S+)\s+(?P<ident>\S+)\s+(?P<user>\S+)\s+'
    r'\[(?P<ts>[^\]]+)\]\s+"(?P<request>[^"]*)"\s+'
    r'(?P<status>\d{3})\s+(?P<bytes>\S+)'
    r'(?:\s+"(?P<referer>[^"]*)"\s+"(?P<agent>[^"]*)")?'
)

RE_NGINX_ERROR = re.compile(
    r'^(?P<ts>\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2})\s+'
    r'\[(?P<level>\w+)\]\s+(?P<pid>\d+)#(?P<tid>\d+):\s*(?P<message>.*)$'
)

RE_SYSLOG = re.compile(
    r'^(?:<(?P<pri>\d+)>)?(?P<ts>[A-Z][a-z]{2}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})\s+'
    r'(?P<host>\S+)\s+(?P<process>[\w./-]+)(?:\[(?P<pid>\d+)\])?:\s*(?P<message>.*)$'
)

RE_PYLOG = re.compile(
    r'^(?P<ts>\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:[.,]\d+)?)\s*[-|]?\s*'
    r'(?P<logger>[\w.]+)?\s*[-|]\s*'
    r'(?P<level>' + "|".join(LEVEL_WORDS) + r')\s*[-|]\s*(?P<message>.*)$',
    re.IGNORECASE,
)

RE_ISO_LEVEL = re.compile(
    r'^\[?(?P<ts>\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:[.,]\d+)?(?:Z|[+-]\d{2}:?\d{2})?)\]?\s+'
    r'[\[(]?(?P<level>' + "|".join(LEVEL_WORDS) + r')[\])]?\s*[:\-]?\s*(?P<message>.*)$',
    re.IGNORECASE,
)

RE_LOGFMT = re.compile(r'(\w[\w.\-]*)=("([^"]*)"|\S+)')
RE_KV_CANDIDATE = re.compile(r'^\s*\w[\w.\-]*=\S')


@dataclass
class LogFormat:
    """Information about a detected log format."""

    name: str
    confidence: float
    parser: str
    sample_fields: list[str] = field(default_factory=list)

    def __str__(self) -> str:  # pragma: no cover - display only
        return f"{self.name} ({self.confidence:.0%})"


def _match_ratio(lines: list[str], rx: re.Pattern) -> float:
    if not lines:
        return 0.0
    hits = sum(1 for ln in lines if rx.match(ln))
    return hits / len(lines)


def _json_ratio(lines: list[str]) -> float:
    import json

    if not lines:
        return 0.0
    ok = 0
    for ln in lines:
        s = ln.strip()
        if not (s.startswith("{") and s.endswith("}")):
            continue
        try:
            json.loads(s)
            ok += 1
        except Exception:
            pass
    return ok / len(lines)


def _logfmt_ratio(lines: list[str]) -> float:
    if not lines:
        return 0.0
    ok = 0
    for ln in lines:
        if RE_KV_CANDIDATE.match(ln) and len(RE_LOGFMT.findall(ln)) >= 2:
            ok += 1
    return ok / len(lines)


def _delimiter_ratio(lines: list[str], delim: str) -> float:
    """A stable delimiter count across lines means the file is tabular."""
    if len(lines) < 2:
        return 0.0
    counts = [ln.count(delim) for ln in lines]
    if counts[0] == 0:
        return 0.0
    same = sum(1 for c in counts if c == counts[0])
    return same / len(counts)


def detect_format(sample_lines: list[str]) -> LogFormat:
    """Detect the log format from a sample of lines."""
    lines = [ln for ln in (s.rstrip("\n\r") for s in sample_lines) if ln.strip()][:400]
    if not lines:
        return LogFormat("empty", 0.0, "raw")

    scores: list[tuple[float, str, str]] = [
        (_json_ratio(lines), "JSON Lines", "json"),
        (_match_ratio(lines, RE_APACHE_COMBINED), "Apache/Nginx access", "apache"),
        (_match_ratio(lines, RE_NGINX_ERROR), "Nginx error", "nginx_error"),
        (_match_ratio(lines, RE_SYSLOG), "Syslog (RFC3164)", "syslog"),
        (_match_ratio(lines, RE_PYLOG), "Python logging", "pylog"),
        (_match_ratio(lines, RE_ISO_LEVEL), "ISO timestamp + level", "iso_level"),
        (_logfmt_ratio(lines), "logfmt (key=value)", "logfmt"),
        (_delimiter_ratio(lines, "|") * 0.8, "Pipe delimited", "delim|"),
        (_delimiter_ratio(lines, "\t") * 0.8, "TAB delimited", "delim\t"),
    ]
    scores.sort(key=lambda t: t[0], reverse=True)
    best_score, best_name, best_parser = scores[0]

    if best_score < 0.55:
        # Nothing matched — fall back to raw, but note whether timestamps exist
        has_ts = sum(1 for ln in lines if RE_TS_ANY.search(ln)) / len(lines)
        return LogFormat(
            "Free text" + (" (timestamped)" if has_ts > 0.5 else ""),
            max(0.3, has_ts),
            "raw",
        )
    return LogFormat(best_name, round(best_score, 3), best_parser)


# ---------------------------------------------------------------------------
# Parsers
# ---------------------------------------------------------------------------
def _canon_level(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    up = value.strip().upper()
    return _LEVEL_CANON.get(up, up)


def _parse_regex(lines: list[str], rx: re.Pattern) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for i, ln in enumerate(lines):
        m = rx.match(ln)
        if m:
            d = m.groupdict()
            d["_raw"] = ln
        else:
            d = {"message": ln, "_raw": ln}
        d["_line_no"] = i + 1
        rows.append(d)
    return pd.DataFrame(rows)


def _parse_json(lines: list[str]) -> pd.DataFrame:
    import json

    rows: list[dict[str, Any]] = []
    for i, ln in enumerate(lines):
        s = ln.strip()
        rec: dict[str, Any]
        try:
            obj = json.loads(s)
            rec = _flatten(obj) if isinstance(obj, dict) else {"value": obj}
        except Exception:
            rec = {"message": ln, "_parse_error": True}
        rec["_line_no"] = i + 1
        rows.append(rec)
    return pd.DataFrame(rows)


def _flatten(obj: dict, prefix: str = "", depth: int = 0) -> dict[str, Any]:
    """Flatten nested JSON into a single-level dict (max 4 levels)."""
    out: dict[str, Any] = {}
    for k, v in obj.items():
        key = f"{prefix}{k}"
        if isinstance(v, dict) and depth < 4:
            out.update(_flatten(v, key + ".", depth + 1))
        elif isinstance(v, list):
            if v and all(not isinstance(x, (dict, list)) for x in v):
                out[key] = ", ".join(str(x) for x in v)
            else:
                out[key] = str(v)
        else:
            out[key] = v
    return out


def _parse_logfmt(lines: list[str]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for i, ln in enumerate(lines):
        rec: dict[str, Any] = {}
        for key, raw, inner in RE_LOGFMT.findall(ln):
            rec[key] = inner if raw.startswith('"') else raw
        if not rec:
            rec = {"message": ln}
        rec["_line_no"] = i + 1
        rec["_raw"] = ln
        rows.append(rec)
    return pd.DataFrame(rows)


def _parse_delim(lines: list[str], delim: str) -> pd.DataFrame:
    parts = [ln.split(delim) for ln in lines]
    width = max(len(p) for p in parts)
    header = [h.strip() for h in parts[0]] if len(parts) > 1 else []
    use_header = (
        len(header) == width
        and all(h and not h.replace(".", "", 1).lstrip("-").isdigit() for h in header)
    )
    body = parts[1:] if use_header else parts
    cols = header if use_header else [f"col_{i + 1}" for i in range(width)]
    norm = [p + [None] * (width - len(p)) for p in body]
    df = pd.DataFrame(norm, columns=cols[:width])
    return df.map(lambda x: x.strip() if isinstance(x, str) else x)


def _parse_raw(lines: list[str]) -> pd.DataFrame:
    ts_list: list[Any] = []
    lvl_list: list[Any] = []
    msg_list: list[str] = []
    for ln in lines:
        mt = RE_TS_ANY.search(ln)
        ts_list.append(mt.group(0) if mt else None)
        ml = RE_LEVEL.search(ln)
        lvl_list.append(_canon_level(ml.group(1)) if ml else None)
        msg = ln
        if mt:
            msg = (ln[: mt.start()] + ln[mt.end():]).strip(" -\t[]:")
        msg_list.append(msg)
    return pd.DataFrame(
        {
            "ts": ts_list,
            "level": lvl_list,
            "message": msg_list,
            "_raw": lines,
            "_line_no": np.arange(1, len(lines) + 1),
        }
    )


PARSERS: dict[str, Callable[[list[str]], pd.DataFrame]] = {
    "json": _parse_json,
    "apache": lambda ls: _parse_regex(ls, RE_APACHE_COMBINED),
    "nginx_error": lambda ls: _parse_regex(ls, RE_NGINX_ERROR),
    "syslog": lambda ls: _parse_regex(ls, RE_SYSLOG),
    "pylog": lambda ls: _parse_regex(ls, RE_PYLOG),
    "iso_level": lambda ls: _parse_regex(ls, RE_ISO_LEVEL),
    "logfmt": _parse_logfmt,
    "raw": _parse_raw,
}


def parse_lines(lines: list[str], parser: str | None = None) -> tuple[pd.DataFrame, LogFormat]:
    """Convert log lines into a DataFrame.

    When ``parser`` is omitted the format is detected automatically.
    """
    lines = [ln.rstrip("\n\r") for ln in lines]
    lines = [ln for ln in lines if ln.strip()]
    if not lines:
        return pd.DataFrame(), LogFormat("empty", 0.0, "raw")

    fmt = detect_format(lines[:400]) if parser is None else LogFormat(parser, 1.0, parser)
    key = fmt.parser
    if key.startswith("delim"):
        df = _parse_delim(lines, key[5:] or "|")
    else:
        df = PARSERS.get(key, _parse_raw)(lines)

    df = _post_process(df)
    fmt.sample_fields = list(df.columns)[:12]
    return df, fmt


def _post_process(df: pd.DataFrame) -> pd.DataFrame:
    """Normalise the standard columns: ts → datetime, level → upper case."""
    if df.empty:
        return df
    df = df.copy()

    # timestamp candidates
    for cand in ("ts", "timestamp", "time", "@timestamp", "datetime", "date", "asctime"):
        if cand in df.columns:
            parsed = parse_timestamp_series(df[cand])
            if parsed.notna().mean() > 0.5:
                df["ts"] = parsed
                if cand != "ts":
                    df.drop(columns=[cand], inplace=True, errors="ignore")
                break

    for cand in ("level", "severity", "levelname", "loglevel", "lvl"):
        if cand in df.columns:
            df["level"] = df[cand].map(_canon_level)
            if cand != "level":
                df.drop(columns=[cand], inplace=True, errors="ignore")
            break

    for cand in ("message", "msg", "text", "log", "event"):
        if cand in df.columns and cand != "message":
            df.rename(columns={cand: "message"}, inplace=True)
            break

    # Apache specific: split "GET /path HTTP/1.1"
    if "request" in df.columns:
        req = df["request"].astype(str).str.split(" ", n=2, expand=True)
        if req.shape[1] >= 2:
            df["method"] = req[0]
            df["path"] = req[1]
        if req.shape[1] >= 3:
            df["protocol"] = req[2]

    for num_col in ("status", "bytes", "pid", "duration", "size", "response_time"):
        if num_col in df.columns:
            df[num_col] = pd.to_numeric(df[num_col], errors="coerce")

    # column order: ts, level, message first
    lead = [c for c in ("ts", "level", "message") if c in df.columns]
    rest = [c for c in df.columns if c not in lead]
    return df[lead + rest]


def parse_timestamp_series(s: pd.Series) -> pd.Series:
    """Convert a timestamp column of any shape into datetime (epoch included)."""
    if pd.api.types.is_datetime64_any_dtype(s):
        return s
    raw = s.astype(str).str.strip()

    # epoch seconds / milliseconds
    numeric = pd.to_numeric(raw, errors="coerce")
    if numeric.notna().mean() > 0.9:
        med = float(numeric.dropna().median()) if numeric.notna().any() else 0.0
        if 1e8 < med < 1e11:
            return pd.to_datetime(numeric, unit="s", errors="coerce")
        if 1e11 <= med < 1e14:
            return pd.to_datetime(numeric, unit="ms", errors="coerce")

    for fmt in ("%d/%b/%Y:%H:%M:%S %z", "%Y/%m/%d %H:%M:%S", "%b %d %H:%M:%S",
                "%d-%m-%Y %H:%M:%S", "%d/%m/%Y %H:%M:%S"):
        try:
            with warnings.catch_warnings():
                # Python 3.13+ warning for year-less syslog dates
                warnings.simplefilter("ignore")
                out = pd.to_datetime(raw, format=fmt, errors="coerce")
            if out.notna().mean() > 0.7:
                return out
        except Exception:
            continue
    try:
        return pd.to_datetime(raw, errors="coerce", format="mixed")
    except Exception:
        return pd.to_datetime(raw, errors="coerce")


# ---------------------------------------------------------------------------
# Entity extraction (enrichment)
# ---------------------------------------------------------------------------
ENTITY_RX: dict[str, re.Pattern] = {
    "ip": RE_IPV4,
    "ipv6": RE_IPV6,
    "mac": RE_MAC,
    "uuid": RE_UUID,
    "email": RE_EMAIL,
    "url": RE_URL,
}


def enrich(df: pd.DataFrame, text_col: str = "message",
           entities: list[str] | None = None) -> pd.DataFrame:
    """Extract entities such as IP/URL/UUID from a text column into new columns."""
    if text_col not in df.columns:
        return df
    out = df.copy()
    txt = out[text_col].astype(str)
    for name in (entities or list(ENTITY_RX)):
        rx = ENTITY_RX.get(name)
        if rx is None:
            continue
        found = txt.str.extract(f"({rx.pattern})", expand=False)
        if found.notna().any():
            out[f"e_{name}"] = found
    return out


# ---------------------------------------------------------------------------
# Log template mining — Drain-lite
# ---------------------------------------------------------------------------
def mask_line(text: str) -> str:
    """Replace the variable parts of a line with placeholders."""
    s = str(text)
    s = RE_URL.sub("<URL>", s)
    s = RE_EMAIL.sub("<EMAIL>", s)
    s = RE_UUID.sub("<UUID>", s)
    s = RE_IPV6.sub("<IPV6>", s)
    s = RE_IPV4.sub("<IP>", s)
    s = RE_MAC.sub("<MAC>", s)
    s = RE_TS_ANY.sub("<TS>", s)
    s = RE_HEX.sub("<HEX>", s)
    s = RE_PATH.sub("<PATH>", s)
    s = RE_QUOTED.sub("<STR>", s)
    s = RE_NUM.sub("<NUM>", s)
    return re.sub(r"\s+", " ", s).strip()


def mine_templates(messages: pd.Series, min_support: int = 1) -> tuple[pd.Series, pd.DataFrame]:
    """Mine templates from messages.

    Returns: (a template_id series aligned to the input, a table of templates).
    """
    masked = messages.astype(str).map(mask_line)

    counts = masked.value_counts()
    keep = counts[counts >= min_support]
    template_list = list(keep.index)
    tid_map = {t: i for i, t in enumerate(template_list)}
    tids = masked.map(lambda m: tid_map.get(m, -1))

    rows = []
    for t, i in tid_map.items():
        n = int(counts[t])
        rows.append(
            {
                "template_id": i,
                "template": t,
                "count": n,
                "ratio": n / max(1, len(masked)),
                "tokens": len(t.split()),
            }
        )
    table = pd.DataFrame(rows).sort_values("count", ascending=False).reset_index(drop=True)
    return tids, table


def rare_templates(table: pd.DataFrame, threshold: float = 0.001) -> pd.DataFrame:
    """Rarely seen (suspicious) templates — anomaly candidates."""
    if table.empty:
        return table
    return table[table["ratio"] <= threshold].copy()


def burst_detect(ts: pd.Series, freq: str = "1min", z: float = 3.0) -> pd.DataFrame:
    """Find event bursts over time."""
    s = pd.to_datetime(ts, errors="coerce").dropna()
    if s.empty:
        return pd.DataFrame(columns=["bucket", "count", "zscore", "is_burst"])
    series = pd.Series(1, index=pd.DatetimeIndex(s.dt.tz_localize(None))).resample(freq).sum()
    mu, sd = series.mean(), series.std(ddof=0)
    zs = (series - mu) / (sd if sd and sd > 0 else 1.0)
    return pd.DataFrame(
        {"bucket": series.index, "count": series.to_numpy(),
         "zscore": zs.to_numpy(), "is_burst": (zs > z).to_numpy()}
    )
