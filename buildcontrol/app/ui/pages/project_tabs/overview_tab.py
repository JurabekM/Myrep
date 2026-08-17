"""Project passport and live status — a working sheet, not a dashboard."""

from __future__ import annotations

from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from app.services import estimate_service, project_service, purchase_service, stage_service
from app.services.permissions import Perm
from app.ui.pages.base_page import BasePage
from app.ui.styles.theme import COLORS, SPACING, SPACING_SM
from app.ui.widgets.common import BudgetBar, Card, MetricCard, button
from app.ui.widgets.table import BADGE, DATE, MONEY, NUMBER, Col, DataTable
from app.utils.formatting import fmt_money, fmt_percent
from app.utils.i18n import tr
from app.utils.labels import purchase_status_label


class OverviewTab(BasePage):
    """Compact operational summary of one project."""

    permission = Perm.PROJECT_VIEW

    def __init__(self, project_id: int, goto, parent: QWidget | None = None) -> None:
        super().__init__("", "", parent, show_header=False, compact=True)
        self.project_id = project_id
        self._goto = goto

        metrics = QHBoxLayout()
        metrics.setSpacing(SPACING)
        self.budget_card = MetricCard(tr("budget"))
        self.committed_card = MetricCard(tr("committed_cost"))
        self.actual_card = MetricCard(tr("actual_cost"))
        self.remaining_card = MetricCard(tr("remaining_funds"))
        self.estimate_card = MetricCard(tr("estimate_total"))
        for card in (
            self.budget_card,
            self.committed_card,
            self.actual_card,
            self.remaining_card,
            self.estimate_card,
        ):
            metrics.addWidget(card, 1)
        self.root.addLayout(metrics)

        usage = Card(tr("budget_usage"))
        self.usage_bar = BudgetBar()
        usage.body().addWidget(self.usage_bar)
        self.usage_label = QLabel("—")
        self.usage_label.setObjectName("CardHint")
        usage.body().addWidget(self.usage_label)
        self.root.addWidget(usage)

        grid = QGridLayout()
        grid.setSpacing(SPACING)
        grid.addWidget(self._build_delays(), 0, 0)
        grid.addWidget(self._build_pending(), 0, 1)
        grid.addWidget(self._build_overruns(), 1, 0)
        grid.addWidget(self._build_activity(), 1, 1)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        self.root.addLayout(grid, 1)

    # -- panels -------------------------------------------------------------------- #
    def _build_delays(self) -> QWidget:
        card = Card(tr("delayed_stages"))
        self.delays_table = DataTable(
            [
                Col("name", tr("stage"), stretch=True),
                Col("plan_end", tr("plan_end"), DATE, width=110),
                Col("overdue_days", tr("delay_days"), NUMBER, width=100),
                Col("progress_percent", tr("percent_done"), NUMBER, width=100),
            ],
            searchable=False,
            paginated=False,
        )
        card.body().addWidget(self.delays_table, 1)
        link = button(tr("tab_stages"), "stage", "LinkButton")
        link.clicked.connect(lambda: self._goto("tab_stages"))
        card.body().addWidget(link)
        return card

    def _build_pending(self) -> QWidget:
        card = Card(tr("pending_purchases"))
        self.pending_table = DataTable(
            [
                Col("number", "№", width=90),
                Col("title", tr("product_service"), stretch=True),
                Col("est_total", tr("est_price"), MONEY, width=140),
                Col(
                    "status",
                    tr("status"),
                    BADGE,
                    width=140,
                    badge=lambda r: (purchase_status_label(r["status"]), "warning"),
                ),
            ],
            searchable=False,
            paginated=False,
        )
        card.body().addWidget(self.pending_table, 1)
        link = button(tr("tab_purchases"), "purchase", "LinkButton")
        link.clicked.connect(lambda: self._goto("tab_purchases"))
        card.body().addWidget(link)
        return card

    def _build_overruns(self) -> QWidget:
        card = Card(tr("over_budget"))
        self.overrun_table = DataTable(
            [
                Col("code", tr("code"), width=80),
                Col("name", tr("item"), stretch=True),
                Col("plan_total", tr("plan_total"), MONEY, width=140),
                Col("actual_total", tr("actual_total"), MONEY, width=140),
                Col(
                    "variance",
                    tr("variance"),
                    MONEY,
                    width=140,
                    color=lambda r: COLORS.danger if r["variance"] > 0 else COLORS.success,
                ),
            ],
            searchable=False,
            paginated=False,
        )
        card.body().addWidget(self.overrun_table, 1)
        link = button(tr("tab_estimate"), "estimate", "LinkButton")
        link.clicked.connect(lambda: self._goto("tab_estimate"))
        card.body().addWidget(link)
        return card

    def _build_activity(self) -> QWidget:
        card = Card(tr("recent_activity"))
        self.activity_box = QVBoxLayout()
        self.activity_box.setSpacing(SPACING_SM)
        holder = QWidget()
        holder.setLayout(self.activity_box)
        card.body().addWidget(holder, 1)
        link = button(tr("tab_activity"), "audit", "LinkButton")
        link.clicked.connect(lambda: self._goto("tab_activity"))
        card.body().addWidget(link)
        return card

    # -- data ---------------------------------------------------------------------- #
    def refresh(self) -> None:
        """Recompute every figure of the overview."""
        totals = project_service.get_totals(self.project_id)
        self.budget_card.update_values(fmt_money(totals.planned_budget))
        self.committed_card.update_values(
            fmt_money(totals.committed), f"{tr('pending_purchases')}: {totals.pending_purchases}"
        )
        self.actual_card.update_values(
            fmt_money(totals.actual),
            f"{tr('materials')}: {fmt_money(totals.material_issued)}",
            "danger" if totals.is_over_budget else "neutral",
        )
        self.remaining_card.update_values(
            fmt_money(totals.remaining),
            "",
            "danger" if totals.remaining < 0 else "success",
        )
        self.estimate_card.update_values(
            fmt_money(totals.estimate_total),
            f"{tr('over_budget')}: {totals.over_budget_items}",
            "warning" if totals.over_budget_items else "neutral",
        )
        self.usage_bar.set_ratio(totals.usage_ratio)
        self.usage_label.setText(
            f"{fmt_percent(totals.usage_ratio * 100)} · {tr('stages_summary')}: "
            f"{totals.done_stages}/{totals.total_stages} · "
            f"{tr('percent_done')}: {fmt_percent(totals.avg_progress)}"
        )

        self.delays_table.set_rows(stage_service.delayed_stages(self.project_id))
        pending = [
            row
            for row in purchase_service.list_requests(project_id=self.project_id)
            if row["status"] in ("submitted", "draft")
        ]
        self.pending_table.set_rows(pending)

        tree = estimate_service.load_tree(self.project_id)
        overruns = [
            {
                "code": item.code,
                "name": item.name,
                "plan_total": item.plan_total,
                "actual_total": item.actual_total,
                "variance": item.variance,
            }
            for item in tree.all_items()
            if item.variance > 0
        ]
        overruns.sort(key=lambda r: r["variance"], reverse=True)
        self.overrun_table.set_rows(overruns)

        self._fill_activity()

    def _fill_activity(self) -> None:
        while self.activity_box.count():
            item = self.activity_box.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        entries = project_service.project_activity(self.project_id, limit=8)
        if not entries:
            self.activity_box.addWidget(QLabel(tr("no_data")))
            return
        from app.utils.formatting import fmt_datetime
        from app.utils.labels import audit_action_label

        for entry in entries:
            label = QLabel(
                f"<b>{entry['username']}</b> · {audit_action_label(entry['action'])} · "
                f"{entry['description']}<br/>"
                f"<span style='color:{COLORS.text_faint}'>{fmt_datetime(entry['ts'])}</span>"
            )
            label.setWordWrap(True)
            self.activity_box.addWidget(label)
        self.activity_box.addStretch(1)
