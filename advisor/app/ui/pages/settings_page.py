"""Sozlamalar sahifasi — AI kalitlari, biznes profili, AI holati."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.container import Container
from app.ui.widgets.common import Card, PageHeader

_HELP_TEXT = (
    "AI ishlashi uchun kamida bitta bepul kalit yoki lokal model kerak "
    "(hech qanday pullik obuna shart emas):\n"
    "• Groq (tez, bepul): https://console.groq.com/keys\n"
    "• Google Gemini (bepul): https://aistudio.google.com/app/apikey\n"
    "• OpenRouter (bepul modellar): https://openrouter.ai/keys\n"
    "• Oflayn: models/ papkasiga .gguf model joylashtiring (llama-cpp-python)."
)

_BUSINESS_TYPES = ["", "ytt", "mchj", "microfirm", "startup", "freelancer"]


class SettingsPage(QWidget):
    def __init__(self, container: Container, parent: QWidget | None = None):
        super().__init__(parent)
        self._container = container
        self._config = container.config

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        inner = QWidget()
        scroll.setWidget(inner)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        root = QVBoxLayout(inner)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(12)
        root.addWidget(PageHeader("Sozlamalar", "AI provayderlar va biznes profili"))

        # AI holati
        status_card = Card()
        status_card.layout().addWidget(QLabel("AI holati"))
        self._status_label = QLabel("")
        self._status_label.setWordWrap(True)
        status_card.layout().addWidget(self._status_label)
        root.addWidget(status_card)

        # AI kalitlari
        keys_card = Card()
        keys_card.layout().addWidget(QLabel("Bepul AI kalitlari"))
        help_label = QLabel(_HELP_TEXT)
        help_label.setObjectName("Muted")
        help_label.setWordWrap(True)
        keys_card.layout().addWidget(help_label)

        self._groq = QLineEdit(self._config.ai.groq_api_key)
        self._groq.setPlaceholderText("Groq API key (ixtiyoriy)")
        self._gemini = QLineEdit(self._config.ai.gemini_api_key)
        self._gemini.setPlaceholderText("Gemini API key (ixtiyoriy)")
        self._openrouter = QLineEdit(self._config.ai.openrouter_api_key)
        self._openrouter.setPlaceholderText("OpenRouter API key (ixtiyoriy)")
        for label, field in [
            ("Groq:", self._groq), ("Gemini:", self._gemini), ("OpenRouter:", self._openrouter)
        ]:
            keys_card.layout().addWidget(QLabel(label))
            field.setEchoMode(QLineEdit.EchoMode.Password)
            keys_card.layout().addWidget(field)
        root.addWidget(keys_card)

        # Biznes profili
        profile_card = Card()
        profile_card.layout().addWidget(QLabel("Biznes profili (AI shaxsiylashtiruvi uchun)"))
        p = self._config.profile
        self._industry = QLineEdit(p.industry); self._industry.setPlaceholderText("Soha")
        self._location = QLineEdit(p.location); self._location.setPlaceholderText("Hudud")
        self._employees = QLineEdit(str(p.employees) if p.employees else "")
        self._employees.setPlaceholderText("Xodimlar soni")
        self._business_type = QComboBox()
        self._business_type.addItems(_BUSINESS_TYPES)
        if p.business_type in _BUSINESS_TYPES:
            self._business_type.setCurrentText(p.business_type)
        self._goals = QTextEdit(p.goals); self._goals.setFixedHeight(56)
        self._goals.setPlaceholderText("Maqsadlar")

        for label, widget in [
            ("Soha:", self._industry), ("Biznes turi:", self._business_type),
            ("Hudud:", self._location), ("Xodimlar:", self._employees),
            ("Maqsadlar:", self._goals),
        ]:
            profile_card.layout().addWidget(QLabel(label))
            profile_card.layout().addWidget(widget)
        root.addWidget(profile_card)

        # Saqlash
        save_row = QHBoxLayout()
        save_btn = QPushButton("Saqlash")
        save_btn.setObjectName("Primary")
        save_btn.clicked.connect(self._save)
        save_row.addWidget(save_btn)
        self._save_status = QLabel("")
        self._save_status.setObjectName("Muted")
        save_row.addWidget(self._save_status)
        save_row.addStretch(1)
        root.addLayout(save_row)
        root.addStretch(1)

        self._refresh_status()

    def _refresh_status(self) -> None:
        providers = self._container.router.available_providers()
        if providers:
            self._status_label.setText(
                f"✅ Faol provayderlar: {', '.join(providers)}\n"
                "Router ularni shu tartibda sinaydi; biri ishlamasa keyingisiga o'tadi."
            )
            self._status_label.setStyleSheet("color: #22c55e;")
        else:
            self._status_label.setText(
                "⚠️ Hech qanday AI provayder sozlanmagan. Quyida bepul kalit kiriting "
                "yoki models/ papkasiga GGUF model joylashtiring."
            )
            self._status_label.setStyleSheet("color: #f59e0b;")

    def _save(self) -> None:
        self._config.ai.groq_api_key = self._groq.text().strip()
        self._config.ai.gemini_api_key = self._gemini.text().strip()
        self._config.ai.openrouter_api_key = self._openrouter.text().strip()

        self._config.profile.industry = self._industry.text().strip()
        self._config.profile.location = self._location.text().strip()
        self._config.profile.business_type = self._business_type.currentText()
        self._config.profile.goals = self._goals.toPlainText().strip()
        employees = self._employees.text().strip()
        self._config.profile.employees = int(employees) if employees.isdigit() else 0

        self._config.save()
        # Router va provayderlarni yangi kalitlar bilan qayta quramiz.
        from app.ai.router import ModelRouter, build_providers

        self._container.router = ModelRouter(
            build_providers(self._config),
            self._config.ai.provider_order,
            self._container.usage,
        )
        self._rewire_services()
        self._save_status.setText("✓ Saqlandi")
        self._refresh_status()

    def _rewire_services(self) -> None:
        """Yangi router/profilni bog'liq servislarga qayta ulaymiz."""
        c = self._container
        profile = self._config.profile
        c.chat_service._router = c.router  # noqa: SLF001
        c.chat_service._profile = profile  # noqa: SLF001
        c.consultant_service._router = c.router  # noqa: SLF001
        c.consultant_service._profile = profile  # noqa: SLF001
        c.legal_service._router = c.router  # noqa: SLF001
        c.tax_service._router = c.router  # noqa: SLF001
        c.marketing_service._router = c.router  # noqa: SLF001
        c.document_service._router = c.router  # noqa: SLF001
