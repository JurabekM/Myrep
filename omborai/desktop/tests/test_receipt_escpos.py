import uuid
from decimal import Decimal

from omborai_desktop.escpos import CUT, INIT, build_receipt_bytes
from omborai_desktop.receipt import render_receipt

SALE = {
    "number": 1042,
    "created_at": "2026-10-10T14:32:00+05:00",
    "subtotal": 38500,
    "discount": 500,
    "total": 38000,
    "items": [
        {
            "product_name": "Shakar 1 kg juda uzun nomli tovar",
            "qty": "2.000",
            "unit": "kg",
            "unit_price": 14500,
            "line_total": 29000,
        },
        {"product_name": "Sut 1 L", "qty": "1", "unit": "dona", "unit_price": 12000, "line_total": 9500},
    ],
    "payments": [{"method": "cash", "amount": 38000}],
    "id": str(uuid.uuid4()),
}


def test_receipt_lines_fit_width_and_show_totals():
    text = render_receipt(SALE, "Do'kon 1", width=32, change=2000)
    lines = text.splitlines()

    assert max(len(line) for line in lines) <= 32
    assert any(line.startswith("Chek #1042") for line in lines)
    assert any("JAMI TO'LOV" in line and "38 000" in line for line in lines)
    assert any("Chegirma" in line and "500" in line for line in lines)
    assert any("Naqd" in line and "38 000" in line for line in lines)
    assert any("Qaytim" in line and "2 000" in line for line in lines)


def test_receipt_wraps_long_product_names():
    text = render_receipt(SALE, "Do'kon 1", width=32)
    assert "Shakar 1 kg juda uzun nomli tovar" not in text
    assert "Shakar 1 kg juda uzun" in text


def test_escpos_bytes_start_with_init_and_end_with_cut():
    data = build_receipt_bytes("Salom\n")
    assert data.startswith(INIT)
    assert data.endswith(CUT)
    assert "Salom".encode("cp866") in data


def test_quantity_formatting_in_receipt():
    text = render_receipt(SALE, "Do'kon 1", width=32)
    assert "2 kg x 14 500" in text
    assert Decimal("1") == Decimal("1.000")
