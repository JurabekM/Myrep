"""Chek matni (80mm yoki 58mm printer uchun). Ko'rsatish va ESC/POS chop etish uchun bir xil manba."""

from decimal import Decimal
from typing import Any

from .money import format_qty, format_som

METHOD_LABELS = {"cash": "Naqd", "card": "Karta", "click": "Click", "payme": "Payme"}


def _two_cols(left: str, right: str, width: int) -> str:
    gap = width - len(left) - len(right)
    if gap < 1:
        return f"{left[: width - len(right) - 1]} {right}"
    return f"{left}{' ' * gap}{right}"


def _wrap(text: str, width: int) -> list[str]:
    words, lines, current = text.split(), [], ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if len(candidate) <= width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word[:width]
    if current:
        lines.append(current)
    return lines or [""]


def render_receipt(sale: dict[str, Any], store_name: str, *, width: int = 32, change: int = 0) -> str:
    rule = "-" * width
    out = [store_name.center(width), rule]
    out.append(_two_cols(f"Chek #{sale['number']}", str(sale["created_at"])[:16].replace("T", " "), width))
    out.append(rule)
    for item in sale["items"]:
        for line in _wrap(item["product_name"], width):
            out.append(line)
        qty = format_qty(Decimal(str(item["qty"])))
        out.append(
            _two_cols(
                f"  {qty} {item['unit']} x {format_som(item['unit_price'])}",
                format_som(item["line_total"]),
                width,
            )
        )
    out.append(rule)
    out.append(_two_cols("Jami", format_som(sale["subtotal"]), width))
    if sale.get("discount"):
        out.append(_two_cols("Chegirma", f"-{format_som(sale['discount'])}", width))
    out.append(_two_cols("JAMI TO'LOV", format_som(sale["total"]), width))
    out.append(rule)
    for payment in sale["payments"]:
        label = METHOD_LABELS.get(payment["method"], payment["method"])
        out.append(_two_cols(label, format_som(payment["amount"]), width))
    if change > 0:
        out.append(_two_cols("Qaytim", format_som(change), width))
    out.append(rule)
    out.append("Xaridingiz uchun rahmat!".center(width))
    return "\n".join(out) + "\n"
