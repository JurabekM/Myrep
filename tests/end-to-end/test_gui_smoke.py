"""GUI smoke testi — HAR BIR ekran ochilishi va yiqilmasligi.

«Unit testlar o'tdi» degani «dastur ishlaydi» degani emas. Bu test
haqiqiy `QApplication` quradi, asosiy oynani ochadi va **har bir
sahifaga o'tib**, `refresh()` ni chaqiradi. Ko'p xatolar aynan shu
yerda chiqadi: yopilgan sessiyadan o'qish, yo'q atribut, noto'g'ri
signal ulanishi.

Offscreen rejimda ishlaydi (`QT_QPA_PLATFORM=offscreen`), ya'ni CI'da
ham monitor kerak emas.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

pytest.importorskip("PySide6", reason="PySide6 o'rnatilmagan")

from distribos.app_context import build_context
from distribos.domain.ids import uuid7_str
from distribos.infrastructure.config import (
    AppSettings,
    MqttSettings,
    PathSettings,
)
from distribos.presentation.main_window import NAVIGATION, MainWindow
from distribos.presentation.theme import stylesheet
from distribos.sync.event_store import NewEvent
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="module")
def app():
    application = QApplication.instance() or QApplication([])
    application.setStyleSheet(stylesheet())
    yield application


@pytest.fixture(scope="module")
def context(tmp_path_factory):
    base = tmp_path_factory.mktemp("distribos-gui")
    settings = AppSettings(
        environment="test",
        mqtt=MqttSettings(),
        paths=PathSettings(
            data_dir=base / "data", log_dir=base / "logs", backup_dir=base / "backups"
        ),
        public_pilot_warning_accepted=True,
    )
    ctx = build_context(settings, allow_insecure_secrets=True)
    _seed(ctx)
    yield ctx
    ctx.close()


def _seed(ctx) -> None:
    """Sahifalar bo'sh bo'lmasligi uchun namuna ma'lumot."""
    from distribos.persistence.models import Organization, Warehouse

    product_id, customer_id, warehouse_id = uuid7_str(), uuid7_str(), uuid7_str()

    with ctx.database.unit_of_work() as session:
        session.add(Organization(
            id=uuid7_str(), tenant_id=ctx.tenant_id, name="Sinov Savdo MChJ",
            phone="+998 90 000 00 00", currency="UZS",
        ))
        session.add(Warehouse(id=warehouse_id, code="W1", name="Asosiy ombor"))

    with ctx.database.unit_of_work() as session:
        ctx.command.submit(session, NewEvent(
            "PRODUCT_CREATED", "Product", product_id,
            {"product_id": product_id, "sku": "COLA-1L", "name": "Cola 1L",
             "unit": "dona", "wholesale_price": 1_500_000,
             "retail_price": 1_800_000, "min_stock": "20"},
        ))
        ctx.command.submit(session, NewEvent(
            "CUSTOMER_CREATED", "Customer", customer_id,
            {"customer_id": customer_id, "code": "M-001", "name": "Dilshod savdo",
             "kind": "COMPANY", "price_tier": "wholesale", "credit_limit": 5_000_000},
        ))

    with ctx.database.unit_of_work() as session:
        ctx.command.submit(session, NewEvent(
            "INVENTORY_MOVED", "Inventory", product_id,
            {"movement_id": uuid7_str(), "warehouse_id": warehouse_id,
             "product_id": product_id, "movement_type": "RECEIPT",
             "quantity": "10", "occurred_at": "2026-08-23T09:00:00+00:00"},
        ))

    order_id = uuid7_str()
    with ctx.database.unit_of_work() as session:
        ctx.command.submit(session, NewEvent(
            "ORDER_CREATED", "Order", order_id,
            {"order_id": order_id, "number": "T-00001", "customer_id": customer_id,
             "ordered_at": "2026-08-23T10:00:00+00:00",
             "lines": [{"line_id": uuid7_str(), "product_id": product_id,
                        "quantity": "3", "unit_price": 1_500_000}]},
        ))

    payment_id = uuid7_str()
    with ctx.database.unit_of_work() as session:
        ctx.command.submit(session, NewEvent(
            "PAYMENT_RECORDED", "Payment", payment_id,
            {"payment_id": payment_id, "number": "T-P-1", "direction": "IN",
             "amount": 2_000_000, "occurred_at": "2026-08-23T11:00:00+00:00",
             "customer_id": customer_id},
        ))


@pytest.fixture(scope="module")
def window(app, context):
    main = MainWindow(context)
    main.show()
    app.processEvents()
    yield main
    main._sync.stop()
    main.hide()


ALL_PAGE_KEYS = [key for _, items in NAVIGATION for key, _ in items]


def test_window_opens(window) -> None:
    assert window.isVisible()
    assert window.windowTitle() == "DistribOS AI"


def test_every_navigation_entry_has_a_page(window) -> None:
    """Navigatsiyada bor, lekin sahifasi yo'q punkt bo'lmasin."""
    missing = [key for key in ALL_PAGE_KEYS if key not in window._pages]
    assert not missing, f"Sahifasi yo'q bo'limlar: {missing}"


@pytest.mark.parametrize("key", ALL_PAGE_KEYS)
def test_page_opens_and_refreshes(window, app, key: str) -> None:
    """Har bir ekranni ochib, ma'lumot yuklanishini tekshiradi."""
    window._select(key)
    app.processEvents()

    page = window._pages[key]
    assert window._stack.currentWidget() is page
    assert page.isVisible()

    # `refresh()` ni yana bir marta — ikki marta chaqirilganda ham yiqilmasin.
    page.refresh()
    app.processEvents()


def test_pages_with_data_are_not_empty(window, app) -> None:
    """Namuna ma'lumot kiritilgan sahifalarda jadval BO'SH BO'LMASLIGI kerak.

    Bo'sh jadval «ishlayapti»dek ko'rinadi, lekin aslida so'rov noto'g'ri
    bo'lishi mumkin — shuning uchun aniq tekshiramiz.
    """
    expectations = {
        "products": "Mahsulot ro'yxati",
        "customers": "Mijozlar ro'yxati",
        "orders": "Buyurtmalar ro'yxati",
    }
    for key, label in expectations.items():
        window._select(key)
        app.processEvents()
        page = window._pages[key]
        assert page.table.row_count() > 0, f"{label} bo'sh chiqdi"


def test_inventory_shows_computed_stock(window, app) -> None:
    window._select("inventory")
    app.processEvents()
    page = window._pages["inventory"]
    assert page.stock_table.row_count() > 0, "qoldiq jadvali bo'sh"
    assert page.movement_table.row_count() > 0, "harakatlar jadvali bo'sh"


def test_sync_page_reports_device_state(window, app) -> None:
    window._select("sync")
    app.processEvents()
    page = window._pages["sync"]
    assert "yozuv" in page.header._subtitle.text()


def test_reports_page_builds_every_report(window, app) -> None:
    """Har bir hisobot turini shakllantiradi — biror so'rov buzuq bo'lmasin."""
    window._select("reports")
    app.processEvents()
    page = window._pages["reports"]

    for index in range(page._choice.count()):
        page._choice.setCurrentIndex(index)
        page._on_build()
        app.processEvents()
        assert page._report is not None, (
            f"hisobot shakllanmadi: {page._choice.itemText(index)}"
        )


def test_assistant_produces_suggestions(window, app) -> None:
    """Namuna ma'lumotda qoldiq minimaldan past — tavsiya chiqishi kerak."""
    window._select("assistant")
    app.processEvents()
    page = window._pages["assistant"]
    assert page.table.row_count() > 0, "AI hech qanday tavsiya bermadi"


def test_security_page_shows_protocol(window, app) -> None:
    window._select("security")
    app.processEvents()
    page = window._pages["security"]
    assert "AETHER-Q" in page._card_protocol._value.text()


def test_settings_page_hides_no_secrets(window, app) -> None:
    """Diagnostika matnida kalit yoki maxfiy material BO'LMASLIGI kerak."""
    window._select("settings")
    app.processEvents()
    page = window._pages["settings"]
    text = page._info.toPlainText()

    assert "AETHER-Q" in text
    for forbidden in ("BEGIN PRIVATE", "sign_sk", "root_secret", "aead_key"):
        assert forbidden not in text, f"diagnostikada maxfiy material: {forbidden}"


def test_language_switch_persists_to_disk(window, app, monkeypatch) -> None:
    """Til tanlagichi diskka yozadi — keyingi ishga tushirishda o'qiladi.

    Qo'lda sinov (`docs/HOLAT.md` §5.7) haqiqiy oynada tasdiqladi:
    navigatsiya va menyu darhol rus tiliga o'tadi. Bu yerda faqat
    SAQLASH mexanizmi tekshiriladi — combo box'ni chertish emas,
    slotni to'g'ridan-to'g'ri chaqirish (offscreen, sichqonchasiz).

    `notify()` MODAL `QMessageBox` ochadi — offscreen rejimda uni
    hech kim yopolmaydi va sinov ABADIY OSILIB QOLADI. Shuning uchun
    bu yerda soxtalashtiriladi (haqiqiy ilovada muammo emas: foydalanuvchi
    uni bosib yopadi).
    """
    from distribos.i18n import prefs

    window._select("settings")
    app.processEvents()
    page = window._pages["settings"]
    monkeypatch.setattr(page, "notify", lambda *a, **k: None)

    ru_index = page._language.findData("ru")
    assert ru_index >= 0, "rus tili tanlov ro'yxatida yo'q"

    page._on_language_changed(ru_index)

    saved = prefs.load_saved_locale(window._context.settings.paths.data_dir)
    assert saved == "ru"


def test_no_technical_jargon_in_user_interface(window, app) -> None:
    """Foydalanuvchi «aggregate», «outbox», «projector» ko'rmasligi kerak."""
    from PySide6.QtWidgets import QLabel, QPushButton

    jargon = ("aggregate", "outbox", "inbox", "projector", "checkpoint",
              "idempoten", "envelope", "payload")

    findings: list[str] = []
    for key in ALL_PAGE_KEYS:
        window._select(key)
        app.processEvents()
        page = window._pages[key]
        widgets = list(page.findChildren(QLabel)) + list(page.findChildren(QPushButton))
        for widget in widgets:
            text = widget.text().lower()
            for word in jargon:
                if word in text:
                    findings.append(f"{key}: {widget.text()!r} ({word})")

    assert not findings, "Interfeysda texnik atamalar topildi:\n" + "\n".join(findings)
