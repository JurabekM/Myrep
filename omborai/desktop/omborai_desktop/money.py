from decimal import ROUND_HALF_UP, Decimal


def round_som(value: Decimal | int) -> int:
    """Summani so'mga yaxlitlaydi (tiyin yo'q). Backend bilan bir xil qoida: ROUND_HALF_UP."""
    return int(Decimal(value).quantize(Decimal(1), rounding=ROUND_HALF_UP))


def format_som(amount: int) -> str:
    """14500 -> '14 500'. Bo'shliq — ming ajratuvchi."""
    sign = "-" if amount < 0 else ""
    return sign + f"{abs(amount):,}".replace(",", " ")


def format_qty(qty: Decimal) -> str:
    """Miqdorni ortiqcha nollarsiz ko'rsatadi: 2.000 -> '2', 1.500 -> '1.5'."""
    text = format(qty.normalize(), "f")
    return text
