"""Project (session) save and load — a .dfp file (parquet + metadata inside a ZIP)."""
from __future__ import annotations

import datetime as _dt
import json
import zipfile
from pathlib import Path
from typing import Any

import pandas as pd

from ..config import VERSION

EXT = ".dfp"
META_NAME = "project.json"


def _safe(name: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "-_ " else "_" for ch in name).strip() or "data"


def save_project(path: str | Path, datasets: dict[str, pd.DataFrame],
                 active: str | None = None,
                 histories: dict[str, list[str]] | None = None,
                 notes: str = "") -> str:
    """Save every table into a single project file."""
    p = Path(path)
    if p.suffix.lower() != EXT:
        p = p.with_suffix(EXT)
    p.parent.mkdir(parents=True, exist_ok=True)

    meta: dict[str, Any] = {
        "version": VERSION,
        "created": _dt.datetime.now().isoformat(timespec="seconds"),
        "active": active,
        "notes": notes,
        "datasets": [],
    }

    with zipfile.ZipFile(p, "w", zipfile.ZIP_DEFLATED) as zf:
        for i, (name, df) in enumerate(datasets.items()):
            fname = f"data/{i:03d}_{_safe(name)}.parquet"
            buf = _to_parquet_bytes(df)
            zf.writestr(fname, buf)
            meta["datasets"].append({
                "name": name,
                "file": fname,
                "rows": int(len(df)),
                "cols": int(df.shape[1]),
                "columns": [str(c) for c in df.columns],
                "history": (histories or {}).get(name, []),
            })
        zf.writestr(META_NAME, json.dumps(meta, ensure_ascii=False, indent=2))
    return str(p)


def _to_parquet_bytes(df: pd.DataFrame) -> bytes:
    import io

    buf = io.BytesIO()
    safe = df.copy()
    # parquet rejects mixed types — coerce object columns to strings
    for c in safe.columns:
        if safe[c].dtype == object:
            try:
                safe[c] = safe[c].astype(str).where(safe[c].notna(), None)
            except Exception:
                safe[c] = safe[c].map(lambda v: None if v is None else str(v))
    safe.columns = [str(c) for c in safe.columns]
    try:
        safe.to_parquet(buf, index=False)
    except Exception:
        buf = io.BytesIO()
        safe.to_parquet(buf, index=False, engine="pyarrow")
    return buf.getvalue()


def load_project(path: str | Path) -> tuple[dict[str, pd.DataFrame], dict[str, Any]]:
    """Read a project file and return its tables plus metadata."""
    import io

    p = Path(path)
    datasets: dict[str, pd.DataFrame] = {}
    with zipfile.ZipFile(p) as zf:
        meta = json.loads(zf.read(META_NAME).decode("utf-8"))
        for entry in meta.get("datasets", []):
            try:
                raw = zf.read(entry["file"])
                datasets[entry["name"]] = pd.read_parquet(io.BytesIO(raw))
            except KeyError:
                continue
    return datasets, meta


def project_info(path: str | Path) -> dict[str, Any]:
    """Read a short summary without loading the whole file."""
    with zipfile.ZipFile(Path(path)) as zf:
        return json.loads(zf.read(META_NAME).decode("utf-8"))
