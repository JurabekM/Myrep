"""Tizim holati: CPU, RAM, yadro jarayoni, disklar va jonli grafik."""

from typing import Any

from PyQt6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QLabel, QProgressBar

from srv1_shell.api import Reply
from srv1_shell.charts import LineChart
from srv1_shell.common import AppContext, Card, Page, muted, section_title

STATS_TOPIC = "system.stats"


def level_for(percent: float) -> str:
    return "bad" if percent >= 90 else "warn" if percent >= 75 else "ok"


def set_level(bar: QProgressBar, percent: float) -> None:
    """Rang darajasini o'zgartiradi; QSS xususiyat bo'yicha qayta qo'llanadi."""
    bar.setValue(round(percent))
    level = level_for(percent)
    if bar.property("level") != level:
        bar.setProperty("level", level)
        style = bar.style()
        if style is not None:
            style.unpolish(bar)
            style.polish(bar)


class SystemPage(Page):
    def __init__(self, ctx: AppContext) -> None:
        super().__init__(ctx)
        t = ctx.i18n.t
        self.add_title(t("nav.system"))
        self.cpu = Card(t("system.cpu"))
        self.memory = Card(t("system.memory"))
        self.core = Card(t("system.core"))
        cards = QHBoxLayout()
        cards.setSpacing(14)
        for card in (self.cpu, self.memory, self.core):
            cards.addWidget(card, 1)
        self.layout_root.addLayout(cards)

        self.layout_root.addWidget(section_title(t("system.chart")))
        self.chart = LineChart(
            [t("system.series.cpu"), t("system.series.memory")], window=120, y_range=(0, 100)
        )
        self.layout_root.addWidget(self.chart, 1)

        self.layout_root.addWidget(section_title(t("system.disks")))
        disks_frame = QFrame()
        disks_frame.setObjectName("Card")
        self._disks = QGridLayout(disks_frame)
        self._disks.setContentsMargins(16, 12, 16, 12)
        self._disks.setColumnStretch(1, 1)
        self._disk_rows: dict[str, tuple[QProgressBar, QLabel]] = {}
        self.layout_root.addWidget(disks_frame)

        self.error = QLabel("")
        self.error.setObjectName("ErrorText")
        self.layout_root.addWidget(self.error)
        ctx.events.received.connect(self._on_event)

    def activate(self) -> None:
        self.ctx.api.get("/api/v1/system", self._on_reply, owner=self)

    def _on_reply(self, reply: Reply) -> None:
        if not reply.ok:
            self.error.setText(self.describe_error(reply))
            return
        self.error.setText("")
        self.show_snapshot(reply.data)

    def _on_event(self, topic: str, data: dict[str, Any]) -> None:
        if topic == STATS_TOPIC:
            self.error.setText("")
            self.show_snapshot(data)

    def show_snapshot(self, snapshot: dict[str, Any]) -> None:
        i18n = self.ctx.i18n
        cpu, memory, process = snapshot["cpu"], snapshot["memory"], snapshot["process"]
        self.cpu.set(i18n.percent(cpu["percent"]), i18n.t("system.cores", n=cpu["logical"]))
        self.memory.set(
            i18n.percent(memory["percent"]),
            i18n.t(
                "system.memory_detail",
                used=i18n.size(memory["used"]),
                total=i18n.size(memory["total"]),
            ),
        )
        self.core.set(
            i18n.size(process["rss"]),
            i18n.t("system.core_detail", pid=process["pid"], threads=process["threads"]),
        )
        self.chart.append([cpu["percent"], memory["percent"]])
        for disk in snapshot["disks"]:
            self._show_disk(disk)

    def _show_disk(self, disk: dict[str, Any]) -> None:
        i18n = self.ctx.i18n
        mount = str(disk["mount"])
        if mount not in self._disk_rows:
            row = len(self._disk_rows)
            bar = QProgressBar()
            bar.setRange(0, 100)
            bar.setTextVisible(True)
            detail = muted(wrap=False)
            self._disks.addWidget(QLabel(mount), row, 0)
            self._disks.addWidget(bar, row, 1)
            self._disks.addWidget(detail, row, 2)
            self._disk_rows[mount] = (bar, detail)
        bar, detail = self._disk_rows[mount]
        set_level(bar, float(disk["percent"]))
        detail.setText(
            i18n.t("system.disk_free", free=i18n.size(disk["free"]), total=i18n.size(disk["total"]))
        )
