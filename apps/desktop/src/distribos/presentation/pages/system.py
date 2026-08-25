"""Tizim sahifalari — sinxronizatsiya, konflikt, xavfsizlik, zaxira, audit."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import Slot
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from distribos.app_context import AppContext
from distribos.application import queries
from distribos.i18n import LOCALE_NAMES, SUPPORTED_LOCALES, current_locale, tr
from distribos.i18n import prefs as language_prefs
from distribos.presentation.pages.base import BasePage
from distribos.presentation.status import (
    device_platform,
    rejection_status,
    role_name,
)
from distribos.presentation.theme import PALETTE, SPACE_MD

if TYPE_CHECKING:
    from PySide6.QtWidgets import QLabel as QLabelType

    from distribos.aether_q.onboarding import Invitation

from distribos.presentation.widgets import (
    Card,
    DataTable,
    WarningBanner,
    danger_button,
    ghost_button,
    primary_button,
)

logger = logging.getLogger(__name__)


class SyncPage(BasePage):
    """Sinxronizatsiya markazi — dashboard EMAS, texnik xizmat oynasi."""

    live = True

    def __init__(self, context: AppContext) -> None:
        super().__init__(
            context, "Sinxronizatsiya",
            "Qurilmalar, navbat va xatolar. Bu sahifa texnik xizmat uchun.",
        )
        self._sync_now = primary_button("Hozir sinxronlash")
        self._sync_now.clicked.connect(self._on_sync_now)
        self.header.add_action(self._sync_now)

        self._retry = ghost_button("Xatolarni qayta urinish")
        self._retry.clicked.connect(self._on_retry)
        self.header.add_action(self._retry)

        if context.settings.mqtt.is_public_pilot:
            self.add(WarningBanner(
                "Ochiq (public) MQTT brokeri ishlatilmoqda. Xabar mazmuni "
                "AETHER-Q bilan himoyalangan, biroq brokerning mavjudligi, "
                "metama'lumotlar maxfiyligi va xabarlarning saqlanishi "
                "kafolatlanmaydi. Haqiqiy mijoz ma'lumotlari bilan ishlash "
                "uchun Sozlamalar bo'limidan xususiy broker ko'rsating."
            ))

        cards = QWidget()
        grid = QGridLayout(cards)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(SPACE_MD)
        self._card_queue = Card("Navbatdagi yozuvlar", "0")
        self._card_devices = Card("Ulangan qurilmalar", "0")
        self._card_conflicts = Card("Tekshiruv talab qiladi", "0")
        self._card_errors = Card("Qabul qilinmagan", "0")
        for column, card in enumerate(
            (self._card_queue, self._card_devices, self._card_conflicts, self._card_errors)
        ):
            grid.addWidget(card, 0, column)
        self.add(cards)

        tabs = QTabWidget()
        self.devices_table = DataTable(
            ["Nomi", "Turi", "Rol", "Holat", "Oxirgi aloqa", "Qabul qilingan"],
            searchable=False,
        )
        self.outbox_table = DataTable(
            ["Vaqt", "Amal", "Holat", "Urinishlar", "Xato"], searchable=False
        )
        self.dead_table = DataTable(
            ["Vaqt", "Kanal", "Sabab", "Tafsilot", "Hajm"], searchable=False
        )
        tabs.addTab(self.devices_table, "Qurilmalar")
        tabs.addTab(self.outbox_table, "Navbat")
        tabs.addTab(self.dead_table, "Qabul qilinmaganlar")
        self.add(tabs, 1)

    def refresh(self) -> None:
        from distribos.presentation.status import delivery_status

        with self.context.database.session() as session:
            summary = queries.sync_summary(session)
            devices = queries.list_devices(session)
            outbox = queries.list_outbox(session)
            dead = queries.list_dead_letters(session)

        self._card_queue.set_value(str(summary.queued))
        self._card_queue.set_tone("progress" if summary.queued else "ok")
        self._card_devices.set_value(str(summary.devices_active))
        self._card_conflicts.set_value(str(summary.open_conflicts))
        self._card_conflicts.set_tone("warning" if summary.open_conflicts else "ok")
        self._card_errors.set_value(str(summary.dead_letters))
        self._card_errors.set_tone("error" if summary.dead_letters else "ok")

        self.devices_table.set_rows([
            (device.display_name, device_platform(device.platform),
             role_name(device.role),
             {"ACTIVE": "Faol", "INVITED": "Tasdiq kutmoqda",
              "REVOKED": "Bekor qilingan", "SUSPENDED": "To'xtatilgan"}.get(
                  device.state, device.state),
             device.last_seen_at.strftime("%d.%m.%Y %H:%M") if device.last_seen_at else "—",
             device.last_applied_sequence)
            for device in devices
        ])
        for index, device in enumerate(devices):
            if device.state == "REVOKED":
                self.devices_table.set_row_tone(index, "error")
            elif device.state == "INVITED":
                self.devices_table.set_row_tone(index, "warning")

        self.outbox_table.set_rows([
            (created.strftime("%d.%m.%Y %H:%M"), event_type,
             delivery_status(state).text, attempts, error or "")
            for created, event_type, state, attempts, error in outbox
        ])

        self.dead_table.set_rows([
            (occurred.strftime("%d.%m.%Y %H:%M"), channel,
             rejection_status(reason).text, detail or "", size)
            for occurred, channel, reason, detail, size in dead
        ])

        self.header.set_subtitle(
            f"Jami {summary.total_events} ta yozuv · "
            f"{summary.unapplied_events} tasi qo'llanmagan"
        )

    @Slot()
    def _on_sync_now(self) -> None:
        try:
            published, _, queued, _ = self.context.run_sync_cycle()
        except Exception as exc:
            self.report_error(exc, "Sinxronizatsiya")
            return
        self.refresh()
        self.notify(
            f"{published} ta yozuv yuborildi. Navbatda {queued} ta qoldi.",
            "Sinxronizatsiya",
        )

    @Slot()
    def _on_retry(self) -> None:
        """Dead-letter'dagi yozuvlarni qayta navbatga qo'yadi."""
        from distribos.persistence.models import DeadLetter, DeliveryState, OutboxEntry

        with self.context.database.unit_of_work() as session:
            entries = session.query(OutboxEntry).filter_by(
                state=DeliveryState.DEAD_LETTER
            ).all()
            for entry in entries:
                entry.state = DeliveryState.LOCAL_COMMITTED
                entry.attempts = 0
                entry.next_attempt_at = None
                entry.last_error = None
            count = len(entries)

            from distribos.persistence.models import utcnow

            session.query(DeadLetter).filter(
                DeadLetter.resolved_at.is_(None)
            ).update({DeadLetter.resolved_at: utcnow()})

        self.refresh()
        self.notify(f"{count} ta yozuv qayta navbatga qo'yildi.", "Qayta urinish")


class ConflictsPage(BasePage):
    """Tekshiruv navbati — avtomatik hal qilinmagan zid holatlar."""

    live = True

    def __init__(self, context: AppContext) -> None:
        super().__init__(
            context, "Tekshiruv navbati",
            "Ikki qurilmada zid o'zgarish bo'lganda, qaysi biri to'g'ri "
            "ekanini siz hal qilasiz.",
        )
        self._resolve = primary_button("Ko'rib chiqildi deb belgilash")
        self._resolve.clicked.connect(self._on_resolve)
        self.header.add_action(self._resolve)

        self.table = DataTable(
            ["Vaqt", "Nima", "Qaysi yozuv", "Sabab", "Bizda", "Kelgan"],
            searchable=False,
        )
        self.add(self.table, 1)

        self._empty_note = QLabel(
            "Hozircha tekshiruv talab qiladigan holat yo'q — hamma "
            "o'zgarishlar avtomatik hal qilindi."
        )
        self._empty_note.setStyleSheet(f"color: {PALETTE.text_muted};")
        self.add(self._empty_note)

    def refresh(self) -> None:
        with self.context.database.session() as session:
            conflicts = queries.list_conflicts(session)

        self.table.set_rows([
            (row.detected_at.strftime("%d.%m.%Y %H:%M"), row.aggregate_type,
             row.aggregate_id[:12], row.resolution or row.strategy,
             row.local_value or "—", row.remote_value or "—")
            for row in conflicts
        ])
        for index in range(len(conflicts)):
            self.table.set_row_tone(index, "warning")

        self._empty_note.setVisible(not conflicts)
        self.table.setVisible(bool(conflicts))
        self.header.set_subtitle(
            f"{len(conflicts)} ta holat kutmoqda" if conflicts else "Hammasi tartibda"
        )

    @Slot()
    def _on_resolve(self) -> None:
        selected = self.table.selected_row()
        if selected is None:
            self.warn("Avval jadvaldan holatni tanlang.")
            return
        if not self.confirm(
            "Bu holat ko'rib chiqilgan deb belgilansinmi?\n\n"
            "Yozuvning o'zi o'zgarmaydi — faqat navbatdan chiqadi.",
        ):
            return

        from distribos.persistence.models import ConflictRecord, utcnow

        with self.context.database.unit_of_work() as session:
            record = session.query(ConflictRecord).filter_by(
                status="NEEDS_REVIEW"
            ).order_by(ConflictRecord.detected_at.desc()).first()
            if record is not None:
                record.status = "REVIEWED"
                record.resolved_at = utcnow()
                record.resolved_by = "owner"
        self.refresh()


class SecurityPage(BasePage):
    """Xavfsizlik markazi — protokol holati, qurilmalar, kalitlar."""

    def __init__(self, context: AppContext) -> None:
        super().__init__(
            context, "Xavfsizlik",
            "Qurilma kalitlari, protokol holati va qurilmani bekor qilish.",
        )
        self._invite = primary_button("Yangi qurilma qo'shish")
        self._invite.clicked.connect(self._on_invite)
        self.header.add_action(self._invite)

        self._rotate = ghost_button("Kalitlarni yangilash")
        self._rotate.clicked.connect(self._on_rotate)
        self.header.add_action(self._rotate)

        self._confirm = ghost_button("Qurilmani tasdiqlash")
        self._confirm.clicked.connect(self._on_confirm)
        self.header.add_action(self._confirm)

        self._revoke = danger_button("Qurilmani bekor qilish")
        self._revoke.clicked.connect(self._on_revoke)
        self.header.add_action(self._revoke)

        cards = QWidget()
        grid = QGridLayout(cards)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(SPACE_MD)
        self._card_protocol = Card("Xavfsizlik protokoli", "—")
        self._card_epoch = Card("Kalit avlodi", "—")
        self._card_devices = Card("Qurilmalar", "—")
        self._card_ready = Card("Holat", "—")
        for column, card in enumerate(
            (self._card_protocol, self._card_epoch, self._card_devices, self._card_ready)
        ):
            grid.addWidget(card, 0, column)
        self.add(cards)

        self.table = DataTable(
            ["Nomi", "Turi", "Rol", "Holat", "To'liq nusxa"], searchable=False
        )
        self.add(self.table, 1)

        self._notes = QLabel()
        self._notes.setWordWrap(True)
        self._notes.setStyleSheet(f"color: {PALETTE.text_muted};")
        self.add(self._notes)

    def refresh(self) -> None:
        health = self.context.provider.protocol_health_check()

        self._card_protocol.set_value(f"AETHER-Q {health.protocol_version}")
        self._card_epoch.set_value(f"#{health.epoch}")
        self._card_devices.set_value(
            f"{health.peers_known - health.peers_revoked} / {health.peers_known}"
        )
        if health.production_ready:
            self._card_ready.set_value("Sozlangan")
            self._card_ready.set_tone("ok")
        else:
            self._card_ready.set_value("E'tibor talab")
            self._card_ready.set_tone("warning")

        with self.context.database.session() as session:
            devices = queries.list_devices(session)

        self.table.set_rows([
            (device.display_name, device_platform(device.platform),
             role_name(device.role),
             {"ACTIVE": "Faol", "INVITED": "Tasdiq kutmoqda",
              "REVOKED": "Bekor qilingan"}.get(device.state, device.state),
             "Ha" if device.is_full_replica else "Yo'q")
            for device in devices
        ])

        notes = [
            "Har bir yozuv qurilmaning shaxsiy kaliti bilan imzolanadi — "
            "boshqa qurilma uning nomidan yozuv yarata olmaydi.",
            "Bekor qilingan qurilmaning yozuvlari imzosi to'g'ri bo'lsa ham "
            "qabul qilinmaydi.",
        ]
        if health.blocking_reasons:
            notes.append("E'tibor: " + "; ".join(health.blocking_reasons))
        if self.context.settings.mqtt.is_public_pilot:
            notes.append(
                "Bu build ochiq brokerda ishlamoqda va «production-secure» "
                "deb belgilanmaydi."
            )
        self._notes.setText("\n\n".join(notes))

    @Slot()
    def _on_invite(self) -> None:
        dialog = InviteDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        role, name = dialog.values()

        from distribos.domain.ids import opaque_tenant_topic_id

        invitation = self.context.invitations.issue(
            tenant_topic_id=opaque_tenant_topic_id(self.context.tenant_id),
            role=role, display_name=name,
            host_sign_public_key=self.context.provider.export_public_identity().sign_public_key,
            broker_host=self.context.settings.mqtt.host,
            broker_port=self.context.settings.mqtt.port,
            environment=self.context.settings.environment,
        )
        # Ulash xizmati sirni eslab qolishi kerak — usiz kelgan
        # JOIN_REQUEST ni ocholmaydi.
        self.context.provisioning.remember(invitation)   # type: ignore[attr-defined]
        ShowInvitationDialog(self, invitation).exec()
        self.refresh()

    @Slot()
    def _on_confirm(self) -> None:
        """Tasdiq kutayotgan qurilmani faollashtiradi.

        Bu qadam ATAYLAB qo'lda: tarmoqdagi hujumchi taklifni ushlab
        olsa ham, egasi tanimagan qurilma ro'yxatda paydo bo'ladi va
        tasdiqlanmaydi.
        """
        from distribos.sync.provisioning import confirm_pending_device

        selected = self.table.selected_row()
        if selected is None:
            self.warn("Avval jadvaldan qurilmani tanlang.")
            return

        name = selected[0]
        with self.context.database.session() as session:
            devices = [d for d in queries.list_devices(session) if d.display_name == name]
        if not devices:
            self.warn("Qurilma topilmadi.")
            return
        device = devices[0]

        if device.state == "ACTIVE":
            self.notify(f"«{name}» allaqachon faol.", "Tasdiqlash")
            return
        if not self.confirm(
            f"«{name}» ({role_name(device.role)}) qurilmasi tasdiqlansinmi?\n\n"
            "Tasdiqlangandan keyin u ma'lumot yubora va qabul qila boshlaydi.",
            "Qurilmani tasdiqlash",
        ):
            return

        try:
            with self.context.database.unit_of_work() as session:
                confirm_pending_device(session, device.device_id)
        except Exception as exc:
            self.report_error(exc, "Qurilmani tasdiqlash")
            return
        self.refresh()
        self.notify(f"«{name}» faollashtirildi.", "Tasdiqlandi")

    @Slot()
    def _on_rotate(self) -> None:
        if not self.confirm(
            "Xavfsizlik kalitlari yangilansinmi?\n\n"
            "Eski kalitlar o'chirilmaydi — uzoq vaqt ulanmagan qurilmalar "
            "qaytganda ularning eski yozuvlari baribir o'qiladi.",
            "Kalitlarni yangilash",
        ):
            return
        try:
            epoch = self.context.provider.rotate_keys()
        except Exception as exc:
            self.report_error(exc, "Kalitlarni yangilash")
            return
        self.refresh()
        self.notify(f"Yangi kalit avlodi: #{epoch}", "Kalitlar yangilandi")

    @Slot()
    def _on_revoke(self) -> None:
        selected = self.table.selected_row()
        if selected is None:
            self.warn("Avval jadvaldan qurilmani tanlang.")
            return

        name = selected[0]
        with self.context.database.session() as session:
            devices = [d for d in queries.list_devices(session) if d.display_name == name]
        if not devices:
            self.warn("Qurilma topilmadi.")
            return
        device = devices[0]

        if device.device_id == self.context.device_id:
            self.warn("Shu kompyuterni o'zini bekor qilib bo'lmaydi.")
            return
        if not self.confirm(
            f"«{name}» qurilmasi bekor qilinsinmi?\n\n"
            "Undan keyin kelgan barcha yozuvlar rad etiladi. Bu amalni "
            "qaytarish uchun qurilmani qaytadan qo'shish kerak bo'ladi.",
            "Qurilmani bekor qilish",
        ):
            return

        try:
            self.context.provider.revoke_device(device.device_id, "Foydalanuvchi bekor qildi")
        except Exception as exc:
            self.report_error(exc, "Qurilmani bekor qilish")
            return
        self.refresh()


class BackupPage(BasePage):
    """Zaxira nusxa va tiklash."""

    def __init__(self, context: AppContext) -> None:
        super().__init__(
            context, "Zaxira nusxa",
            "Server yo'q — nusxa yagona himoyangiz. Uni tashqi diskda "
            "ham saqlang.",
        )
        self._create = primary_button("Nusxa yaratish")
        self._create.clicked.connect(self._on_create)
        self.header.add_action(self._create)

        self._verify = ghost_button("Nusxani tekshirish")
        self._verify.clicked.connect(self._on_verify)
        self.header.add_action(self._verify)

        self._restore = danger_button("Nusxadan tiklash")
        self._restore.clicked.connect(self._on_restore)
        self.header.add_action(self._restore)

        self.add(WarningBanner(
            "Agar barcha qurilmalar yo'qolsa va tashqi nusxa bo'lmasa, "
            "ma'lumotni tiklash imkoni BO'LMAYDI. MQTT broker ma'lumot "
            "ombori emas."
        ))

        self.table = DataTable(
            ["Yaratilgan", "Fayl", "Hajm", "Dastur versiyasi"], searchable=False
        )
        self.add(self.table, 1)

    def refresh(self) -> None:
        from distribos.infrastructure.backup import list_backups

        backups = list_backups(self.context.settings.paths.backup_dir)
        self.table.set_rows([
            (info.created_at.strftime("%d.%m.%Y %H:%M"), info.path.name,
             info.human_size, info.app_version)
            for info in backups
        ])
        self.header.set_subtitle(
            f"{len(backups)} ta nusxa · {self.context.settings.paths.backup_dir}"
        )

    @Slot()
    def _on_create(self) -> None:
        from distribos.infrastructure.backup import create_backup, default_backup_name

        password = PasswordDialog.ask(
            self, "Nusxa uchun parol",
            "Nusxa shifrlanadi. Parolni yo'qotsangiz, uni ochib bo'lmaydi.",
            confirm=True,
        )
        if password is None:
            return

        target = self.context.settings.paths.backup_dir / default_backup_name()
        try:
            info = create_backup(self.context.database, target, password)
        except Exception as exc:
            self.report_error(exc, "Nusxa yaratish")
            return

        self.refresh()
        self.notify(
            f"Nusxa yaratildi: {info.path.name}\nHajmi: {info.human_size}\n\n"
            "Uni tashqi diskka yoki boshqa kompyuterga ham ko'chiring.",
            "Zaxira nusxa tayyor",
        )

    @Slot()
    def _on_verify(self) -> None:
        from distribos.infrastructure.backup import verify_backup

        path, _ = QFileDialog.getOpenFileName(
            self, "Nusxani tanlang",
            str(self.context.settings.paths.backup_dir),
            "DistribOS nusxasi (*.dbak)",
        )
        if not path:
            return
        password = PasswordDialog.ask(self, "Nusxa paroli", "Nusxa parolini kiriting.")
        if password is None:
            return

        try:
            info = verify_backup(Path(path), password)
        except Exception as exc:
            self.warn(str(exc), "Tekshiruv muvaffaqiyatsiz")
            return

        self.notify(
            f"Nusxa BUTUN va ochiladi.\n\n"
            f"Yaratilgan: {info.created_at.strftime('%d.%m.%Y %H:%M')}\n"
            f"Hajmi: {info.human_size}",
            "Nusxa tekshirildi",
        )

    @Slot()
    def _on_restore(self) -> None:
        from distribos.infrastructure.backup import restore_backup

        path, _ = QFileDialog.getOpenFileName(
            self, "Nusxani tanlang",
            str(self.context.settings.paths.backup_dir),
            "DistribOS nusxasi (*.dbak)",
        )
        if not path:
            return
        if not self.confirm(
            "Joriy ma'lumotlar nusxadagi ma'lumotlar bilan ALMASHTIRILADI.\n\n"
            "Joriy baza o'chirilmaydi — u chetga olinadi va kerak bo'lsa "
            "qaytarish mumkin.\n\n"
            "Tiklashdan so'ng dastur qayta ishga tushirilishi kerak.",
            "Nusxadan tiklash",
        ):
            return

        password = PasswordDialog.ask(self, "Nusxa paroli", "Nusxa parolini kiriting.")
        if password is None:
            return

        try:
            info = restore_backup(
                Path(path), password, self.context.settings.paths.database_path
            )
        except Exception as exc:
            self.warn(str(exc), "Tiklash muvaffaqiyatsiz")
            return

        QMessageBox.information(
            self, "Tiklandi",
            f"{info.created_at.strftime('%d.%m.%Y %H:%M')} dagi nusxa tiklandi.\n\n"
            "Dasturni yopib, qaytadan oching.",
        )


class AuditPage(BasePage):
    """Audit jurnali — o'zgarmas yozuvlar."""

    live = True

    def __init__(self, context: AppContext) -> None:
        super().__init__(
            context, "Audit jurnali",
            "Bu jurnal o'zgartirilmaydi va o'chirilmaydi — buni ma'lumotlar "
            "bazasining o'zi majburlaydi.",
        )
        self.table = DataTable(
            ["Vaqt", "Amal", "Nima", "Yozuv", "Tavsif"],
            placeholder="Amal yoki tavsif bo'yicha qidirish…",
        )
        self.add(self.table, 1)

    def refresh(self) -> None:
        with self.context.database.session() as session:
            rows = queries.list_audit(session)
        self.table.set_rows([
            (occurred.strftime("%d.%m.%Y %H:%M:%S"), action,
             entity_type or "—", (entity_id or "")[:12], summary)
            for occurred, action, entity_type, entity_id, summary in rows
        ])
        self.header.set_subtitle(f"Oxirgi {len(rows)} ta yozuv")


class SettingsPage(BasePage):
    """Sozlamalar va diagnostika."""

    def __init__(self, context: AppContext) -> None:
        super().__init__(
            context, tr("Sozlamalar"), tr("Ulanish, til va diagnostika."),
        )

        self._bundle = ghost_button(tr("Yordam to'plamini yaratish"))
        self._bundle.clicked.connect(self._on_bundle)
        self.header.add_action(self._bundle)

        language_row = QWidget()
        language_layout = QHBoxLayout(language_row)
        language_layout.setContentsMargins(0, 0, 0, 0)
        language_layout.addWidget(QLabel(tr("Til")))
        self._language = QComboBox()
        for locale in SUPPORTED_LOCALES:
            self._language.addItem(LOCALE_NAMES[locale], locale)
        active_index = self._language.findData(current_locale())
        if active_index >= 0:
            self._language.setCurrentIndex(active_index)
        # Lambda YO'Q — bog'langan slot (background.py 1-qoida).
        self._language.currentIndexChanged.connect(self._on_language_changed)
        language_layout.addWidget(self._language)
        language_layout.addStretch(1)
        self.add(language_row)

        self._info = QTextEdit()
        self._info.setReadOnly(True)
        self.add(self._info, 1)

    @Slot(int)
    def _on_language_changed(self, index: int) -> None:
        locale = self._language.itemData(index)
        if not isinstance(locale, str) or locale == current_locale():
            return
        # Joriy sessiyada DARHOL o'zgarmaydi: allaqachon qurilgan
        # widget'larni qayta chizish (`retranslateUi`) bu loyiha
        # hajmida ortiqcha murakkablik bo'lardi. Tanlov diskka
        # yoziladi va KEYINGI ishga tushirishda kuchga kiradi — bu
        # foydalanuvchiga ANIQ aytiladi, jimgina emas.
        language_prefs.save_locale(self.context.settings.paths.data_dir, locale)
        self.notify(
            tr(
                "Til o'zgartirildi. Kuchga kirishi uchun dasturni "
                "qayta ishga tushiring."
            ),
            tr("Til"),
        )

    def refresh(self) -> None:
        settings = self.context.settings
        health = self.context.provider.protocol_health_check()
        queued, dead = self.context.engine.queue_depth()
        connected = bool(
            self.context.transport is not None
            and getattr(self.context.transport, "is_connected", lambda: False)()
        )

        transport_status = getattr(self.context.transport, "status", None)
        negotiated = getattr(transport_status, "negotiated_session_expiry", None)

        lines = [
            "ULANISH",
            f"  Broker profili        : {settings.mqtt.profile.value}",
            f"  Manzil                : {settings.mqtt.host}:{settings.mqtt.port}",
            f"  TLS                   : {'yoqilgan' if settings.mqtt.tls_required else 'YO`Q'}",
            f"  Holat                 : {'ulangan' if connected else 'ulanmagan'}",
            "  Sessiya muddati (broker javobi): "
            f"{negotiated if negotiated is not None else 'noma`lum'}",
            f"  Xabar hajmi chegarasi : {settings.mqtt.max_payload_bytes // 1024} KiB",
            "",
            "XAVFSIZLIK",
            f"  Protokol              : AETHER-Q {health.protocol_version}",
            f"  Profil                : 0x{health.profile_id:02x}",
            f"  Kalit avlodi          : #{health.epoch}",
            f"  Qurilma               : {health.device_id_masked}",
            f"  Qurilmalar            : {health.peers_known} ta "
            f"({health.peers_revoked} tasi bekor qilingan)",
            f"  Takror himoyasi oynasi: {health.replay_window_size} ta yozuv",
            "",
            "NAVBAT",
            f"  Navbatda              : {queued}",
            f"  Qabul qilinmagan      : {dead}",
            "",
            "PAPKALAR",
            f"  Ma'lumot              : {settings.paths.data_dir}",
            f"  Jurnallar             : {settings.paths.log_dir}",
            f"  Zaxira nusxalar       : {settings.paths.backup_dir}",
        ]
        if health.blocking_reasons:
            lines += ["", "E'TIBOR"] + [f"  · {r}" for r in health.blocking_reasons]
        if settings.mqtt.is_public_pilot:
            lines += [
                "", "OGOHLANTIRISH",
                "  Ochiq broker ishlatilmoqda. Bu build 'production-secure'",
                "  deb belgilanmaydi. Haqiqiy mijoz ma'lumotlari uchun",
                "  xususiy MQTT broker sozlang.",
            ]
        self._info.setPlainText("\n".join(lines))

    @Slot()
    def _on_bundle(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, tr("Yordam to'plamini saqlash"),
            str(Path.home() / "distribos-diagnostika.txt"), tr("Matn (*.txt)"),
        )
        if not path:
            return
        try:
            Path(path).write_text(self._info.toPlainText(), encoding="utf-8")
        except OSError as exc:
            self.report_error(exc, tr("Yordam to'plamini saqlash"))
            return
        self.notify(
            tr(
                "To'plam saqlandi.\n\nUnda maxfiy ma'lumot, kalit yoki mijoz "
                "ma'lumotlari YO'Q — faqat texnik holat."
            ),
            tr("Yordam to'plami"),
        )


# --- dialoglar ------------------------------------------------------------


class InviteDialog(QDialog):
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setWindowTitle("Yangi qurilma")
        self.setMinimumWidth(400)

        self._name = QLineEdit()
        self._name.setPlaceholderText("Masalan: Aziz — savdo agenti")
        self._role = QComboBox()
        for key in ("agent", "warehouse", "cashier", "manager", "viewer"):
            self._role.addItem(role_name(key), key)

        form = QFormLayout()
        form.addRow("Qurilma nomi *", self._name)
        form.addRow("Rol", self._role)

        note = QLabel(
            "Taklif 10 daqiqa amal qiladi va faqat BIR MARTA ishlaydi. "
            "QR kodda uzoq muddatli kalit saqlanmaydi."
        )
        note.setWordWrap(True)
        note.setStyleSheet(f"color: {PALETTE.text_muted};")

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(note)
        layout.addWidget(buttons)

    @Slot()
    def _on_accept(self) -> None:
        if not self._name.text().strip():
            QMessageBox.warning(self, "To'ldirilmagan", "Qurilma nomini kiriting.")
            return
        self.accept()

    def values(self) -> tuple[str, str]:
        return self._role.currentData(), self._name.text().strip()


class ShowInvitationDialog(QDialog):
    """Taklifni ko'rsatadi (QR yoki matn)."""

    def __init__(self, parent: QWidget, invitation: Invitation) -> None:
        super().__init__(parent)
        self.setWindowTitle("Qurilmani ulash")
        self.setMinimumSize(460, 420)

        layout = QVBoxLayout(self)

        heading = QLabel(f"«{invitation.display_name}» uchun taklif")
        heading.setObjectName("PageTitle")
        layout.addWidget(heading)

        note = QLabel(
            "Telefondagi DistribOS ilovasida «Qurilmani ulash» ni tanlang "
            "va shu kodni skanerlang. Taklif 10 daqiqa amal qiladi."
        )
        note.setWordWrap(True)
        note.setStyleSheet(f"color: {PALETTE.text_muted};")
        layout.addWidget(note)

        payload = invitation.to_qr_payload()
        image = _render_qr(payload)
        if image is not None:
            layout.addWidget(image, 1)

        # Matnli kod DOIM ko'rsatiladi, QR bo'lsa ham. Omborda telefon
        # kamerasi ko'pincha ishlamaydi (qorong'i, iflos linza), shuning
        # uchun qo'lda kiritish zaxira emas — to'liq huquqli yo'l.
        layout.addWidget(QLabel("Yoki telefonga shu kodni kiriting:"))
        code = QTextEdit()
        code.setReadOnly(True)
        code.setPlainText(payload.hex())
        code.setMaximumHeight(90 if image is not None else 260)
        layout.addWidget(code, 0 if image is not None else 1)

        # Lambda ISHLATILMAYDI (`presentation/background.py` 1-qoidasi) —
        # bog'langan metod, kodni esa `self` da saqlaymiz.
        self._code_text = payload.hex()
        copy_button = ghost_button("Kodni nusxalash")
        copy_button.clicked.connect(self._on_copy)
        layout.addWidget(copy_button)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        buttons.button(QDialogButtonBox.StandardButton.Close).clicked.connect(self.accept)
        layout.addWidget(buttons)

    @Slot()
    def _on_copy(self) -> None:
        QApplication.clipboard().setText(self._code_text)


def _render_qr(payload: bytes) -> QLabelType | None:
    """QR kodni chizadi. Kutubxona bo'lmasa `None`."""
    try:
        import qrcode
    except ImportError:
        return None

    from PySide6.QtGui import QImage, QPixmap

    matrix = qrcode.QRCode(border=2)
    matrix.add_data(payload)
    matrix.make(fit=True)
    modules = matrix.get_matrix()

    scale = 6
    size = len(modules) * scale
    image = QImage(size, size, QImage.Format.Format_RGB32)
    image.fill(0xFFFFFFFF)
    for y, row in enumerate(modules):
        for x, filled in enumerate(row):
            if not filled:
                continue
            for dy in range(scale):
                for dx in range(scale):
                    image.setPixel(x * scale + dx, y * scale + dy, 0xFF000000)

    label = QLabel()
    label.setPixmap(QPixmap.fromImage(image))
    label.setAlignment(__import__("PySide6.QtCore", fromlist=["Qt"]).Qt.AlignmentFlag.AlignCenter)
    return label


class PasswordDialog(QDialog):
    """Parol so'raydi. Parol HECH QAYERGA yozilmaydi."""

    def __init__(
        self, parent: QWidget, title: str, message: str, *, confirm: bool = False,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(420)
        self._confirm = confirm

        self._password = QLineEdit()
        self._password.setEchoMode(QLineEdit.EchoMode.Password)
        self._repeat = QLineEdit()
        self._repeat.setEchoMode(QLineEdit.EchoMode.Password)

        note = QLabel(message)
        note.setWordWrap(True)
        note.setStyleSheet(f"color: {PALETTE.text_muted};")

        form = QFormLayout()
        form.addRow("Parol", self._password)
        if confirm:
            form.addRow("Takrorlang", self._repeat)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(note)
        layout.addLayout(form)
        layout.addWidget(buttons)

    @Slot()
    def _on_accept(self) -> None:
        if len(self._password.text()) < 8:
            QMessageBox.warning(
                self, "Parol qisqa", "Parol kamida 8 belgidan iborat bo'lsin."
            )
            return
        if self._confirm and self._password.text() != self._repeat.text():
            QMessageBox.warning(self, "Mos kelmadi", "Parollar bir xil emas.")
            return
        self.accept()

    @classmethod
    def ask(
        cls, parent: QWidget, title: str, message: str, *, confirm: bool = False
    ) -> str | None:
        dialog = cls(parent, title, message, confirm=confirm)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return None
        return dialog._password.text()
