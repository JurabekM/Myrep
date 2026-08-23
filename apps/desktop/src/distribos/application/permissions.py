"""Rollar va vakolatlar.

Fail-closed: ro'yxatda bo'lmagan rol yoki hodisa — **rad etiladi**.
"Noma'lum bo'lsa ruxsat ber" yondashuvi yangi hodisa qo'shilganda
jimgina teshik ochadi.

Bu tekshiruv lokal buyruqda ishlaydi. Kelgan hodisada esa jo'natuvchining
roli emas, uning **imzosi** va bekor qilinmaganligi tekshiriladi (DES-1) —
chunki peer o'z rolini o'zi da'vo qila olmaydi.
"""

from __future__ import annotations

from typing import Final


class PermissionDenied(PermissionError):
    """Rolda bu amal uchun vakolat yo'q."""


#: Rol -> ruxsat etilgan hodisa turlari.
ROLE_PERMISSIONS: Final[dict[str, frozenset[str]]] = {
    "owner": frozenset({
        "PRODUCT_CREATED", "PRODUCT_UPDATED", "PRODUCT_PRICE_CHANGED",
        "CUSTOMER_CREATED", "CUSTOMER_UPDATED",
        "ORDER_CREATED", "ORDER_STATE_CHANGED",
        "INVENTORY_MOVED", "PAYMENT_RECORDED", "PAYMENT_REVERSED",
        "VISIT_RECORDED", "USER_CREATED", "DEVICE_REVOKED",
    }),
    "manager": frozenset({
        "PRODUCT_CREATED", "PRODUCT_UPDATED", "PRODUCT_PRICE_CHANGED",
        "CUSTOMER_CREATED", "CUSTOMER_UPDATED",
        "ORDER_CREATED", "ORDER_STATE_CHANGED",
        "INVENTORY_MOVED", "PAYMENT_RECORDED", "PAYMENT_REVERSED",
        "VISIT_RECORDED",
    }),
    "agent": frozenset({
        # Agent buyurtma oladi va to'lov qabul qiladi, lekin NARX
        # o'zgartira olmaydi va to'lovni bekor qila olmaydi.
        "ORDER_CREATED", "CUSTOMER_CREATED", "CUSTOMER_UPDATED",
        "PAYMENT_RECORDED", "VISIT_RECORDED",
    }),
    "warehouse": frozenset({
        "INVENTORY_MOVED", "ORDER_STATE_CHANGED",
    }),
    "cashier": frozenset({
        "PAYMENT_RECORDED",
    }),
    "viewer": frozenset(),
}

#: Faqat egasi bajaradigan, ayniqsa xavfli amallar.
OWNER_ONLY: Final[frozenset[str]] = frozenset({"DEVICE_REVOKED", "USER_CREATED"})


def is_allowed(role: str, event_type: str) -> bool:
    permitted = ROLE_PERMISSIONS.get(role)
    if permitted is None:
        return False  # noma'lum rol — fail-closed
    if event_type in OWNER_ONLY and role != "owner":
        return False
    return event_type in permitted


def ensure_allowed(role: str, event_type: str) -> None:
    if not is_allowed(role, event_type):
        raise PermissionDenied(
            f"'{role}' roli '{event_type}' amalini bajara olmaydi"
        )


def allowed_events(role: str) -> frozenset[str]:
    """UI menyusini rolga moslash uchun."""
    permitted = ROLE_PERMISSIONS.get(role, frozenset())
    if role != "owner":
        permitted = permitted - OWNER_ONLY
    return permitted


#: Android'ga rolga qarab nima replikatsiya qilinadi (topshiriq §6).
#: Agentga butun korxonaning moliyaviy bazasi YUBORILMAYDI.
ROLE_REPLICATION_SCOPE: Final[dict[str, frozenset[str]]] = {
    "owner": frozenset({"*"}),
    "manager": frozenset({
        "Product", "Customer", "Order", "Inventory", "Payment", "Visit", "User",
    }),
    "agent": frozenset({
        # O'z hududidagi mijozlar, katalog, o'z buyurtmalari va to'lovlari.
        "Product", "Customer", "Order", "Payment", "Visit",
    }),
    "warehouse": frozenset({"Product", "Inventory", "Order"}),
    "cashier": frozenset({"Customer", "Order", "Payment"}),
    "viewer": frozenset({"Product"}),
}


def replication_scope(role: str) -> frozenset[str]:
    return ROLE_REPLICATION_SCOPE.get(role, frozenset())


def should_replicate(role: str, aggregate_type: str) -> bool:
    scope = replication_scope(role)
    return "*" in scope or aggregate_type in scope
