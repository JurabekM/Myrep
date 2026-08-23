"""Har bir ekranning suratini oladi (hujjat va vizual tekshiruv uchun).

    python tools/capture_screens.py [chiqish_papkasi]

Offscreen ishlaydi — monitor kerak emas, CI'da ham yuradi.
"""

from __future__ import annotations

import sys
from pathlib import Path

# DIQQAT: bu yerda `offscreen` MAJBURLANMAYDI. Windows'da offscreen
# platformasida shriftlar umuman yuklanmaydi (QFontDatabase bo'sh) va
# butun matn "tofu" (kvadratchalar) bo'lib chiqadi -- surat yaroqsiz.
# Haqiqiy platformada oyna qisqa vaqt ko'rinadi, lekin surat to'g'ri.
# Shriftsiz muhitda ataylab ishlatish uchun: QT_QPA_PLATFORM=offscreen

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "apps" / "desktop" / "src"))

from distribos.app_context import build_context  # noqa: E402
from distribos.domain.ids import uuid7_str  # noqa: E402
from distribos.infrastructure.config import AppSettings, MqttSettings, PathSettings  # noqa: E402
from distribos.presentation.main_window import NAVIGATION, MainWindow  # noqa: E402
from distribos.presentation.theme import stylesheet  # noqa: E402
from distribos.sync.event_store import NewEvent  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402


def seed(context) -> None:
    """Ekranlar bo'sh chiqmasligi uchun realistik namuna ma'lumot."""
    from distribos.persistence.models import Organization, Warehouse

    warehouse_id = uuid7_str()
    with context.database.unit_of_work() as session:
        session.add(Organization(
            id=uuid7_str(), tenant_id=context.tenant_id,
            name="Alfa Distribution MChJ", tax_id="300123456",
            phone="+998 71 200 40 60", address="Toshkent sh., Chilonzor 12",
        ))
        session.add(Warehouse(id=warehouse_id, code="MARKAZ", name="Markaziy ombor"))

    catalogue = [
        ("COLA-1L", "Coca-Cola 1 L", 1_450_000, 1_800_000, "50"),
        ("FANTA-1L", "Fanta 1 L", 1_400_000, 1_750_000, "50"),
        ("SUV-05", "Ichimlik suvi 0.5 L", 300_000, 450_000, "100"),
        ("CHOY-100", "Qora choy 100 g", 1_200_000, 1_600_000, "30"),
        ("SHAKAR-1", "Shakar 1 kg", 1_100_000, 1_350_000, "40"),
        ("YOGH-1L", "Paxta yog'i 1 L", 2_400_000, 2_900_000, "25"),
    ]
    products: list[str] = []
    for sku, name, wholesale, retail, minimum in catalogue:
        product_id = uuid7_str()
        products.append(product_id)
        with context.database.unit_of_work() as session:
            context.command.submit(session, NewEvent(
                "PRODUCT_CREATED", "Product", product_id,
                {"product_id": product_id, "sku": sku, "name": name,
                 "unit": "dona", "wholesale_price": wholesale,
                 "retail_price": retail, "min_stock": minimum},
            ))

    clients = [
        ("M-001", "Dilshod savdo do'koni", "+998 90 123 45 67", 15_000_000),
        ("M-002", "Nodira market", "+998 91 234 56 78", 8_000_000),
        ("M-003", "Chorsu ulgurji", "+998 93 345 67 89", 40_000_000),
        ("M-004", "Baraka oziq-ovqat", "+998 94 456 78 90", 0),
    ]
    customers: list[str] = []
    for code, name, phone, limit in clients:
        customer_id = uuid7_str()
        customers.append(customer_id)
        with context.database.unit_of_work() as session:
            context.command.submit(session, NewEvent(
                "CUSTOMER_CREATED", "Customer", customer_id,
                {"customer_id": customer_id, "code": code, "name": name,
                 "kind": "COMPANY", "phone": phone, "price_tier": "wholesale",
                 "credit_limit": limit},
            ))

    # Kirim: ba'zi mahsulotlarda qoldiq ataylab minimaldan past qoldiriladi,
    # shunda «kam qoldi» ogohlantirishi va AI tavsiyasi ko'rinadi.
    receipts = ["120", "80", "40", "15", "60", "5"]
    for product_id, amount in zip(products, receipts, strict=True):
        with context.database.unit_of_work() as session:
            context.command.submit(session, NewEvent(
                "INVENTORY_MOVED", "Inventory", product_id,
                {"movement_id": uuid7_str(), "warehouse_id": warehouse_id,
                 "product_id": product_id, "movement_type": "RECEIPT",
                 "quantity": amount, "occurred_at": "2026-08-20T09:00:00+00:00"},
            ))

    orders = [
        (customers[0], [(products[0], "12"), (products[2], "24")], "2026-08-21T10:15:00+00:00"),
        (customers[1], [(products[1], "8"), (products[4], "10")], "2026-08-22T11:30:00+00:00"),
        (customers[2], [(products[0], "40"), (products[3], "6"), (products[5], "3")],
         "2026-08-22T15:45:00+00:00"),
        (customers[3], [(products[2], "30")], "2026-08-23T09:20:00+00:00"),
    ]
    order_ids: list[str] = []
    for index, (customer_id, lines, ordered_at) in enumerate(orders, start=1):
        order_id = uuid7_str()
        order_ids.append(order_id)
        with context.database.unit_of_work() as session:
            context.command.submit(session, NewEvent(
                "ORDER_CREATED", "Order", order_id,
                {"order_id": order_id, "number": f"B-{index:05d}",
                 "customer_id": customer_id, "ordered_at": ordered_at,
                 "lines": [
                     {"line_id": uuid7_str(), "product_id": product_id,
                      "quantity": quantity, "unit_price": 1_450_000}
                     for product_id, quantity in lines
                 ]},
            ))

    # Bir nechta buyurtmani oldinga suramiz — holatlar rang-barang bo'lsin.
    for order_id, chain in (
        (order_ids[0], ["CONFIRMED", "APPROVED", "ALLOCATED", "PICKED", "SHIPPED", "DELIVERED"]),
        (order_ids[1], ["CONFIRMED", "APPROVED"]),
        (order_ids[2], ["CONFIRMED"]),
    ):
        previous = "DRAFT"
        for target in chain:
            with context.database.unit_of_work() as session:
                context.command.submit(session, NewEvent(
                    "ORDER_STATE_CHANGED", "Order", order_id,
                    {"order_id": order_id, "from_state": previous, "to_state": target},
                ))
            previous = target

    for index, (customer_id, amount) in enumerate(
        [(customers[0], 20_000_000), (customers[1], 5_000_000)], start=1
    ):
        payment_id = uuid7_str()
        with context.database.unit_of_work() as session:
            context.command.submit(session, NewEvent(
                "PAYMENT_RECORDED", "Payment", payment_id,
                {"payment_id": payment_id, "number": f"T-{index:05d}",
                 "direction": "IN", "amount": amount,
                 "occurred_at": "2026-08-22T16:00:00+00:00",
                 "customer_id": customer_id, "method": "cash"},
            ))


def main() -> int:
    output = Path(sys.argv[1]) if len(sys.argv) > 1 else _ROOT / "docs" / "screenshots"
    output.mkdir(parents=True, exist_ok=True)

    import tempfile

    workdir = Path(tempfile.mkdtemp(prefix="distribos-shots-"))
    settings = AppSettings(
        environment="test", mqtt=MqttSettings(),
        paths=PathSettings(
            data_dir=workdir / "data", log_dir=workdir / "logs",
            backup_dir=workdir / "backups",
        ),
        public_pilot_warning_accepted=True,
    )

    application = QApplication.instance() or QApplication([])
    application.setStyleSheet(stylesheet())

    context = build_context(settings, allow_insecure_secrets=True)
    seed(context)

    window = MainWindow(context)
    window.resize(1440, 900)
    window.show()
    application.processEvents()

    saved = []
    for _, items in NAVIGATION:
        for key, title in items:
            window._select(key)
            application.processEvents()
            application.processEvents()
            path = output / f"{key}.png"
            window.grab().save(str(path))
            saved.append((key, title, path))
            print(f"  {title:24s} -> {path.name}")

    window._sync.stop()
    context.close()
    print(f"\n{len(saved)} ta ekran surati: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
