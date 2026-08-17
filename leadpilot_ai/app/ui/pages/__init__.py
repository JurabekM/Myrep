"""Workspace pages."""

from app.ui.pages.ai_page import AIPage
from app.ui.pages.audit_page import AuditPage
from app.ui.pages.base_page import BasePage
from app.ui.pages.bookings_page import BookingsPage
from app.ui.pages.calls_page import CallsPage
from app.ui.pages.inbox_page import InboxPage
from app.ui.pages.knowledge_page import KnowledgePage
from app.ui.pages.leads_page import LeadsPage
from app.ui.pages.marketing_page import MarketingPage
from app.ui.pages.operators_page import OperatorsPage
from app.ui.pages.reports_page import ReportsPage
from app.ui.pages.settings_page import SettingsPage
from app.ui.pages.tasks_page import TasksPage

__all__ = [
    "BasePage",
    "InboxPage",
    "LeadsPage",
    "BookingsPage",
    "CallsPage",
    "TasksPage",
    "KnowledgePage",
    "AIPage",
    "MarketingPage",
    "OperatorsPage",
    "ReportsPage",
    "AuditPage",
    "SettingsPage",
]
