"""Task, call, knowledge base, user and password dialogs."""

from __future__ import annotations

from datetime import timedelta

from PySide6.QtCore import QDate, QDateTime, Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDateEdit,
    QDateTimeEdit,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QLineEdit,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.models.enums import CallDirection, KBItemType, RoleName, TaskPriority, TaskType
from app.models.intelligence import KnowledgeBaseItem
from app.models.operations import Task
from app.models.organization import User
from app.services import (
    auth_service,
    call_service,
    company_service,
    knowledge_service,
    task_service,
)
from app.services.auth_service import CurrentUser
from app.ui.i18n import tr
from app.ui.widgets.common import combo, set_combo_value, show_error
from app.ui.widgets.labels import (
    kb_type_items,
    language_items,
    outcome_items,
    priority_items,
    role_items,
    task_type_items,
)
from app.utils.dates import now


class TaskDialog(QDialog):
    """Create or edit a follow-up task."""

    def __init__(
        self,
        actor: CurrentUser,
        *,
        task: Task | None = None,
        lead_id: int | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.actor = actor
        self.task_id = task.id if task else None
        self.lead_id = lead_id or (task.lead_id if task else None)
        self.setWindowTitle(tr("tasks.new") if task is None else tr("common.edit"))
        self.setMinimumWidth(460)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.title_input = QLineEdit(task.title if task else "")
        self.type_box = combo(task_type_items(include_all=False))
        self.priority_box = combo(priority_items())
        operators = auth_service.list_operators()
        self.assignee_box = combo(
            [(tr("common.unassigned"), None)] + [(u.full_name, u.id) for u in operators]
        )
        self.due_input = QDateTimeEdit(QDateTime.currentDateTime().addSecs(3600))
        self.due_input.setCalendarPopup(True)
        self.due_input.setDisplayFormat("dd.MM.yyyy HH:mm")
        self.description_input = QTextEdit()
        self.description_input.setMaximumHeight(90)

        if task is not None:
            set_combo_value(self.type_box, task.task_type)
            set_combo_value(self.priority_box, task.priority)
            set_combo_value(self.assignee_box, task.assignee_id)
            if task.due_at:
                self.due_input.setDateTime(QDateTime(task.due_at))
            self.description_input.setPlainText(task.description)
        else:
            set_combo_value(self.type_box, TaskType.CALL_BACK)
            set_combo_value(self.priority_box, TaskPriority.NORMAL)
            set_combo_value(self.assignee_box, actor.id)

        form.addRow(tr("common.title"), self.title_input)
        form.addRow(tr("common.type"), self.type_box)
        form.addRow(tr("common.priority"), self.priority_box)
        form.addRow(tr("tasks.assignee"), self.assignee_box)
        form.addRow(tr("tasks.due"), self.due_input)
        form.addRow(tr("common.description"), self.description_input)
        layout.addLayout(form)

        buttons = QDialogButtonBox()
        save = buttons.addButton(tr("common.save"), QDialogButtonBox.ButtonRole.AcceptRole)
        save.setObjectName("Primary")
        buttons.addButton(tr("common.cancel"), QDialogButtonBox.ButtonRole.RejectRole)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _save(self) -> None:
        """Persist the task."""
        title = self.title_input.text().strip()
        if not title:
            show_error(self, tr("err.kb_title_required"))
            return
        try:
            if self.task_id:
                task_service.update_task(
                    self.task_id,
                    actor=self.actor,
                    title=title,
                    assignee_id=self.assignee_box.currentData(),
                    due_at=self.due_input.dateTime().toPython(),
                    priority=self.priority_box.currentData(),
                    description=self.description_input.toPlainText(),
                )
            else:
                task_service.create_task(
                    title=title,
                    lead_id=self.lead_id,
                    assignee_id=self.assignee_box.currentData(),
                    task_type=self.type_box.currentData(),
                    priority=self.priority_box.currentData(),
                    due_at=self.due_input.dateTime().toPython(),
                    description=self.description_input.toPlainText(),
                    actor=self.actor,
                )
        except Exception as exc:
            code = getattr(exc, "code", None)
            show_error(self, tr(f"err.{code}") if code else tr("err.unknown"))
            return
        self.accept()


class CallLogDialog(QDialog):
    """Register a call that happened outside the system."""

    def __init__(self, actor: CurrentUser, lead_id: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.actor = actor
        self.lead_id = lead_id
        self.setWindowTitle(tr("calls.log"))
        self.setMinimumWidth(440)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.direction_box = combo(
            [
                (tr("calls.outbound"), CallDirection.OUTBOUND),
                (tr("calls.inbound"), CallDirection.INBOUND),
            ]
        )
        self.outcome_box = combo(outcome_items(include_all=False))
        self.duration_input = QSpinBox()
        self.duration_input.setRange(0, 7200)
        self.duration_input.setSuffix(" s")
        self.duration_input.setValue(60)
        self.started_input = QDateTimeEdit(QDateTime.currentDateTime())
        self.started_input.setCalendarPopup(True)
        self.started_input.setDisplayFormat("dd.MM.yyyy HH:mm")
        self.recording_input = QLineEdit()
        self.recording_input.setPlaceholderText("…\\call.mp3")
        self.note_input = QTextEdit()
        self.note_input.setMaximumHeight(80)

        browse = QDialogButtonBox()
        pick = browse.addButton(tr("common.attach"), QDialogButtonBox.ButtonRole.ActionRole)
        pick.setObjectName("Ghost")
        pick.clicked.connect(self._pick_recording)

        form.addRow(tr("calls.direction"), self.direction_box)
        form.addRow(tr("common.result"), self.outcome_box)
        form.addRow(tr("common.duration"), self.duration_input)
        form.addRow(tr("common.date"), self.started_input)
        form.addRow(tr("calls.recording"), self.recording_input)
        form.addRow("", browse)
        form.addRow(tr("common.comment"), self.note_input)
        layout.addLayout(form)

        buttons = QDialogButtonBox()
        save = buttons.addButton(tr("common.save"), QDialogButtonBox.ButtonRole.AcceptRole)
        save.setObjectName("Primary")
        buttons.addButton(tr("common.cancel"), QDialogButtonBox.ButtonRole.RejectRole)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _pick_recording(self) -> None:
        """Choose an audio file."""
        path, _ = QFileDialog.getOpenFileName(
            self, tr("calls.recording"), "", "Audio (*.mp3 *.wav *.ogg *.m4a);;All files (*.*)"
        )
        if path:
            self.recording_input.setText(path)

    def _save(self) -> None:
        """Persist the call."""
        try:
            call_service.log_manual_call(
                lead_id=self.lead_id,
                actor=self.actor,
                direction=self.direction_box.currentData(),
                duration_seconds=self.duration_input.value(),
                outcome=self.outcome_box.currentData(),
                note=self.note_input.toPlainText(),
                started_at=self.started_input.dateTime().toPython(),
                recording_path=self.recording_input.text().strip(),
            )
        except Exception as exc:
            code = getattr(exc, "code", None)
            show_error(self, tr(f"err.{code}") if code else tr("err.unknown"))
            return
        self.accept()


class KnowledgeDialog(QDialog):
    """Create or edit a knowledge base article."""

    def __init__(
        self,
        actor: CurrentUser,
        item: KnowledgeBaseItem | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.actor = actor
        self.item_id = item.id if item else None
        self.setWindowTitle(tr("kb.new") if item is None else tr("common.edit"))
        self.setMinimumSize(600, 560)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.type_box = combo(kb_type_items(include_all=False))
        self.title_input = QLineEdit(item.title if item else "")
        self.title_ru_input = QLineEdit(item.title_ru if item else "")
        self.category_input = QLineEdit(item.category if item else "")
        self.keywords_input = QLineEdit(item.keywords if item else "")
        self.tags_input = QLineEdit(item.tags if item else "")
        self.body_input = QTextEdit(item.body if item else "")
        self.body_input.setMinimumHeight(110)
        self.body_ru_input = QTextEdit(item.body_ru if item else "")
        self.body_ru_input.setMinimumHeight(90)
        self.price_input = QDoubleSpinBox()
        self.price_input.setRange(0, 10_000_000_000)
        self.price_input.setGroupSeparatorShown(True)
        self.price_input.setValue(float(item.price or 0) if item else 0.0)
        self.priority_input = QSpinBox()
        self.priority_input.setRange(0, 10)
        self.priority_input.setValue(item.priority if item else 0)
        self.valid_from = QDateEdit(QDate.currentDate())
        self.valid_from.setCalendarPopup(True)
        self.valid_from.setDisplayFormat("dd.MM.yyyy")
        self.valid_from.setSpecialValueText("—")
        self.valid_to = QDateEdit(QDate.currentDate().addDays(30))
        self.valid_to.setCalendarPopup(True)
        self.valid_to.setDisplayFormat("dd.MM.yyyy")
        self.use_validity = QCheckBox(tr("kb.valid_from") + " / " + tr("kb.valid_to"))
        self.ai_usable = QCheckBox(tr("kb.ai_usable"))
        self.ai_usable.setChecked(item.ai_usable if item else True)

        services = company_service.list_services()
        self.service_box = combo([("—", None)] + [(s.name, s.id) for s in services])
        branches = company_service.list_branches()
        self.branch_box = combo([("—", None)] + [(b.name, b.id) for b in branches])

        if item is not None:
            set_combo_value(self.type_box, item.item_type)
            set_combo_value(self.service_box, item.service_id)
            set_combo_value(self.branch_box, item.branch_id)
            if item.valid_from:
                self.use_validity.setChecked(True)
                self.valid_from.setDate(QDate(item.valid_from))
            if item.valid_to:
                self.valid_to.setDate(QDate(item.valid_to))
        else:
            set_combo_value(self.type_box, KBItemType.FAQ)

        form.addRow(tr("common.type"), self.type_box)
        form.addRow(tr("common.title"), self.title_input)
        form.addRow(tr("common.title") + " (RU)", self.title_ru_input)
        form.addRow(tr("common.category"), self.category_input)
        form.addRow(tr("kb.body"), self.body_input)
        form.addRow(tr("kb.body_ru"), self.body_ru_input)
        form.addRow(tr("kb.keywords"), self.keywords_input)
        form.addRow(tr("common.tags"), self.tags_input)
        form.addRow(tr("common.price"), self.price_input)
        form.addRow(tr("common.service"), self.service_box)
        form.addRow(tr("common.branch"), self.branch_box)
        form.addRow(tr("common.priority"), self.priority_input)
        form.addRow("", self.use_validity)
        form.addRow(tr("kb.valid_from"), self.valid_from)
        form.addRow(tr("kb.valid_to"), self.valid_to)
        form.addRow("", self.ai_usable)
        layout.addLayout(form)

        buttons = QDialogButtonBox()
        save = buttons.addButton(tr("common.save"), QDialogButtonBox.ButtonRole.AcceptRole)
        save.setObjectName("Primary")
        buttons.addButton(tr("common.cancel"), QDialogButtonBox.ButtonRole.RejectRole)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _save(self) -> None:
        """Persist the knowledge base article."""
        try:
            knowledge_service.save_item(
                actor=self.actor,
                item_id=self.item_id,
                company_id=self.actor.company_id,
                item_type=self.type_box.currentData(),
                category=self.category_input.text(),
                title=self.title_input.text(),
                title_ru=self.title_ru_input.text(),
                body=self.body_input.toPlainText(),
                body_ru=self.body_ru_input.toPlainText(),
                keywords=self.keywords_input.text(),
                tags=self.tags_input.text(),
                service_id=self.service_box.currentData(),
                branch_id=self.branch_box.currentData(),
                price=self.price_input.value() or None,
                valid_from=(
                    self.valid_from.date().toPython() if self.use_validity.isChecked() else None
                ),
                valid_to=self.valid_to.date().toPython() if self.use_validity.isChecked() else None,
                ai_usable=self.ai_usable.isChecked(),
                priority=self.priority_input.value(),
            )
        except Exception as exc:
            code = getattr(exc, "code", None)
            show_error(self, tr(f"err.{code}") if code else tr("err.unknown"))
            return
        self.accept()


class UserDialog(QDialog):
    """Create or edit an application user."""

    def __init__(self, actor: CurrentUser, user: User | None = None, parent: QWidget | None = None):
        super().__init__(parent)
        self.actor = actor
        self.user_id = user.id if user else None
        self.setWindowTitle(tr("set.users"))
        self.setMinimumWidth(440)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.username_input = QLineEdit(user.username if user else "")
        self.username_input.setEnabled(user is None)
        self.full_name_input = QLineEdit(user.full_name if user else "")
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("—" if user else "")
        self.email_input = QLineEdit(user.email if user else "")
        self.phone_input = QLineEdit(user.phone if user else "")
        self.role_box = combo(role_items())
        self.language_box = combo(language_items(include_unknown=False))
        branches = company_service.list_branches()
        self.branch_box = combo([("—", None)] + [(b.name, b.id) for b in branches])
        self.active_box = QCheckBox(tr("common.active"))
        self.active_box.setChecked(user.is_active if user else True)

        if user is not None:
            set_combo_value(self.role_box, user.role.name)
            set_combo_value(self.language_box, user.language)
            set_combo_value(self.branch_box, user.branch_id)
        else:
            set_combo_value(self.role_box, RoleName.OPERATOR)

        form.addRow(tr("login.username"), self.username_input)
        form.addRow(tr("login.full_name"), self.full_name_input)
        form.addRow(tr("login.password"), self.password_input)
        form.addRow(tr("common.email"), self.email_input)
        form.addRow(tr("common.phone"), self.phone_input)
        form.addRow(tr("common.role"), self.role_box)
        form.addRow(tr("common.language"), self.language_box)
        form.addRow(tr("common.branch"), self.branch_box)
        form.addRow("", self.active_box)
        layout.addLayout(form)

        buttons = QDialogButtonBox()
        save = buttons.addButton(tr("common.save"), QDialogButtonBox.ButtonRole.AcceptRole)
        save.setObjectName("Primary")
        buttons.addButton(tr("common.cancel"), QDialogButtonBox.ButtonRole.RejectRole)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _save(self) -> None:
        """Create or update the user."""
        try:
            if self.user_id:
                auth_service.update_user(
                    self.user_id,
                    actor=self.actor,
                    full_name=self.full_name_input.text(),
                    role_name=self.role_box.currentData(),
                    email=self.email_input.text(),
                    phone=self.phone_input.text(),
                    language=self.language_box.currentData(),
                    branch_id=self.branch_box.currentData(),
                    is_active=self.active_box.isChecked(),
                    is_operator=self.role_box.currentData() == RoleName.OPERATOR,
                )
                if self.password_input.text():
                    auth_service.change_password(
                        self.user_id, self.password_input.text(), actor=self.actor
                    )
            else:
                auth_service.create_user(
                    username=self.username_input.text(),
                    password=self.password_input.text(),
                    full_name=self.full_name_input.text(),
                    role_name=self.role_box.currentData(),
                    company_id=self.actor.company_id,
                    email=self.email_input.text(),
                    phone=self.phone_input.text(),
                    language=self.language_box.currentData(),
                    branch_id=self.branch_box.currentData(),
                    actor=self.actor,
                )
        except Exception as exc:
            code = getattr(exc, "code", None)
            show_error(self, tr(f"err.{code}") if code else tr("err.unknown"))
            return
        self.accept()


class PasswordDialog(QDialog):
    """Change the password of the signed-in user."""

    def __init__(self, actor: CurrentUser, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.actor = actor
        self.setWindowTitle(tr("topbar.change_password"))
        self.setMinimumWidth(380)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)
        form = QFormLayout()
        self.new_input = QLineEdit()
        self.new_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.repeat_input = QLineEdit()
        self.repeat_input.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow(tr("login.password"), self.new_input)
        form.addRow(tr("login.password_repeat"), self.repeat_input)
        layout.addLayout(form)

        buttons = QDialogButtonBox()
        save = buttons.addButton(tr("common.save"), QDialogButtonBox.ButtonRole.AcceptRole)
        save.setObjectName("Primary")
        buttons.addButton(tr("common.cancel"), QDialogButtonBox.ButtonRole.RejectRole)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _save(self) -> None:
        """Apply the new password."""
        if self.new_input.text() != self.repeat_input.text():
            show_error(self, tr("err.password_mismatch"))
            return
        try:
            auth_service.change_password(self.actor.id, self.new_input.text(), actor=self.actor)
        except Exception as exc:
            code = getattr(exc, "code", None)
            show_error(self, tr(f"err.{code}") if code else tr("err.unknown"))
            return
        self.accept()


def next_hour() -> QDateTime:
    """Helper returning the next round hour as ``QDateTime``."""
    reference = now() + timedelta(hours=1)
    return QDateTime(reference.replace(minute=0, second=0, microsecond=0))
