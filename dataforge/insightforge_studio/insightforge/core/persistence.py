from __future__ import annotations

import io
import json
import zipfile
from dataclasses import asdict
from pathlib import Path

import pandas as pd

from ..config import APP_VERSION, MAX_ZIP_EXPANDED_BYTES, MAX_ZIP_MEMBERS
from .types import AuditEvent, Dataset, utc_now
from .workspace import Workspace


def save_workspace(workspace: Workspace, path: str | Path) -> Path:
    p = Path(path).with_suffix(".ifs")
    p.parent.mkdir(parents=True, exist_ok=True)
    manifest = {"format": 1, "app_version": APP_VERSION, "saved_at": utc_now(),
                "summary": workspace.summary(), "datasets": [],
                "audit": workspace.audit_records()}
    with zipfile.ZipFile(p, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for dataset in workspace.datasets:
            buffer = io.BytesIO()
            safe = dataset.frame.copy()
            for column in safe.select_dtypes(include="object").columns:
                safe[column] = safe[column].map(lambda value: None if pd.isna(value) else str(value))
            safe.to_parquet(buffer, index=False)
            filename = f"data/{dataset.id}.parquet"
            archive.writestr(filename, buffer.getvalue())
            manifest["datasets"].append({
                "id": dataset.id, "name": dataset.name, "source": dataset.source,
                "kind": dataset.kind, "created_at": dataset.created_at,
                "tags": dataset.tags, "notes": dataset.notes,
                "revision": dataset.revision, "file": filename,
            })
        archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
    return p


def load_workspace(path: str | Path) -> Workspace:
    p = Path(path)
    with zipfile.ZipFile(p) as archive:
        members = archive.infolist()
        if len(members) > MAX_ZIP_MEMBERS:
            raise ValueError("Workspace ichida juda ko'p fayl")
        if sum(member.file_size for member in members) > MAX_ZIP_EXPANDED_BYTES:
            raise ValueError("Workspace ochilgan hajmi limitdan katta")
        manifest = json.loads(archive.read("manifest.json").decode("utf-8"))
        if manifest.get("format") != 1:
            raise ValueError("Qo'llab-quvvatlanmaydigan workspace formati")
        datasets = []
        for item in manifest.get("datasets", []):
            raw = archive.read(item["file"])
            frame = pd.read_parquet(io.BytesIO(raw))
            datasets.append(Dataset(name=item["name"], frame=frame, source=item["source"],
                                    kind=item["kind"], id=item["id"],
                                    created_at=item["created_at"], tags=item.get("tags", []),
                                    notes=item.get("notes", ""), revision=item.get("revision", 0)))
    workspace = Workspace()
    workspace.extend(datasets)
    workspace.audit = [AuditEvent(**event) for event in manifest.get("audit", [])]
    return workspace

