"""Domen qoidalari — buyurtma holati, narx, chegirma, qoldiq, qarzdorlik.

Bu modul **sof**: bazaga ham, tarmoqqa ham tegmaydi. Shuning uchun uni
tez va to'liq test qilish mumkin, va bir xil qoidalar Android'da ham
takrorlanadi (kontrakt testlari bilan solishtiriladi).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from distribos.persistence.models import MOVEMENT_SIGN, MovementType, OrderState


class DomainError(Exception):
    """Biznes qoidasi buzildi."""


class IllegalStateTransition(DomainError):
    """Buyurtma holati noqonuniy o'tishga urindi."""


# --- buyurtma holat mashinasi ---------------------------------------------

#: Ruxsat etilgan o'tishlar. Bu yerda yo'q o'tish RAD ETILADI (§13).
ORDER_TRANSITIONS: dict[OrderState, frozenset[OrderState]] = {
    OrderState.DRAFT: frozenset({OrderState.CONFIRMED, OrderState.CANCELLED}),
    OrderState.CONFIRMED: frozenset({OrderState.APPROVED, OrderState.CANCELLED}),
    OrderState.APPROVED: frozenset({OrderState.ALLOCATED, OrderState.CANCELLED}),
    OrderState.ALLOCATED: frozenset({OrderState.PICKED, OrderState.CANCELLED}),
    OrderState.PICKED: frozenset({OrderState.SHIPPED, OrderState.CANCELLED}),
    OrderState.SHIPPED: frozenset({OrderState.DELIVERED}),
    OrderState.DELIVERED: frozenset(
        {OrderState.PARTIALLY_RETURNED, OrderState.RETURNED}
    ),
    OrderState.PARTIALLY_RETURNED: frozenset({OrderState.RETURNED}),
    # Yakuniy holatlar — chiqish yo'q.
    OrderState.RETURNED: frozenset(),
    OrderState.CANCELLED: frozenset(),
}

#: Jo'natilgandan keyin bekor qilib bo'lmaydi — tovar allaqachon ketgan.
TERMINAL_STATES: frozenset[OrderState] = frozenset(
    {OrderState.RETURNED, OrderState.CANCELLED}
)


def can_transition(current: OrderState, target: OrderState) -> bool:
    return target in ORDER_TRANSITIONS.get(current, frozenset())


def assert_transition(current: OrderState, target: OrderState) -> None:
    """Noqonuniy o'tishda `IllegalStateTransition`.

    Bu tekshiruv sinxronizatsiyada ham ishlaydi: peer'dan kelgan
    `ORDER_STATE_CHANGED` noqonuniy bo'lsa, u qo'llanmaydi va konflikt
    sifatida ko'rsatiladi — jimgina qabul qilinmaydi.
    """
    if not can_transition(current, target):
        allowed = sorted(s.value for s in ORDER_TRANSITIONS.get(current, frozenset()))
        raise IllegalStateTransition(
            f"{current.value} -> {target.value} mumkin emas. "
            f"Ruxsat etilgan: {allowed or 'yakuniy holat'}"
        )


def is_terminal(state: OrderState) -> bool:
    return state in TERMINAL_STATES


# --- narx va chegirma -----------------------------------------------------

#: Mijoz toifasi -> mahsulotdagi narx maydoni.
PRICE_TIERS: dict[str, str] = {
    "retail": "retail_price",
    "wholesale": "wholesale_price",
    "agent": "agent_price",
}


def resolve_unit_price(product_prices: dict[str, int], price_tier: str) -> int:
    """Mijoz toifasiga mos narxni tanlaydi (tiyinda).

    Toifa narxi 0 bo'lsa — ulgurjiga, u ham bo'lmasa chakanaga tushadi.
    Narx umuman yo'q bo'lsa xato: 0 so'mga sotishni jimgina ruxsat berish
    moliyaviy teshik ochadi.
    """
    field = PRICE_TIERS.get(price_tier, "wholesale_price")
    for candidate in (field, "wholesale_price", "retail_price"):
        price = product_prices.get(candidate, 0)
        if price > 0:
            return int(price)
    raise DomainError("Mahsulot uchun narx belgilanmagan")


def line_total(
    quantity: Decimal | str, unit_price: int, discount_percent: Decimal | str = 0
) -> int:
    """Qator summasi (tiyinda, butun son).

    Yaxlitlash ROUND_HALF_UP — moliyaviy hisobda odatiy. Butun songa
    yaxlitlanadi, ya'ni tiyindan mayda qism qolmaydi.
    """
    qty = Decimal(str(quantity))
    discount = Decimal(str(discount_percent))
    if qty < 0:
        raise DomainError("Miqdor manfiy bo'lishi mumkin emas")
    if not 0 <= discount <= 100:
        raise DomainError("Chegirma 0-100% oralig'ida bo'lishi kerak")

    gross = qty * Decimal(unit_price)
    net = gross * (Decimal(100) - discount) / Decimal(100)
    return int(net.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


@dataclass(frozen=True, slots=True)
class OrderTotals:
    subtotal: int
    discount_total: int
    total: int


def compute_order_totals(lines: list[dict[str, object]]) -> OrderTotals:
    """Buyurtma summalari. Hammasi tiyinda."""
    subtotal = 0
    total = 0
    for line in lines:
        quantity = Decimal(str(line["quantity"]))
        unit_price = int(line["unit_price"])  # type: ignore[arg-type]
        discount = Decimal(str(line.get("discount_percent", 0)))
        gross = int(
            (quantity * Decimal(unit_price)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        )
        subtotal += gross
        total += line_total(quantity, unit_price, discount)
    return OrderTotals(subtotal=subtotal, discount_total=subtotal - total, total=total)


# --- kredit limiti --------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CreditCheck:
    allowed: bool
    current_debt: int
    credit_limit: int
    order_total: int
    reason: str = ""

    @property
    def projected_debt(self) -> int:
        return self.current_debt + self.order_total


def check_credit_limit(current_debt: int, credit_limit: int, order_total: int) -> CreditCheck:
    """Kredit limitini tekshiradi.

    `credit_limit == 0` — limit belgilanmagan, cheklov yo'q (odatiy holat
    kichik savdoda). Manfiy qarz = oldindan to'lov, bu ruxsat etiladi.
    """
    projected = current_debt + order_total
    if credit_limit <= 0:
        return CreditCheck(True, current_debt, credit_limit, order_total)
    if projected > credit_limit:
        return CreditCheck(
            False, current_debt, credit_limit, order_total,
            reason=(
                f"Kredit limiti oshib ketadi: {projected / 100:,.0f} > "
                f"{credit_limit / 100:,.0f}"
            ),
        )
    return CreditCheck(True, current_debt, credit_limit, order_total)


# --- ombor qoldig'i -------------------------------------------------------


def apply_movement(
    quantity_on_hand: Decimal, movement_type: str, quantity: Decimal | str
) -> Decimal:
    """Bitta harakatni qoldiqqa qo'llaydi.

    Qoldiq HECH QACHON to'g'ridan-to'g'ri yozilmaydi — u shu funksiya
    orqali harakatlar ketma-ketligidan hisoblanadi (§13). Shuning uchun
    ikki qurilma bir vaqtda sotsa ham, ikkala harakat ham saqlanadi va
    natija to'g'ri chiqadi (yo'qolgan yangilanish bo'lmaydi).
    """
    sign = MOVEMENT_SIGN.get(movement_type)
    if sign is None:
        raise DomainError(f"Noma'lum harakat turi: {movement_type}")
    return quantity_on_hand + Decimal(str(quantity)) * sign


def compute_stock(movements: list[tuple[str, Decimal | str]]) -> tuple[Decimal, Decimal]:
    """Harakatlar ro'yxatidan `(qoldiq, rezerv)` ni hisoblaydi."""
    on_hand = Decimal(0)
    reserved = Decimal(0)
    for movement_type, quantity in movements:
        amount = Decimal(str(quantity))
        if movement_type == MovementType.RESERVATION:
            reserved += amount
        elif movement_type == MovementType.RELEASE:
            reserved -= amount
        else:
            on_hand = apply_movement(on_hand, movement_type, amount)
    return on_hand, reserved


def available_stock(on_hand: Decimal, reserved: Decimal) -> Decimal:
    """Sotish mumkin bo'lgan miqdor."""
    return on_hand - reserved


def check_stock_available(
    on_hand: Decimal, reserved: Decimal, requested: Decimal | str, *, allow_negative: bool = False
) -> bool:
    """Yetarli qoldiq bormi.

    `allow_negative` — ba'zi korxonalar minusga sotishga ruxsat beradi
    (tovar yo'lda). Bu ATAYLAB yoqiladigan sozlama, sukut bo'yicha yo'q.
    """
    if allow_negative:
        return True
    return available_stock(on_hand, reserved) >= Decimal(str(requested))


# --- qarzdorlik -----------------------------------------------------------


def customer_debt(orders_total: int, payments_total: int, returns_total: int = 0) -> int:
    """Mijoz qarzi (tiyinda). Manfiy qiymat — oldindan to'lov."""
    return orders_total - payments_total - returns_total


def allocate_payment(amount: int, open_orders: list[tuple[str, int]]) -> list[tuple[str, int]]:
    """To'lovni ochiq buyurtmalarga taqsimlaydi (eng eskisidan boshlab).

    `open_orders` — `(order_id, qoldiq_qarz)`, eskisidan yangisiga.
    Ortib qolgan summa taqsimlanmaydi — u avans sifatida qoladi.
    """
    if amount < 0:
        raise DomainError("To'lov summasi manfiy bo'lishi mumkin emas")

    allocations: list[tuple[str, int]] = []
    remaining = amount
    for order_id, outstanding in open_orders:
        if remaining <= 0:
            break
        if outstanding <= 0:
            continue
        applied = min(remaining, outstanding)
        allocations.append((order_id, applied))
        remaining -= applied
    return allocations
