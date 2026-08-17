from __future__ import annotations

import json
import re
from collections import Counter

import pandas as pd

APACHE = re.compile(
    r'(?P<ip>\S+) \S+ \S+ \[(?P<timestamp>[^]]+)] "(?P<method>[A-Z]+) '
    r'(?P<path>\S+)(?: [^"]+)?" (?P<status>\d{3}) (?P<bytes>\S+)')
STANDARD = re.compile(
    r"(?P<timestamp>\d{4}-\d{2}-\d{2}[ T][^ ]+)\s+[-|]?\s*"
    r"(?P<level>TRACE|DEBUG|INFO|WARN|WARNING|ERROR|CRITICAL)\s+[-|:]?\s*(?P<message>.*)", re.I)
SYSLOG = re.compile(
    r"(?P<timestamp>[A-Z][a-z]{2}\s+\d+\s+\d{2}:\d{2}:\d{2})\s+"
    r"(?P<host>\S+)\s+(?P<process>[^:]+):\s*(?P<message>.*)")


def parse_log_lines(lines: list[str]) -> tuple[pd.DataFrame, str]:
    clean = [line.rstrip("\r\n") for line in lines if line.strip()]
    if not clean:
        return pd.DataFrame(columns=["message"]), "empty"
    sample = clean[:100]
    scores = {
        "json": sum(_is_json(line) for line in sample),
        "apache": sum(bool(APACHE.match(line)) for line in sample),
        "standard": sum(bool(STANDARD.match(line)) for line in sample),
        "syslog": sum(bool(SYSLOG.match(line)) for line in sample),
    }
    parser = max(scores, key=scores.get)
    if scores[parser] < max(2, len(sample) * .35):
        parser = "raw"
    records = [_parse_line(line, parser) for line in clean]
    frame = pd.DataFrame(records)
    if "timestamp" in frame:
        if parser == "apache":
            frame["timestamp"] = pd.to_datetime(
                frame["timestamp"], format="%d/%b/%Y:%H:%M:%S %z", errors="coerce", utc=True)
        else:
            frame["timestamp"] = pd.to_datetime(frame["timestamp"], errors="coerce", utc=True)
    if "status" in frame:
        frame["status"] = pd.to_numeric(frame["status"], errors="coerce").astype("Int64")
    if "bytes" in frame:
        frame["bytes"] = pd.to_numeric(frame["bytes"], errors="coerce")
    return frame, parser


def mine_templates(messages: pd.Series) -> pd.DataFrame:
    templates = messages.fillna("").astype(str).map(mask_message)
    counts = templates.value_counts()
    total = max(1, len(templates))
    return pd.DataFrame({"template": counts.index, "count": counts.values,
                         "share": counts.values / total})


def mask_message(message: str) -> str:
    value = re.sub(r"\b[0-9a-f]{8}-[0-9a-f-]{27,}\b", "<UUID>", message, flags=re.I)
    value = re.sub(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", "<IP>", value)
    value = re.sub(r"https?://\S+", "<URL>", value)
    value = re.sub(r"\b0x[0-9a-f]+\b", "<HEX>", value, flags=re.I)
    value = re.sub(r"\b\d+(?:\.\d+)?\b", "<NUM>", value)
    return re.sub(r"\s+", " ", value).strip()


def level_summary(frame: pd.DataFrame) -> pd.DataFrame:
    if "level" not in frame:
        return pd.DataFrame(columns=["level", "count", "share"])
    counts = frame["level"].astype("string").str.upper().value_counts()
    return pd.DataFrame({"level": counts.index, "count": counts.values,
                         "share": counts.values / max(1, counts.sum())})


def burst_detection(frame: pd.DataFrame, timestamp: str = "timestamp",
                    frequency: str = "5min", z_threshold: float = 3.0) -> pd.DataFrame:
    dates = pd.to_datetime(frame[timestamp], errors="coerce").dropna()
    counts = dates.to_frame("timestamp").set_index("timestamp").resample(frequency).size()
    std = counts.std()
    zscore = (counts - counts.mean()) / (std if std else 1)
    return pd.DataFrame({"timestamp": counts.index, "events": counts.values,
                         "zscore": zscore.values, "is_burst": zscore.values >= z_threshold})


def entity_counts(messages: pd.Series) -> pd.DataFrame:
    patterns = {
        "ip": r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
        "email": r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b",
        "url": r"https?://\S+",
        "uuid": r"\b[0-9a-f]{8}-[0-9a-f-]{27,}\b",
    }
    rows = []
    text = "\n".join(messages.dropna().astype(str))
    for kind, pattern in patterns.items():
        for value, count in Counter(re.findall(pattern, text, re.I)).most_common(25):
            rows.append({"kind": kind, "value": value, "count": count})
    return pd.DataFrame(rows)


def _is_json(line: str) -> bool:
    try:
        return isinstance(json.loads(line), dict)
    except (json.JSONDecodeError, TypeError):
        return False


def _parse_line(line: str, parser: str) -> dict:
    if parser == "json":
        record = pd.json_normalize(json.loads(line)).to_dict(orient="records")[0]
    elif parser == "apache":
        record = APACHE.match(line).groupdict()  # type: ignore[union-attr]
    elif parser == "standard":
        record = STANDARD.match(line).groupdict()  # type: ignore[union-attr]
    elif parser == "syslog":
        record = SYSLOG.match(line).groupdict()  # type: ignore[union-attr]
    else:
        record = {"message": line}
    record["_raw"] = line
    return record
