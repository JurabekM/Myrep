"""Domen qoidalari uchun moslik vektorlarini generatsiya qiladi.

Python va Kotlin bir xil biznes qoidalarini AYNAN bir xil hisoblashi
kerak. Aks holda telefonda hisoblangan buyurtma summasi desktopda
boshqacha chiqadi — bu sinxronizatsiyada tuzatib bo'lmaydigan xato,
chunki ikkala qiymat ham "to'g'ri" imzolangan bo'ladi.

Bu vektorlar CHEKKA HOLATLARNI ataylab qamraydi: yaxlitlash chegarasi,
nol narx, 100% chegirma, manfiy tuzatish, katta sonlar.

    python tools/gen_rules_parity.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "apps" / "desktop" / "src"))

from distribos.domain import rules  # noqa: E402
from distribos.persistence.models import MovementType, OrderState  # noqa: E402

OUTPUT = _ROOT / "tests" / "interoperability" / "rules_parity.json"


def transitions() -> list[dict]:
    """Har bir (joriy, maqsad) juftligi uchun ruxsat/rad."""
    cases = []
    for current in OrderState:
        for target in OrderState:
            cases.append({
                "current": current.value,
                "target": target.value,
                "allowed": rules.can_transition(current, target),
            })
    return cases


def line_totals() -> list[dict]:
    """Yaxlitlash chegaralarini ataylab qamraydi."""
    inputs = [
        ("10", 15000, "0"),
        ("10", 15000, "10"),
        ("3", 3333, "15"),          # 8499.15 -> 8499 (HALF_UP)
        ("1", 1, "50"),             # 0.5 -> 1 (HALF_UP, .5 tepaga)
        ("1", 3, "50"),             # 1.5 -> 2
        ("1", 5, "50"),             # 2.5 -> 3
        ("7", 142857, "33.33"),
        ("0.001", 1000000, "0"),
        ("12.345", 987654, "7.5"),
        ("1000000", 999999999, "0"),
        ("5", 20000, "100"),        # to'liq chegirma
        ("0", 15000, "0"),
    ]
    return [
        {
            "quantity": quantity, "unit_price": price, "discount_percent": discount,
            "line_total": rules.line_total(quantity, price, discount),
        }
        for quantity, price, discount in inputs
    ]


def order_totals() -> list[dict]:
    scenarios = [
        [{"quantity": "10", "unit_price": 15000, "discount_percent": "10"},
         {"quantity": "2", "unit_price": 50000}],
        [{"quantity": "3", "unit_price": 3333, "discount_percent": "15"}] * 10,
        [{"quantity": "1.5", "unit_price": 199999, "discount_percent": "2.5"},
         {"quantity": "0.25", "unit_price": 800000},
         {"quantity": "100", "unit_price": 1, "discount_percent": "99"}],
        [],
    ]
    cases = []
    for lines in scenarios:
        totals = rules.compute_order_totals(lines)
        cases.append({
            "lines": [
                {
                    "quantity": line["quantity"],
                    "unit_price": line["unit_price"],
                    "discount_percent": str(line.get("discount_percent", 0)),
                }
                for line in lines
            ],
            "subtotal": totals.subtotal,
            "discount_total": totals.discount_total,
            "total": totals.total,
        })
    return cases


def prices() -> list[dict]:
    cases = []
    catalogue = [
        ({"retail_price": 20000, "wholesale_price": 17000, "agent_price": 15000}, "retail"),
        ({"retail_price": 20000, "wholesale_price": 17000, "agent_price": 15000}, "wholesale"),
        ({"retail_price": 20000, "wholesale_price": 17000, "agent_price": 15000}, "agent"),
        ({"retail_price": 20000, "wholesale_price": 0, "agent_price": 0}, "agent"),
        ({"retail_price": 0, "wholesale_price": 5000, "agent_price": 0}, "retail"),
        ({"retail_price": 20000, "wholesale_price": 17000}, "noma'lum-toifa"),
    ]
    for price_map, tier in catalogue:
        try:
            resolved = rules.resolve_unit_price(price_map, tier)
            error = None
        except rules.DomainError:
            resolved, error = None, "no_price"
        cases.append({
            "prices": price_map, "price_tier": tier,
            "unit_price": resolved, "error": error,
        })
    return cases


def credit() -> list[dict]:
    inputs = [
        (800_000, 1_000_000, 300_000),
        (500_000, 1_000_000, 300_000),
        (9_000_000, 0, 5_000_000),
        (-200_000, 1_000_000, 300_000),
        (1_000_000, 1_000_000, 0),
        (0, 1_000_000, 1_000_001),
    ]
    return [
        {
            "current_debt": debt, "credit_limit": limit, "order_total": total,
            "allowed": (result := rules.check_credit_limit(debt, limit, total)).allowed,
            "projected_debt": result.projected_debt,
        }
        for debt, limit, total in inputs
    ]


def stock() -> list[dict]:
    scenarios = [
        [("RECEIPT", "100"), ("SALE", "30"), ("RETURN_IN", "5"), ("WRITE_OFF", "2")],
        [("RECEIPT", "100"), ("SALE", "30"), ("SALE", "40")],
        [("RECEIPT", "100"), ("RESERVATION", "25"), ("RELEASE", "10")],
        [("RECEIPT", "50"), ("ADJUSTMENT", "-8")],
        [("RECEIPT", "12.345"), ("SALE", "0.345")],
        [("TRANSFER_IN", "10"), ("TRANSFER_OUT", "3")],
        [],
    ]
    cases = []
    for movements in scenarios:
        on_hand, reserved = rules.compute_stock(movements)
        cases.append({
            "movements": [{"type": m, "quantity": q} for m, q in movements],
            "on_hand": str(on_hand),
            "reserved": str(reserved),
            "available": str(rules.available_stock(on_hand, reserved)),
        })
    return cases


def allocations() -> list[dict]:
    inputs = [
        (500_000, [("o1", 300_000), ("o2", 400_000)]),
        (1_000_000, [("o1", 300_000)]),
        (100_000, [("o1", 0), ("o2", 250_000)]),
        (0, [("o1", 100_000)]),
    ]
    return [
        {
            "amount": amount,
            "open_orders": [{"order_id": oid, "outstanding": due} for oid, due in orders],
            "allocations": [
                {"order_id": oid, "amount": applied}
                for oid, applied in rules.allocate_payment(amount, orders)
            ],
        }
        for amount, orders in inputs
    ]


def main() -> int:
    payload = {
        "generated_by": "tools/gen_rules_parity.py",
        "note": (
            "Python va Kotlin domen qoidalari bir xil natija berishini "
            "qulflaydi. Chekka holatlar ataylab kiritilgan."
        ),
        "order_transitions": transitions(),
        "line_totals": line_totals(),
        "order_totals": order_totals(),
        "prices": prices(),
        "credit": credit(),
        "stock": stock(),
        "payment_allocations": allocations(),
        "movement_types": [m.value for m in MovementType],
        "order_states": [s.value for s in OrderState],
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    android_copy = _ROOT / "apps" / "android" / "domain" / "src" / "test" / "resources"
    android_copy.mkdir(parents=True, exist_ok=True)
    (android_copy / "rules_parity.json").write_text(
        OUTPUT.read_text(encoding="utf-8"), encoding="utf-8"
    )

    counts = {
        key: len(value) for key, value in payload.items() if isinstance(value, list)
    }
    print(f"Moslik vektorlari yozildi: {OUTPUT}")
    for name, count in counts.items():
        print(f"  {name:22s} {count}")
    print(f"Jami: {sum(counts.values())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
