"""Settings tab configuring replication between installations."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QSpinBox,
    QWidget,
)

from app.config import SYNC_DEFAULT_INTERVAL, SYNC_MIN_INTERVAL
from app.controllers.app_state import app_state
from app.services.permissions import Perm
from app.sync import engine as sync_engine
from app.sync.transports import SETUP_SQL, TRANSPORT_LABELS, build_transport
from app.sync.transports.base import TransportError
from app.sync.transports.mqtt import DEFAULT_HOST as MQTT_DEFAULT_HOST
from app.sync.transports.mqtt import DEFAULT_PORT as MQTT_DEFAULT_PORT
from app.sync.transports.mqtt import DEFAULT_PREFIX as MQTT_DEFAULT_PREFIX
from app.sync.transports.mqtt import PUBLIC_BROKERS
from app.ui.dialogs.base_dialog import confirm, show_error, show_info
from app.ui.pages.base_page import BasePage
from app.ui.styles.theme import COLORS, SPACING_SM
from app.ui.widgets.common import Card, button, field_label
from app.utils.formatting import fmt_datetime
from app.utils.i18n import tr


class SyncTab(BasePage):
    """Configure the backend, watch the status, trigger a manual round."""

    def __init__(self, controller=None, parent: QWidget | None = None) -> None:
        super().__init__(tr("sync"), "", parent, show_header=False, compact=True)
        self.controller = controller

        intro = QLabel(tr("sync_intro"))
        intro.setObjectName("Hint")
        intro.setWordWrap(True)
        self.root.addWidget(intro)

        body = QHBoxLayout()
        body.setSpacing(SPACING_SM * 2)
        body.addWidget(self._build_settings_card(), 3)
        body.addWidget(self._build_status_card(), 2)
        self.root.addLayout(body)
        self.root.addWidget(self._build_help_card(), 1)

        self._load()
        self._toggle_fields()
        if self.controller is not None:
            self.controller.started.connect(self._on_started)
            self.controller.finished.connect(self._on_finished)

    # -- construction --------------------------------------------------------- #
    def _build_settings_card(self) -> QWidget:
        card = Card(tr("sync"))
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        form.setSpacing(SPACING_SM)

        self.backend_box = QComboBox()
        for key in ("off", "mqtt", "supabase", "folder"):
            self.backend_box.addItem(TRANSPORT_LABELS[key], key)
        self.backend_box.currentIndexChanged.connect(self._toggle_fields)
        form.addRow(field_label(tr("sync_backend")), self.backend_box)

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://xxxxxxxx.supabase.co")
        form.addRow(field_label(tr("sync_url")), self.url_input)

        self.key_input = QLineEdit()
        self.key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.key_input.setPlaceholderText("eyJhbGciOi...")
        form.addRow(field_label(tr("sync_api_key")), self.key_input)

        self.broker_box = QComboBox()
        for host, port, label in PUBLIC_BROKERS:
            self.broker_box.addItem(label, (host, port))
        self.broker_box.addItem(tr("mqtt_custom"), None)
        self.broker_box.currentIndexChanged.connect(self._on_broker_changed)
        form.addRow(field_label(tr("mqtt_broker")), self.broker_box)

        host_row = QWidget()
        host_layout = QHBoxLayout(host_row)
        host_layout.setContentsMargins(0, 0, 0, 0)
        host_layout.setSpacing(SPACING_SM)
        self.mqtt_host_input = QLineEdit()
        self.mqtt_host_input.setPlaceholderText(MQTT_DEFAULT_HOST)
        host_layout.addWidget(self.mqtt_host_input, 3)
        self.mqtt_port_box = QSpinBox()
        self.mqtt_port_box.setRange(1, 65535)
        self.mqtt_port_box.setValue(MQTT_DEFAULT_PORT)
        host_layout.addWidget(self.mqtt_port_box, 1)
        self.mqtt_host_row = host_row
        form.addRow(field_label(tr("mqtt_host")), host_row)

        self.mqtt_tls_box = QCheckBox(tr("mqtt_tls"))
        self.mqtt_tls_box.setChecked(True)
        form.addRow("", self.mqtt_tls_box)

        self.mqtt_user_input = QLineEdit()
        form.addRow(field_label(tr("mqtt_user")), self.mqtt_user_input)
        self.mqtt_password_input = QLineEdit()
        self.mqtt_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow(field_label(tr("mqtt_password")), self.mqtt_password_input)
        self.mqtt_prefix_input = QLineEdit()
        self.mqtt_prefix_input.setPlaceholderText(MQTT_DEFAULT_PREFIX)
        form.addRow(field_label(tr("mqtt_prefix")), self.mqtt_prefix_input)

        folder_row = QWidget()
        folder_layout = QHBoxLayout(folder_row)
        folder_layout.setContentsMargins(0, 0, 0, 0)
        folder_layout.setSpacing(SPACING_SM)
        self.folder_input = QLineEdit()
        self.folder_input.setPlaceholderText(r"\\server\buildcontrol")
        folder_layout.addWidget(self.folder_input, 1)
        browse = button(tr("browse"), "attach")
        browse.clicked.connect(self._pick_folder)
        folder_layout.addWidget(browse)
        self.folder_row = folder_row
        form.addRow(field_label(tr("sync_folder")), folder_row)

        self.tenant_input = QLineEdit()
        self.tenant_input.setToolTip(tr("sync_tenant_hint"))
        form.addRow(field_label(tr("sync_tenant")), self.tenant_input)

        self.passphrase_input = QLineEdit()
        self.passphrase_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.passphrase_input.setToolTip(tr("sync_passphrase_hint"))
        form.addRow(field_label(tr("sync_passphrase")), self.passphrase_input)

        self.device_input = QLineEdit()
        form.addRow(field_label(tr("sync_device_name")), self.device_input)

        self.auto_box = QCheckBox(tr("sync_auto"))
        form.addRow("", self.auto_box)

        self.interval_box = QSpinBox()
        self.interval_box.setRange(SYNC_MIN_INTERVAL, 3600)
        self.interval_box.setValue(SYNC_DEFAULT_INTERVAL)
        self.interval_box.setSuffix(" s")
        form.addRow(field_label(tr("sync_interval")), self.interval_box)

        card.body().addLayout(form)

        buttons = QHBoxLayout()
        buttons.setSpacing(SPACING_SM)
        self.save_btn = button(tr("save"), "save", "Primary")
        self.save_btn.clicked.connect(self._save)
        self.test_btn = button(tr("sync_test"), "refresh")
        self.test_btn.clicked.connect(self._test)
        buttons.addWidget(self.save_btn)
        buttons.addWidget(self.test_btn)
        buttons.addStretch(1)
        card.body().addLayout(buttons)
        return card

    def _build_status_card(self) -> QWidget:
        card = Card(tr("sync_status"))
        grid = QGridLayout()
        grid.setVerticalSpacing(6)
        grid.setHorizontalSpacing(14)
        self.status_labels: dict[str, QLabel] = {}
        rows = [
            ("state", tr("sync_status")),
            ("pending", tr("sync_pending")),
            ("last_push", tr("sync_last_push")),
            ("last_pull", tr("sync_last_pull")),
            ("cursor", tr("sync_cursor")),
            ("totals", tr("sync_totals")),
            ("device", tr("sync_device_id")),
        ]
        for index, (key, caption) in enumerate(rows):
            grid.addWidget(field_label(caption), index, 0)
            value = QLabel("—")
            value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            grid.addWidget(value, index, 1)
            self.status_labels[key] = value
        grid.setColumnStretch(1, 1)
        card.body().addLayout(grid)

        self.warning_label = QLabel(tr("mqtt_warning"))
        self.warning_label.setWordWrap(True)
        self.warning_label.setStyleSheet(f"color: {COLORS.warning};")
        self.warning_label.setVisible(False)
        card.body().addWidget(self.warning_label)

        self.error_label = QLabel("")
        self.error_label.setObjectName("FieldError")
        self.error_label.setWordWrap(True)
        card.body().addWidget(self.error_label)

        actions = QHBoxLayout()
        actions.setSpacing(SPACING_SM)
        self.sync_btn = button(tr("sync_now"), "refresh", "Primary")
        self.sync_btn.clicked.connect(self._sync_now)
        self.upload_btn = button(tr("sync_upload_all"), "up")
        self.upload_btn.clicked.connect(self._upload_all)
        self.replay_btn = button(tr("sync_reset_cursor"), "down", "Ghost")
        self.replay_btn.clicked.connect(self._replay)
        for widget in (self.sync_btn, self.upload_btn, self.replay_btn):
            actions.addWidget(widget)
        actions.addStretch(1)
        card.body().addLayout(actions)
        card.body().addStretch(1)
        return card

    def _build_help_card(self) -> QWidget:
        card = Card(tr("sync_setup_title"))
        self.help_label = QLabel(tr("sync_setup_steps"))
        self.help_label.setObjectName("Hint")
        self.help_label.setWordWrap(True)
        card.body().addWidget(self.help_label)

        self.sql_view = QPlainTextEdit(SETUP_SQL.strip())
        self.sql_view.setReadOnly(True)
        self.sql_view.setMinimumHeight(150)
        self.sql_view.setStyleSheet(
            f"font-family: Consolas, monospace; color: {COLORS.text_muted};"
        )
        card.body().addWidget(self.sql_view, 1)

        copy_btn = button(tr("copy_sql"), "copy")
        copy_btn.clicked.connect(self._copy_sql)
        row = QHBoxLayout()
        row.addWidget(copy_btn)
        row.addStretch(1)
        card.body().addLayout(row)
        return card

    # -- data ----------------------------------------------------------------- #
    def _load(self) -> None:
        settings = app_state.sync_settings
        index = self.backend_box.findData(settings["backend"])
        self.backend_box.setCurrentIndex(max(0, index))
        self.url_input.setText(settings["url"])
        self.key_input.setText(settings["api_key"])
        self.folder_input.setText(settings["folder"])
        self.mqtt_host_input.setText(settings["mqtt_host"])
        self.mqtt_port_box.setValue(int(settings["mqtt_port"]))
        self.mqtt_tls_box.setChecked(bool(settings["mqtt_tls"]))
        self.mqtt_user_input.setText(settings["mqtt_user"])
        self.mqtt_password_input.setText(settings["mqtt_password"])
        self.mqtt_prefix_input.setText(settings["mqtt_prefix"])
        self.passphrase_input.setText(settings["passphrase"])
        known = [(host, port) for host, port, _ in PUBLIC_BROKERS]
        pair = (settings["mqtt_host"], int(settings["mqtt_port"]))
        self.broker_box.blockSignals(True)
        self.broker_box.setCurrentIndex(
            known.index(pair) if pair in known else self.broker_box.count() - 1
        )
        self.broker_box.blockSignals(False)
        self.tenant_input.setText(settings["tenant"])
        self.device_input.setText(settings["device_name"])
        self.auto_box.setChecked(bool(settings["auto"]))
        self.interval_box.setValue(int(settings["interval"]))

    def _values(self) -> dict:
        return {
            "backend": str(self.backend_box.currentData()),
            "url": self.url_input.text().strip(),
            "api_key": self.key_input.text().strip(),
            "folder": self.folder_input.text().strip(),
            "tenant": self.tenant_input.text().strip() or "buildcontrol",
            "device_name": self.device_input.text().strip(),
            "auto": self.auto_box.isChecked(),
            "interval": self.interval_box.value(),
            "mqtt_host": self.mqtt_host_input.text().strip() or MQTT_DEFAULT_HOST,
            "mqtt_port": self.mqtt_port_box.value(),
            "mqtt_tls": self.mqtt_tls_box.isChecked(),
            "mqtt_user": self.mqtt_user_input.text().strip(),
            "mqtt_password": self.mqtt_password_input.text(),
            "mqtt_prefix": self.mqtt_prefix_input.text().strip() or MQTT_DEFAULT_PREFIX,
            "passphrase": self.passphrase_input.text(),
        }

    def refresh(self) -> None:
        """Refresh the status panel."""
        try:
            state = sync_engine.status()
        except Exception as exc:  # pragma: no cover - defensive
            self.error_label.setText(str(exc))
            return
        settings = app_state.sync_settings
        backend = settings["backend"]
        running = self.controller is not None and self.controller.busy
        if running:
            label, color = tr("sync_running"), COLORS.warning
        elif backend in ("", "off"):
            label, color = tr("sync_disabled"), COLORS.text_muted
        elif state["last_error"]:
            label, color = tr("sync_failed"), COLORS.danger
        else:
            label, color = TRANSPORT_LABELS.get(backend, backend), COLORS.success
        self.status_labels["state"].setText(label)
        self.status_labels["state"].setStyleSheet(f"color: {color}; font-weight: 600;")
        pending = state["pending"]
        self.status_labels["pending"].setText(str(pending))
        self.status_labels["pending"].setStyleSheet(
            f"color: {COLORS.warning if pending else COLORS.text};"
        )
        self.status_labels["last_push"].setText(
            fmt_datetime(state["last_push_at"]) if state["last_push_at"] else tr("sync_never")
        )
        self.status_labels["last_pull"].setText(
            fmt_datetime(state["last_pull_at"]) if state["last_pull_at"] else tr("sync_never")
        )
        self.status_labels["cursor"].setText(state["cursor"] or "—")
        self.status_labels["totals"].setText(f"↑{state['pushed_total']}  ↓{state['pulled_total']}")
        self.status_labels["device"].setText(
            f"{state['device_name'] or '—'}  ·  {state['device_id']}"
        )
        self.error_label.setText(state["last_error"])
        self.error_label.setVisible(bool(state["last_error"]))
        self.sync_btn.setEnabled(backend not in ("", "off") and not running)

    # -- actions -------------------------------------------------------------- #
    def _on_broker_changed(self) -> None:
        """Fill host and port from the selected public broker."""
        chosen = self.broker_box.currentData()
        manual = chosen is None
        self.mqtt_host_row.setEnabled(manual)
        if not manual:
            host, port = chosen
            self.mqtt_host_input.setText(host)
            self.mqtt_port_box.setValue(port)
            self.mqtt_tls_box.setChecked(port in (8883, 8886))

    def _toggle_fields(self) -> None:
        backend = str(self.backend_box.currentData())
        for widget in (self.url_input, self.key_input):
            widget.setEnabled(backend == "supabase")
        self.folder_row.setEnabled(backend == "folder")
        is_mqtt = backend == "mqtt"
        for widget in (
            self.broker_box,
            self.mqtt_tls_box,
            self.mqtt_user_input,
            self.mqtt_password_input,
            self.mqtt_prefix_input,
        ):
            widget.setEnabled(is_mqtt)
        self.mqtt_host_row.setEnabled(is_mqtt and self.broker_box.currentData() is None)
        self.passphrase_input.setEnabled(backend != "off")
        self.warning_label.setVisible(is_mqtt)
        self.sql_view.setVisible(backend == "supabase")
        self.help_label.setText(tr("mqtt_setup_steps") if is_mqtt else tr("sync_setup_steps"))
        enabled = backend != "off"
        self.tenant_input.setEnabled(enabled)
        self.auto_box.setEnabled(enabled)
        self.interval_box.setEnabled(enabled)
        self.test_btn.setEnabled(enabled)

    def _pick_folder(self) -> None:
        path = QFileDialog.getExistingDirectory(self, tr("sync_folder"))
        if path:
            self.folder_input.setText(path)

    def _save(self) -> None:
        if not self.can(Perm.SETTINGS_MANAGE):
            show_error(self, tr("permission_denied"))
            return
        values = self._values()
        app_state.save_sync_settings(values)
        sync_engine.set_device_name(values["device_name"])
        if self.controller is not None:
            self.controller.apply_schedule()
        self.notify(tr("saved"))
        self.refresh()

    def _test(self) -> None:
        try:
            transport = build_transport(self._values())
            if transport is None:
                show_info(self, tr("sync_disabled"))
                return
            message = transport.check()
        except TransportError as exc:
            show_error(self, str(exc))
            return
        except Exception as exc:
            show_error(self, str(exc))
            return
        show_info(self, f"{transport.describe()}\n\n{message}")

    def _sync_now(self) -> None:
        if self.controller is None:
            return
        if not self.controller.sync_now():
            self.notify(tr("sync_running"), "warning")
        self.refresh()

    def _upload_all(self) -> None:
        if not self.can(Perm.SETTINGS_MANAGE):
            show_error(self, tr("permission_denied"))
            return
        if not confirm(self, tr("sync_upload_all_q"), tr("sync_upload_all")):
            return
        queued = sync_engine.queue_full_upload()
        self.notify(f"{tr('sync_pending')}: {queued}")
        self.refresh()

    def _replay(self) -> None:
        if not confirm(self, tr("sync_reset_q"), tr("sync_reset_cursor")):
            return
        sync_engine.reset_cursor()
        self.notify(tr("saved"))
        self.refresh()

    def _copy_sql(self) -> None:
        from PySide6.QtWidgets import QApplication

        QApplication.clipboard().setText(SETUP_SQL.strip())
        self.notify(tr("copied"))

    # -- controller signals ---------------------------------------------------- #
    def _on_started(self) -> None:
        self.refresh()

    def _on_finished(self, report) -> None:
        self.refresh()
        if report.errors:
            self.notify(f"{tr('sync_failed')}: {report.errors[0]}", "danger")
        else:
            self.notify(f"{tr('sync_ok')} · {report.summary()}")
