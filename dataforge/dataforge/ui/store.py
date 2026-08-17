"""Markaziy ma'lumot ombori — barcha sahifalar shu obyekt orqali gaplashadi."""
from __future__ import annotations

from typing import Any

import pandas as pd
from PySide6.QtCore import QObject, Signal

from ..core.transform import History, apply_op, describe_op


class DataStore(QObject):
    """Yuklangan jadvallar, faol jadval va undo/redo tarixini boshqaradi."""

    datasets_changed = Signal()            # ro'yxat o'zgardi
    active_changed = Signal(str)           # faol jadval almashdi
    data_changed = Signal()                # faol jadval mazmuni o'zgardi
    message = Signal(str, str)             # (matn, daraja: info|success|warn|error)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._data: dict[str, pd.DataFrame] = {}
        self._meta: dict[str, dict[str, Any]] = {}
        self._hist: dict[str, History] = {}
        self._active: str | None = None

    # ------------------------------------------------------------- ro'yxat
    @property
    def names(self) -> list[str]:
        return list(self._data)

    @property
    def active_name(self) -> str | None:
        return self._active

    @property
    def is_empty(self) -> bool:
        return not self._data

    def meta(self, name: str | None = None) -> dict[str, Any]:
        return self._meta.get(name or self._active or "", {})

    def get(self, name: str) -> pd.DataFrame | None:
        return self._data.get(name)

    def df(self) -> pd.DataFrame:
        """Faol jadval (bo'sh bo'lsa — bo'sh DataFrame)."""
        if self._active and self._active in self._data:
            return self._data[self._active]
        return pd.DataFrame()

    def history(self, name: str | None = None) -> History | None:
        return self._hist.get(name or self._active or "")

    # -------------------------------------------------------------- qo'shish
    def add(self, name: str, df: pd.DataFrame, meta: dict[str, Any] | None = None,
            activate: bool = True) -> str:
        """Yangi jadval qo'shadi (nom band bo'lsa raqam qo'shiladi)."""
        base, i = name or "dataset", 2
        while name in self._data:
            name = f"{base} ({i})"
            i += 1
        self._data[name] = df
        self._meta[name] = meta or {}
        self._hist[name] = History(df, label=f"Yuklandi · {df.shape[0]:,}×{df.shape[1]}")
        self.datasets_changed.emit()
        if activate:
            self.set_active(name)
        self.message.emit(f"'{name}' yuklandi: {len(df):,} qator × {df.shape[1]} ustun",
                          "success")
        return name

    def remove(self, name: str) -> None:
        if name not in self._data:
            return
        self._data.pop(name, None)
        self._meta.pop(name, None)
        self._hist.pop(name, None)
        if self._active == name:
            self._active = next(iter(self._data), None)
            self.active_changed.emit(self._active or "")
        self.datasets_changed.emit()
        self.data_changed.emit()

    def rename(self, old: str, new: str) -> None:
        if old not in self._data or not new or new in self._data:
            return
        self._data[new] = self._data.pop(old)
        self._meta[new] = self._meta.pop(old, {})
        self._hist[new] = self._hist.pop(old)
        if self._active == old:
            self._active = new
        self.datasets_changed.emit()
        self.active_changed.emit(self._active or "")

    def clear(self) -> None:
        self._data.clear()
        self._meta.clear()
        self._hist.clear()
        self._active = None
        self.datasets_changed.emit()
        self.active_changed.emit("")
        self.data_changed.emit()

    def set_active(self, name: str) -> None:
        if name in self._data and name != self._active:
            self._active = name
            self.active_changed.emit(name)
            self.data_changed.emit()
        elif name in self._data:
            self.data_changed.emit()

    # ----------------------------------------------------------- o'zgartirish
    def commit(self, df: pd.DataFrame, label: str, name: str | None = None) -> None:
        """Yangi holatni tarixga yozib, faol jadvalni yangilaydi."""
        target = name or self._active
        if not target:
            return
        self._data[target] = df
        hist = self._hist.get(target)
        if hist is None:
            self._hist[target] = History(df, label)
        else:
            hist.push(df, label)
        self.data_changed.emit()
        self.message.emit(f"{label} → {df.shape[0]:,}×{df.shape[1]}", "info")

    def run_op(self, key: str, **params: Any) -> bool:
        """Registrdagi tahrirlash amalini faol jadvalga qo'llaydi."""
        df = self.df()
        if df.empty and key not in ("reset_index",):
            self.message.emit("Avval ma'lumot yuklang", "warn")
            return False
        try:
            new = apply_op(df, key, **params)
        except Exception as exc:
            self.message.emit(f"Amal bajarilmadi: {exc}", "error")
            return False
        self.commit(new, describe_op(key, params))
        return True

    def set_cell(self, row: int, col: str, value: Any) -> bool:
        """Bitta katakni tahrirlaydi (tarixga yoziladi)."""
        df = self.df()
        if df.empty or col not in df.columns or row >= len(df):
            return False
        new = df.copy()
        try:
            series = new[col]
            if pd.api.types.is_numeric_dtype(series) and value != "":
                cast: Any = pd.to_numeric(value, errors="coerce")
            elif pd.api.types.is_datetime64_any_dtype(series):
                cast = pd.to_datetime(value, errors="coerce")
            elif pd.api.types.is_bool_dtype(series):
                cast = str(value).strip().lower() in ("1", "true", "ha", "yes")
            else:
                cast = value
            if isinstance(series.dtype, pd.CategoricalDtype):
                if cast not in series.cat.categories:
                    new[col] = series.cat.add_categories([cast])
            new.iloc[row, new.columns.get_loc(col)] = cast
        except Exception as exc:
            self.message.emit(f"Katak tahrirlanmadi: {exc}", "error")
            return False
        self.commit(new, f"Katak tahrirlandi [{row}, {col}]")
        return True

    def add_row(self, at: int | None = None) -> None:
        df = self.df()
        blank = pd.DataFrame([{c: None for c in df.columns}])
        pos = len(df) if at is None else max(0, min(at, len(df)))
        new = pd.concat([df.iloc[:pos], blank, df.iloc[pos:]], ignore_index=True)
        self.commit(new, "Yangi qator qo'shildi")

    def add_column(self, name: str, default: Any = None) -> None:
        df = self.df().copy()
        if not name or name in df.columns:
            self.message.emit("Ustun nomi bo'sh yoki band", "warn")
            return
        df[name] = default
        self.commit(df, f"Ustun qo'shildi: {name}")

    # ----------------------------------------------------------- undo / redo
    def undo(self) -> None:
        hist = self.history()
        if hist and hist.can_undo:
            label = hist.current_label
            self._data[self._active] = hist.undo()  # type: ignore[index]
            self.data_changed.emit()
            self.message.emit(f"Bekor qilindi: {label}", "info")

    def redo(self) -> None:
        hist = self.history()
        if hist and hist.can_redo:
            self._data[self._active] = hist.redo()  # type: ignore[index]
            self.data_changed.emit()
            self.message.emit(f"Qaytarildi: {hist.current_label}", "info")

    def goto_history(self, idx: int) -> None:
        hist = self.history()
        if hist:
            self._data[self._active] = hist.goto(idx)  # type: ignore[index]
            self.data_changed.emit()

    def history_labels(self) -> list[str]:
        hist = self.history()
        return hist.labels() if hist else []

    def can_undo(self) -> bool:
        hist = self.history()
        return bool(hist and hist.can_undo)

    def can_redo(self) -> bool:
        hist = self.history()
        return bool(hist and hist.can_redo)
