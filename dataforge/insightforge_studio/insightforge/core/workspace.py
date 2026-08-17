from __future__ import annotations

from collections import deque
from dataclasses import asdict
from typing import Iterable

import pandas as pd

from .types import AuditEvent, Dataset


class Workspace:
    """In-memory dataset catalog with bounded revision history and audit trail."""

    def __init__(self, history_limit: int = 12) -> None:
        self._datasets: dict[str, Dataset] = {}
        self._active_id: str | None = None
        self._undo: dict[str, deque[tuple[str, pd.DataFrame]]] = {}
        self._redo: dict[str, deque[tuple[str, pd.DataFrame]]] = {}
        self.audit: list[AuditEvent] = []
        self.history_limit = max(1, history_limit)

    @property
    def datasets(self) -> list[Dataset]:
        return list(self._datasets.values())

    @property
    def active(self) -> Dataset | None:
        return self._datasets.get(self._active_id or "")

    def get(self, dataset_id: str) -> Dataset:
        try:
            return self._datasets[dataset_id]
        except KeyError as exc:
            raise KeyError(f"Dataset topilmadi: {dataset_id}") from exc

    def add(self, name: str, frame: pd.DataFrame, *, source: str = "memory",
            kind: str = "table", activate: bool = True) -> Dataset:
        clean = self._unique_name(name.strip() or "Dataset")
        dataset = Dataset(name=clean, frame=frame.copy(deep=False), source=source, kind=kind)
        self._datasets[dataset.id] = dataset
        self._undo[dataset.id] = deque(maxlen=self.history_limit)
        self._redo[dataset.id] = deque(maxlen=self.history_limit)
        if activate:
            self._active_id = dataset.id
        self.audit.append(AuditEvent("dataset.add", dataset.id,
                                     {"name": clean, "rows": len(frame), "cols": frame.shape[1]}))
        return dataset

    def remove(self, dataset_id: str) -> None:
        ds = self.get(dataset_id)
        self._datasets.pop(dataset_id)
        self._undo.pop(dataset_id, None)
        self._redo.pop(dataset_id, None)
        if self._active_id == dataset_id:
            self._active_id = next(iter(self._datasets), None)
        self.audit.append(AuditEvent("dataset.remove", dataset_id, {"name": ds.name}))

    def activate(self, dataset_id: str) -> Dataset:
        ds = self.get(dataset_id)
        self._active_id = dataset_id
        return ds

    def rename(self, dataset_id: str, name: str) -> str:
        ds = self.get(dataset_id)
        old = ds.name
        ds.name = self._unique_name(name.strip() or old, exclude=dataset_id)
        self.audit.append(AuditEvent("dataset.rename", dataset_id,
                                     {"old": old, "new": ds.name}))
        return ds.name

    def commit(self, dataset_id: str, frame: pd.DataFrame, action: str,
               detail: dict | None = None) -> Dataset:
        ds = self.get(dataset_id)
        self._undo[dataset_id].append((action, ds.frame))
        self._redo[dataset_id].clear()
        ds.frame = frame
        ds.revision += 1
        payload = {"revision": ds.revision, "rows": len(frame), "cols": frame.shape[1]}
        payload.update(detail or {})
        self.audit.append(AuditEvent(action, dataset_id, payload))
        return ds

    def can_undo(self, dataset_id: str) -> bool:
        return bool(self._undo.get(dataset_id))

    def can_redo(self, dataset_id: str) -> bool:
        return bool(self._redo.get(dataset_id))

    def undo(self, dataset_id: str) -> Dataset:
        ds = self.get(dataset_id)
        if not self._undo[dataset_id]:
            return ds
        action, previous = self._undo[dataset_id].pop()
        self._redo[dataset_id].append((action, ds.frame))
        ds.frame = previous
        ds.revision += 1
        self.audit.append(AuditEvent("history.undo", dataset_id, {"action": action}))
        return ds

    def redo(self, dataset_id: str) -> Dataset:
        ds = self.get(dataset_id)
        if not self._redo[dataset_id]:
            return ds
        action, following = self._redo[dataset_id].pop()
        self._undo[dataset_id].append((action, ds.frame))
        ds.frame = following
        ds.revision += 1
        self.audit.append(AuditEvent("history.redo", dataset_id, {"action": action}))
        return ds

    def clear(self) -> None:
        self._datasets.clear()
        self._undo.clear()
        self._redo.clear()
        self._active_id = None
        self.audit.append(AuditEvent("workspace.clear"))

    def summary(self) -> dict:
        return {
            "datasets": len(self._datasets),
            "rows": sum(len(d.frame) for d in self._datasets.values()),
            "memory_bytes": sum(d.memory_bytes for d in self._datasets.values()),
            "active_id": self._active_id,
            "audit_events": len(self.audit),
        }

    def audit_records(self) -> list[dict]:
        return [asdict(e) for e in self.audit]

    def extend(self, datasets: Iterable[Dataset]) -> None:
        for ds in datasets:
            self._datasets[ds.id] = ds
            self._undo[ds.id] = deque(maxlen=self.history_limit)
            self._redo[ds.id] = deque(maxlen=self.history_limit)
            self._active_id = self._active_id or ds.id

    def _unique_name(self, name: str, exclude: str | None = None) -> str:
        occupied = {d.name for key, d in self._datasets.items() if key != exclude}
        if name not in occupied:
            return name
        i = 2
        while f"{name} ({i})" in occupied:
            i += 1
        return f"{name} ({i})"
