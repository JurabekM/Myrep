"""GUI umumiy holati va signal shinasi."""
from __future__ import annotations

from dataclasses import replace

from PySide6.QtCore import QObject, Signal

from ..config import FLAG_CATALOG, Mode, ProtocolConfig, hardened_config, spec_config
from ..sim.trace import Event, Trace
from ..sim.world import World


class AppState(QObject):
    config_changed = Signal()
    world_changed = Signal()
    event_logged = Signal(object)

    def __init__(self) -> None:
        super().__init__()
        self.trace = Trace()
        self.trace.subscribe(self._on_event)
        self.cfg: ProtocolConfig = spec_config()
        self.world = World(self.cfg, self.trace)

    # ------------------------------------------------------------------
    def _on_event(self, ev: Event) -> None:
        self.event_logged.emit(ev)

    # ------------------------------------------------------------------
    def set_mode(self, mode: Mode) -> None:
        if mode is Mode.SPEC:
            self.cfg = spec_config()
        elif mode is Mode.HARDENED:
            self.cfg = hardened_config()
        else:
            self.cfg = replace(self.cfg, mode=Mode.CUSTOM)
        self.rebuild()

    def set_flag(self, key: str, value: bool) -> None:
        self.cfg = replace(self.cfg, mode=Mode.CUSTOM, **{key: value})
        self.rebuild()

    def set_param(self, key: str, value) -> None:
        self.cfg = replace(self.cfg, **{key: value})
        self.rebuild()

    def rebuild(self) -> None:
        self.trace.clear()
        self.world.reconfigure(self.cfg)
        self.config_changed.emit()
        self.world_changed.emit()

    # ------------------------------------------------------------------
    @property
    def fixed_count(self) -> int:
        return len(self.cfg.enabled_flags())

    @property
    def total_flags(self) -> int:
        return len(FLAG_CATALOG)
