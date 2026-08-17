"""Modal dialogs."""

from app.ui.dialogs.booking_dialog import BookingDialog
from app.ui.dialogs.lead_dialog import LeadDialog, MergeLeadsDialog, StatusChangeDialog
from app.ui.dialogs.login_dialog import LoginDialog
from app.ui.dialogs.misc_dialogs import (
    CallLogDialog,
    KnowledgeDialog,
    PasswordDialog,
    TaskDialog,
    UserDialog,
)

__all__ = [
    "LoginDialog",
    "LeadDialog",
    "StatusChangeDialog",
    "MergeLeadsDialog",
    "BookingDialog",
    "TaskDialog",
    "CallLogDialog",
    "KnowledgeDialog",
    "UserDialog",
    "PasswordDialog",
]
